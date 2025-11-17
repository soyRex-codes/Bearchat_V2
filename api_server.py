"""
MSU Chatbot API Server
Flask-based REST API for serving the fine-tuned Llama model
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os
from werkzeug.utils import secure_filename
import tempfile
import re
import hashlib
import time
from functools import lru_cache
from datetime import datetime
import logging
import traceback
import json

# Try to import PDF processing libraries
try:
    import fitz  # PyMuPDF - much faster than PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("⚠️  PyMuPDF (fitz) not installed - PDF upload will be disabled")
    print("   Install with: pip install pymupdf")

try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("⚠️  PIL/pytesseract not installed - Image OCR will be disabled")

# Try to import Web Search functionality (optional)
HAS_WEB_SEARCH = False
search_engine = None
try:
    from web_search import get_search_engine
    search_engine = None  # Will be initialized in load_model()
    HAS_WEB_SEARCH = True
except ImportError:
    print("⚠️  web_search.py not found - web search will be disabled")


# Configure logging for performance monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter web/mobile apps

# File upload configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'gif'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Global variables for model (load once at startup)
model = None
tokenizer = None
device = None
doc_processor = None
search_engine = None  # Web search engine

# Response cache (in-memory LRU cache for frequent questions)
# Key: hash of (question + temperature + top_p)
# Value: (response, topic, content_type, timestamp)
response_cache = {}
CACHE_MAX_SIZE = 200  # Increased from 100 for better hit rate
CACHE_TTL = 7200  # Increased to 2 hours (from 1 hour)

def get_cache_key(question, temperature, top_p, conversation_history=None):
    """Generate cache key from question parameters"""
    # Include conversation history in cache key for context-aware caching
    history_str = ""
    if conversation_history:
        history_str = str([(h.get('question', ''), h.get('answer', '')) for h in conversation_history[-2:]])
    
    cache_input = f"{question.lower().strip()}|{temperature}|{top_p}|{history_str}"
    return hashlib.md5(cache_input.encode()).hexdigest()

def get_cached_response(cache_key):
    """Retrieve cached response if valid"""
    if cache_key in response_cache:
        cached_data = response_cache[cache_key]
        timestamp = cached_data.get('timestamp', 0)
        
        # Check if cache is still valid
        if time.time() - timestamp < CACHE_TTL:
            logger.info(f"✓ Cache HIT: {cache_key[:8]}...")
            return cached_data
        else:
            # Cache expired
            logger.info(f"⚠ Cache EXPIRED: {cache_key[:8]}...")
            del response_cache[cache_key]
    
    logger.info(f"✗ Cache MISS: {cache_key[:8]}...")
    return None

def cache_response(cache_key, response, topic, content_type):
    """Cache a response with LRU eviction"""
    global response_cache
    
    # If cache is full, remove oldest entry (simple LRU)
    if len(response_cache) >= CACHE_MAX_SIZE:
        oldest_key = min(response_cache.keys(), key=lambda k: response_cache[k]['timestamp'])
        del response_cache[oldest_key]
        logger.info(f"Cache full, evicted: {oldest_key[:8]}...")
    
    response_cache[cache_key] = {
        'response': response,
        'topic': topic,
        'content_type': content_type,
        'timestamp': time.time()
    }
    logger.info(f"✓ Cached response: {cache_key[:8]}... (total: {len(response_cache)})")

# Simple Document Processor
class SimpleDocumentProcessor:
    """Basic document processor for PDFs and images with caching"""
    
    def __init__(self):
        # Cache for document text (hash -> (text, metadata))
        self._cache = {}
        self._cache_max_size = 50  # Store up to 50 processed docs in memory
    
    def _get_file_hash(self, file_path):
        """Calculate MD5 hash of file for cache key"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
    
    def process_document(self, file_path, original_filename=None):
        """Extract text from document with caching"""
        # Check cache first
        try:
            file_hash = self._get_file_hash(file_path)
            if file_hash in self._cache:
                print(f"  ⚡ Using cached extraction for {original_filename or 'document'}")
                return self._cache[file_hash]
        except Exception:
            pass  # If hashing fails, proceed without cache
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        metadata = {
            'file_name': original_filename or os.path.basename(file_path),
            'file_type': file_ext,
            'processing_method': 'unknown',
            'num_characters': 0,
            'num_pages': 0
        }
        
        result = None
        try:
            if file_ext == '.pdf':
                if not HAS_PDF:
                    result = ("PDF processing not available. Please install PyMuPDF: pip install pymupdf", metadata)
                else:
                    text, num_pages = self._extract_pdf(file_path)
                    metadata['processing_method'] = 'pdf_extraction'
                    metadata['num_pages'] = num_pages
                    metadata['num_characters'] = len(text)
                    result = (text, metadata)
                
            elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
                if not HAS_OCR:
                    result = ("Image OCR not available. Please install: pip install pillow pytesseract", metadata)
                else:
                    text = self._extract_image_ocr(file_path)
                    metadata['processing_method'] = 'ocr'
                    metadata['num_characters'] = len(text)
                    result = (text, metadata)
            else:
                result = (f"Unsupported file type: {file_ext}", metadata)
                
        except Exception as e:
            result = (f"Error processing document: {str(e)}", metadata)
        
        # Cache successful extractions
        if result and file_ext == '.pdf':
            try:
                file_hash = self._get_file_hash(file_path)
                # Manage cache size
                if len(self._cache) >= self._cache_max_size:
                    # Remove oldest entry (simple FIFO)
                    self._cache.pop(next(iter(self._cache)))
                self._cache[file_hash] = result
            except Exception:
                pass  # Cache failure shouldn't break processing
        
        return result
    
    def _extract_pdf(self, file_path):
        """Extract text from PDF - optimized with PyMuPDF (5-10x faster than PyPDF2)"""
        text = ""
        num_pages = 0
        
        try:
            # Open PDF with PyMuPDF (much faster than PyPDF2)
            doc = fitz.open(file_path)
            total_pages = len(doc)
            num_pages = total_pages
            
            # Process up to 50 pages (increased from 10 due to faster processing)
            max_pages = min(50, total_pages)
            
            if total_pages > max_pages:
                print(f"  ⚠️  Large PDF ({total_pages} pages), processing first {max_pages} pages")
            
            # Batch extract text (much faster than page-by-page)
            page_texts = []
            for page_num in range(max_pages):
                try:
                    page = doc[page_num]
                    page_text = page.get_text("text")  # PyMuPDF's optimized text extraction
                    if page_text.strip():  # Only add non-empty pages
                        page_texts.append(page_text)
                except Exception as e:
                    print(f"  ⚠️  Skipping page {page_num+1}: {str(e)}")
                    continue
            
            # Combine all pages
            text = "\n\n".join(page_texts)
            doc.close()
            
        except Exception as e:
            print(f"  ❌ PDF extraction failed: {str(e)}")
            return f"Error: {str(e)}", 0
        
        return text.strip(), num_pages
    
    def _extract_image_ocr(self, file_path):
        """Extract text from image using OCR"""
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    
    def chunk_text_for_llama(self, text, max_tokens=2000):
        """Split text into chunks that fit in context window - optimized for speed"""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return [text]
        
        # For very large documents, use first + last strategy (faster than full processing)
        if len(text) > max_chars * 3:
            # Take first 60% and last 40% of allowed size
            first_part_size = int(max_chars * 0.6)
            last_part_size = int(max_chars * 0.4)
            
            first_part = text[:first_part_size]
            last_part = text[-last_part_size:]
            
            return [first_part + "\n\n[... middle content omitted for speed ...]\n\n" + last_part]
        
        # For moderately large docs, split by paragraphs
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text[:max_chars]]

def load_model():
    """Load the fine-tuned model at server startup"""
    global model, tokenizer, device, doc_processor, search_engine
    
    print("🔄 Loading model...")
    
    # Set device
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print(" Using Apple Silicon (MPS)")
    else:
        device = torch.device("cpu")
        print(" Using CPU")
    
    # Load base model and tokenizer
    base_model_name = "meta-llama/Llama-3.2-3B-Instruct"  # Llama 3.2-3B
    
    # Model selection priority: production > staging > latest (fallback for old setups)
    if os.path.exists("./models/production"):
        adapter_path = "./models/production"
        print(" Using PRODUCTION model (safe, manually promoted)")
    elif os.path.exists("./models/staging"):
        adapter_path = "./models/staging"
        print(" ⚠️  Using STAGING model (promote to production when ready)")
    elif os.path.exists("./models/latest"):
        adapter_path = "./models/latest"
        print(" ⚠️  Using LATEST model (old setup - migrate to new system)")
    else:
        print(" ❌ ERROR: No model found!")
        print("    Train a model first: python finetune.py")
        exit(1)
    
    print(f"Loading base model: {base_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, token=os.environ['hf_token'])
    
    # CRITICAL FIX: Ensure padding side and special tokens match training
    tokenizer.padding_side = 'right'
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # DISABLE chat template to use raw format (matches training)
    tokenizer.chat_template = None
    
    # OPTIMIZATION: Set padding to False by default for single-request inference
    # This reduces unnecessary padding tokens that slow down processing
    print(" ✓ Tokenizer configured for optimized inference (no padding)")
    
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.bfloat16,
        device_map={"":device},
        token=os.environ['hf_token'],
        attn_implementation="sdpa",  # Use scaled dot-product attention (faster)
    )

    
    print(f" Loading fine-tuned adapters from: {adapter_path}")
    model = PeftModel.from_pretrained(model, adapter_path)
    
    # Check adapter config
    import json
    config_path = os.path.join(adapter_path, "adapter_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            adapter_config = json.load(f)
            alpha = adapter_config.get('lora_alpha', 32)
            rank = adapter_config.get('r', 16)
            scaling = alpha / rank
            print(f" ✓ Adapter loaded: alpha={alpha}, rank={rank}, scaling={scaling:.1f}x")
            
            # Only apply scaling fix if alpha is weak (< 64)
            if alpha < 64:
                print(f" ⚡ APPLYING QUICK FIX: Scaling weak adapters...")
                for name, param in model.named_parameters():
                    if 'lora_A' in name or 'lora_B' in name:
                        param.data *= 2.0
                print(f"    ✓ Adapters scaled 2x (compensating for alpha={alpha})")
            else:
                print(f" ✓ Strong adapters detected (alpha={alpha}), no scaling needed")
    
    # Merge LoRA weights into base model
    print(" Merging LoRA adapters into base model...")
    model = model.merge_and_unload()
    
    model.eval()  # Set to evaluation mode
    
    # OPTIMIZATION: Compile model for Apple Silicon (20-30% speedup)
    if device.type == "mps":
        try:
            print(" Compiling model for Apple Silicon (Metal optimization)...")
            model = torch.compile(model, backend="aot_eager", mode="reduce-overhead")
            print(" ✓ Model compiled for optimized inference")
        except Exception as e:
            print(f" ⚠️  Model compilation skipped: {e}")
    
    # Initialize document processor
    doc_processor = SimpleDocumentProcessor()
    print("✓ Document processor initialized")
    
    # Initialize web search engine
    if HAS_WEB_SEARCH:
        search_engine = get_search_engine()
        if search_engine and search_engine.is_available():
            print("✓ Web search engine initialized (Google Custom Search)")
        else:
            print("⚠️  Web search engine not configured (add GOOGLE_API_KEY and GOOGLE_CSE_ID to .env)")
    
    print("✅ Model loaded successfully!\n")

def detect_topic(question):
    """Simple topic detection based on keywords"""
    question_lower = question.lower().strip()
    
    # Check for greetings/casual conversation (return special marker)
    greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 
                 'greetings', 'howdy', 'what\'s up', 'whats up', 'sup']
    casual = ['how are you', 'how r u', 'hru', 'thank you', 'thanks', 'bye', 'goodbye', 
              'see you', 'nice talking', 'ok', 'okay', 'cool', 'great']
    
    if any(question_lower == greeting or question_lower.startswith(greeting + ' ') 
           for greeting in greetings):
        return "Greeting", "casual"
    
    if any(phrase in question_lower for phrase in casual):
        return "Casual", "casual"
    
    # Topic detection logic
    if any(word in question_lower for word in ['computer science', 'cs', 'csc', 'msu', 'course plan', ' Computer Science degree plan', 'programming', 'coding', 'software']):
        return "BS Computer Science Degree Plan", "academic_program"
    elif any(word in question_lower for word in ['scholarship', 'financial aid', 'grant', 'loan']):
        return "Scholarships and Financial Aid", "financial_aid"
    elif any(word in question_lower for word in ['admission', 'apply', 'application', 'requirements']):
        return "Admissions", "admissions"
    elif any(word in question_lower for word in ['housing', 'dorm', 'residence', 'room']):
        return "Housing", "housing"
    else:
        return "Missouri State University", "general_info"

def format_response_text(text):
    """
    Post-process model output to ensure clean, readable formatting.
    
    This function:
    - Removes excessive whitespace and random symbols
    - Ensures proper line breaks between ideas
    - Formats lists with bullets or numbers
    - Cleans up formatting artifacts from model output
    """
    if not text or len(text.strip()) == 0:
        return text
    
    # 1. Remove excessive whitespace (multiple spaces, tabs)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 2. Remove random special characters that don't belong (but keep bullets, numbers, basic punctuation, URLs)
    # Keep: . , ! ? : ; - • () [] "" '' 1234567890 / @ # (for URLs and markdown)
    # Remove: weird unicode, excessive symbols
    # CRITICAL: Preserve URL characters (://@#) and markdown syntax ([])
    text = re.sub(r'[^\w\s.,!?:;\-•()\[\]"\'•\n1-9/@#]', '', text)
    
    # 3. Fix line breaks - ensure proper spacing
    # Remove excessive newlines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 4. Add line breaks before numbered lists if missing
    # Pattern: "text1. Item" -> "text\n1. Item"
    text = re.sub(r'([a-z])\s*(\d+\.)', r'\1\n\n\2', text)
    
    # 5. Add line breaks before bullet points if missing
    # Pattern: "text• Item" -> "text\n• Item"
    text = re.sub(r'([a-z])\s*(•)', r'\1\n\n\2', text)
    
    # 6. Ensure space after sentence-ending punctuation
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    
    # 7. Clean up common model artifacts
    text = text.replace('###', '')  # Remove training format markers
    text = text.replace('***', '')  # Remove excessive asterisks
    text = text.replace('---', '')  # Remove separator lines
    
    # 8. Ensure proper spacing around list items
    lines = text.split('\n')
    formatted_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a list item (bullet or number)
        is_list_item = bool(re.match(r'^[•\-\*]|\d+\.', line))
        
        # Add proper spacing before list items
        if is_list_item and formatted_lines and not re.match(r'^[•\-\*]|\d+\.', formatted_lines[-1]):
            # Add blank line before first list item
            if formatted_lines[-1]:  # Only if previous line wasn't blank
                formatted_lines.append('')
        
        formatted_lines.append(line)
    
    # 9. Join lines back together
    text = '\n'.join(formatted_lines)
    
    # 10. Final cleanup: remove leading/trailing whitespace
    text = text.strip()
    
    # 11. Ensure no more than 2 consecutive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text

def generate_response(question, max_length=512, temperature=0.6, top_p=0.8, conversation_history=None, web_search_enabled=False):
    """
    Generate response from the model with optional conversation history and caching
    
    Args:
        question: Current user question
        max_length: Max tokens to generate
        temperature: Sampling temperature
        top_p: Top-p sampling parameter
        conversation_history: List of {"question": str, "answer": str} dicts (last 3-5 exchanges)
        web_search_enabled: User preference for web search (default: False)
    
    Returns:
        tuple: (response, topic, content_type, metrics)
        - response: Generated text
        - topic: Detected topic
        - content_type: Type of content
        - metrics: Dict with performance data
    """
    start_time = time.time()
    
    # Check cache first (only for non-casual questions)
    cache_key = get_cache_key(question, temperature, top_p, conversation_history)
    cached = get_cached_response(cache_key)
    
    if cached:
        metrics = {
            'cached': True,
            'inference_time': 0,
            'total_time': time.time() - start_time
        }
        return cached['response'], cached['topic'], cached['content_type'], metrics
    
    # Detect topic
    topic, content_type = detect_topic(question)
    
    # Handle greetings and casual conversation with SHORT responses
    if content_type == "casual":
        greeting_responses = {
            "hi": "Hi! I'm BearChat, your Missouri State University assistant. How can I help you today?",
            "hello": "Hello! I'm here to help with questions about Missouri State University. What would you like to know?",
            "hey": "Hey! How can I assist you with Missouri State University information?",
            "good morning": "Good morning! How can I help you with Missouri State University today?",
            "good afternoon": "Good afternoon! What can I help you with regarding Missouri State University?",
            "good evening": "Good evening! How may I assist you with Missouri State University?",
            "how are you": "I'm doing great, thanks for asking! How can I help you with Missouri State University information?",
            "thank you": "You're welcome! Let me know if you need anything else about Missouri State University.",
            "thanks": "Happy to help! Feel free to ask more questions about Missouri State University.",
            "bye": "Goodbye! Feel free to come back if you have more questions about Missouri State University.",
            "goodbye": "Take care! Come back anytime you need information about Missouri State University.",
            "ok": "Great! Let me know if you have any other questions.",
            "okay": "Sounds good! Feel free to ask more questions about Missouri State University.",
        }
        
        question_lower = question.lower().strip()
        # Try exact match first
        for key, response in greeting_responses.items():
            if question_lower == key or question_lower.startswith(key + ' '):
                metrics = {'cached': False, 'casual_response': True, 'total_time': time.time() - start_time}
                return response, topic, content_type, metrics
        
        # Try partial match for casual phrases
        for key, response in greeting_responses.items():
            if key in question_lower:
                metrics = {'cached': False, 'casual_response': True, 'total_time': time.time() - start_time}
                return response, topic, content_type, metrics
        
        # Default casual response
        metrics = {'cached': False, 'casual_response': True, 'total_time': time.time() - start_time}
        return "I'm BearChat, your Missouri State University assistant. How can I help you today?", topic, content_type, metrics
    
    # Web search - RESPECTS USER TOGGLE ONLY (no secondary filtering)
    web_search_context = ""
    search_citations = []
    search_used = False
    
    # Perform web search ONLY if user explicitly enabled it (no model/script override)
    if web_search_enabled:
        # Skip web search for casual/greeting queries (waste of API calls)
        if content_type in ["casual", "greeting"]:
            logger.info("⏭️  Skipping web search for casual/greeting query")
        elif HAS_WEB_SEARCH and search_engine:
            logger.info(f"🔍 Performing web search (user-requested): {question}")
            search_response = search_engine.search(question, num_results=3)
            
            if search_response['success'] and search_response['results']:
                web_search_context = "\n" + search_engine.format_results_for_llm(search_response)
                search_citations = search_engine.extract_citations(search_response)
                search_used = True
                logger.info(f"✓ Added {len(search_citations)} web sources to context")
            else:
                logger.warning("⚠️  Web search returned no results")
        else:
            logger.warning("⚠️  Web search requested but search engine not available")
    else:
        logger.info("⏭️  Web search disabled by user; skipping")
    
    # Build conversation context if history exists
    history_context = ""
    if conversation_history and len(conversation_history) > 0:
        history_context = "\n### Conversation History:\n"
        for i, exchange in enumerate(conversation_history[-3:], 1):  # Last 3 exchanges
            history_context += f"User: {exchange['question']}\n"
            history_context += f"Assistant: {exchange['answer']}\n\n"
    
    # Format with contextual metadata (EXACTLY like training format)
    # CRITICAL: Add strong constraints to prevent generic responses
    content_type_readable = content_type.replace('_', ' ').title()
    
    # Adjust system behavior based on whether web search is active
    if search_used:
        # When web search is used, be HELPFUL and synthesize the information
        context_instruction = f"""You are BearChat, Missouri State University's AI assistant. Web search results are provided below with current MSU information.

Your task:
1. Read the web search results carefully
2. Answer the question using information from the search results
3. Provide a helpful, detailed response about MSU
4. Cite sources using [1], [2], [3] notation
5. If the search results don't fully answer the question, acknowledge what you found and what's missing

Do NOT refuse to help or redirect users to the website - you have current information from web search, so use it to provide a complete answer."""
        web_search_section = f"\n\n{web_search_context}\n"
    else:
        # When no web search, use the training constraint
        context_instruction = "You are BearChat, an AI assistant specialized in Missouri State University (MSU) information. Provide helpful information about MSU based on your training data. If you don't have specific information, acknowledge that and suggest checking missouristate.edu."
        web_search_section = ""
    
    prompt = f"""### Topic: {topic}
### Category: {content_type_readable}
### Context: {context_instruction}{web_search_section}{history_context}
### Instruction:
{question}

### Response:
"""
    
    # NO system prompt - use ONLY the training format
    # The model was fine-tuned without a system prompt prefix
    
    # Tokenize with optimized settings
    inputs = tokenizer(prompt, return_tensors="pt", padding=False).to(device)
    
    # OPTIMIZATION: Pre-allocate attention mask for faster processing
    attention_mask = inputs['attention_mask']
    
    # Generate with parameters matching training + speed optimizations
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_length,
            temperature=0.7,  # Moderate temperature for coherent output
            top_p=0.9,  # Standard nucleus sampling
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.1,  # Mild repetition penalty
            use_cache=True,  # Enable KV cache for faster decoding
        )
    
    # Decode
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract only the response part (after "### Response:")
    if "### Response:" in response:
        response = response.split("### Response:")[-1].strip()
    
    # Remove any remaining prompt artifacts
    if "### Instruction:" in response:
        response = response.split("### Instruction:")[-1].strip()
    
    # APPLY POST-PROCESSING FORMATTER
    response = format_response_text(response)
    
    # CRITICAL: Filter for generic/off-topic responses
    # If the model gives generic advice not specific to MSU, replace with a focused response
    generic_phrases = [
        "in general", "universities typically", "most colleges", "many schools",
        "usually", "generally speaking", "colleges and universities", "higher education institutions",
        "educational institutions", "across different universities"
    ]
    
    # Check if response is too generic
    response_lower = response.lower()
    if any(phrase in response_lower for phrase in generic_phrases) and "missouri state" not in response_lower:
        logger.warning(f"Detected generic response, adding MSU-specific constraint")
        response = f"I'm specifically designed to help with Missouri State University (MSU) information. For your question about {topic}, I recommend:\n\n" + \
                   "• Visit the MSU website at missouristate.edu\n" + \
                   "• Contact MSU directly at (417) 836-5000\n" + \
                   "• Email admissions@missouristate.edu for specific inquiries\n\n" + \
                   "Could you rephrase your question to focus specifically on Missouri State University?"
    
    # Ensure MSU is mentioned at least once in substantial responses (>50 chars)
    if len(response) > 50 and "missouri state" not in response_lower and "msu" not in response_lower:
        logger.warning(f"Response missing MSU reference, adding reminder")
        response = f"[Missouri State University (MSU) Information]\n\n{response}\n\n*Note: This information is specific to Missouri State University.*"
    
    # Calculate metrics
    inference_time = time.time() - start_time
    metrics = {
        'cached': False,
        'casual_response': False,
        'inference_time': inference_time,
        'total_time': inference_time,
        'tokens_generated': len(tokenizer.encode(response)) if tokenizer else 0,
        'web_search_used': search_used,
        'citations': search_citations if search_used else []
    }
    
    # Cache the response (skip casual conversations)
    if content_type != "casual":
        cache_response(cache_key, response, topic, content_type)
    
    logger.info(f"Generated response in {inference_time:.2f}s ({metrics['tokens_generated']} tokens)")
    
    # Save web search data for training if search was used
    if search_used and search_citations:
        save_web_search_training_data(
            question=question,
            answer=response,
            citations=search_citations,
            topic=topic,
            content_type=content_type
        )
    
    return response, topic, content_type, metrics

def save_web_search_training_data(question, answer, citations, topic, content_type):
    """
    Save web search queries and responses for future model training
    Appends to web_search_data_collection.txt in JSON Lines format
    """
    try:
        training_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "topic": topic,
            "content_type": content_type,
            "citations": citations,
            "source": "web_search",
            "model_version": "llama-3.2-3b-instruct-finetuned"
        }
        
        # Append to file in JSON Lines format (one JSON object per line)
        with open('web_search_data_collection.txt', 'a', encoding='utf-8') as f:
            f.write(json.dumps(training_entry, ensure_ascii=False) + '\n')
        
        logger.info(f"✓ Saved web search training data: {question[:50]}...")
    except Exception as e:
        logger.error(f"Failed to save web search training data: {e}")

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# API Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "document_processor_ready": doc_processor is not None,
        "message": "MSU Chatbot API is running"
    })

@app.route('/upload', methods=['POST'])
def upload_document():
    """
    Document upload endpoint for PDFs and images.
    
    Form data:
    - file: PDF or image file (required)
    - question: Question about the document (required)
    - max_length: Response length (optional, default 1024)
    - temperature: Generation temperature (optional, default 0.3)
    - top_p: Top-p sampling (optional, default 0.85)
    
    Response:
    {
        "success": true,
        "question": "What is my GPA?",
        "answer": "Based on your transcript...",
        "document_info": {
            "file_name": "transcript.pdf",
            "file_type": "pdf",
            "processing_method": "pdf_extraction",
            "num_characters": 5234
        }
    }
    """
    try:
        # 1. Validate request
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file provided. Include 'file' in form data."
            }), 400
        
        if 'question' not in request.form:
            return jsonify({
                "success": False,
                "error": "No question provided. Include 'question' in form data."
            }), 400
        
        file = request.files['file']
        question = request.form['question']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # Get optional parameters - ADJUSTED for document analysis
        max_length = int(request.form.get('max_length', 400))  # Increased from 256 for detailed analysis
        temperature = float(request.form.get('temperature', 0.3))
        top_p = float(request.form.get('top_p', 0.85))
        
        # 2. Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # 3. Process document (extract text) - OPTIMIZED
            print(f"\n📄 Processing document and generating reponse: {filename}")
            start_time = time.time()
            extracted_text, metadata = doc_processor.process_document(temp_path, original_filename=filename)
            print(f"  ✓ Text extraction: {time.time() - start_time:.2f}s")
            
            # 4. Check if text was extracted
            if not extracted_text or len(extracted_text.strip()) < 10:
                return jsonify({
                    "success": False,
                    "error": "Could not extract text from document. It may be empty or corrupted.",
                    "document_info": metadata
                }), 400
            
            # 5. Chunk text if needed (REDUCED to 2000 tokens for speed)
            chunks = doc_processor.chunk_text_for_llama(extracted_text, max_tokens=2000)
            
            # Use first chunk only for speed
            document_context = chunks[0]
            if len(chunks) > 1:
                context_note = f"\n(Note: This document has {len(chunks)} sections. Showing first section with key information.)"
            else:
                context_note = ""
            
            # 6. Create DETAILED but efficient prompt for document analysis
            # Detect topic from question
            topic, content_type = detect_topic(question)
            
            # Determine document type and adjust instructions
            is_transcript = "transcript" in question.lower() or "grade" in document_context.lower() or "course" in document_context.lower()
            
            if is_transcript:
                # TRANSCRIPT-SPECIFIC PROMPT: Use training format with clear boundaries
                system_context = "You are BearChat, an academic advisor for Missouri State University. When analyzing transcripts, identify completed courses, missing requirements, and recommend specific courses for the next semester. Be thorough and specific."
                
                full_prompt = f"""{system_context}

### Transcript:
{document_context}{context_note}

### Question:
{question}

### Response:
"""
            else:
                # GENERAL DOCUMENT PROMPT
                system_context = "You are BearChat, Missouri State University assistant. Read documents carefully and provide detailed, helpful answers based on the content."
                
                full_prompt = f"""{system_context}

### Document:
{document_context}{context_note}

### Question:
{question}

### Response:
"""
            
            # 7. Generate response with timing
            print(f"  ⚡ Generating response...")
            gen_start = time.time()
            inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=3000, padding=False).to(device)
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=temperature > 0,  # Only sample if temperature > 0
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    num_beams=1,  # Greedy decoding for speed
                    use_cache=True,  # Enable KV cache
                    early_stopping=True,  # Stop when EOS token generated
                )
            
            gen_time = time.time() - gen_start
            print(f"  ✓ Generation: {gen_time:.2f}s")
            
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # AGGRESSIVE EXTRACTION: Remove all prompt artifacts
            # Try multiple split points in order of preference
            if "### Response:" in response:
                response = response.split("### Response:")[-1].strip()
            elif "Response:" in response:
                response = response.split("Response:")[-1].strip()
            elif "ANSWER:" in response:
                response = response.split("ANSWER:")[-1].strip()
            elif "Answer:" in response:
                response = response.split("Answer:")[-1].strip()
            
            # Remove any remaining prompt sections
            for marker in ["### Transcript:", "### Document:", "### Question:", "TRANSCRIPT DATA:", "DOCUMENT CONTENT:", "STUDENT'S QUESTION:", "YOUR TASK:"]:
                if marker in response:
                    response = response.split(marker)[0].strip()
            
            # Remove the full_prompt if it somehow got included
            if full_prompt[:100] in response:
                response = response.replace(full_prompt, "").strip()
            
            # APPLY POST-PROCESSING FORMATTER
            response = format_response_text(response)
            
            print(f"  ✓ Total time: {time.time() - start_time:.2f}s")
            
            # 8. Return response
            return jsonify({
                "success": True,
                "question": question,
                "answer": response,
                "document_info": {
                    "file_name": metadata['file_name'],
                    "file_type": metadata['file_type'],
                    "processing_method": metadata['processing_method'],
                    "num_characters": metadata['num_characters'],
                    "num_chunks": len(chunks)
                },
                "topic": topic,
                "content_type": content_type
            })
            
        finally:
            # 9. Clean up temp file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
        
    except Exception as e:
        print(f" Error in upload endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint with conversation memory support
    
    Request body:
    {
        "question": "What courses do I need for CS degree?",
        "conversation_history": [  // optional - last 3-5 Q&A pairs
            {"question": "What is the CS program?", "answer": "The CS program is..."},
            {"question": "How long is it?", "answer": "It's a 4-year program..."}
        ],
        "max_length": 1024,  // optional, default 1024
        "temperature": 0.8,  // optional, default 0.8
        "top_p": 0.92  // optional, default 0.92
    }
    
    Response:
    {
        "success": true,
        "question": "What courses do I need for CS degree?",
        "answer": "The CS program requires...",
        "topic": "BS Computer Science Degree Plan",
        "content_type": "academic_program"
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'question' field in request body"
            }), 400
        
        question = data['question']
        conversation_history = data.get('conversation_history', [])  # Optional history
        web_search_enabled = bool(data.get('web_search_enabled', False))  # User preference for web search
        max_length = data.get('max_length', 512)
        temperature = data.get('temperature', 0.6)
        top_p = data.get('top_p', 0.8)

        logger.info(
            f"Web search preference (client): {'ENABLED' if web_search_enabled else 'DISABLED'}"
        )

        # Validate parameters
        if not isinstance(question, str) or len(question.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "Question must be a non-empty string"
            }), 400
        
        # Validate conversation history format
        if conversation_history and not isinstance(conversation_history, list):
            return jsonify({
                "success": False,
                "error": "conversation_history must be a list of {question, answer} objects"
            }), 400
        
        # Generate response WITH conversation context and web search preference
        answer, topic, content_type, metrics = generate_response(
            question, 
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            conversation_history=conversation_history,
            web_search_enabled=web_search_enabled
        )
        
        # Log performance metrics
        logger.info(f"Chat request: cached={metrics.get('cached', False)}, "
                   f"time={metrics.get('total_time', 0):.2f}s, "
                   f"tokens={metrics.get('tokens_generated', 0)}")
        
        return jsonify({
            "success": True,
            "question": question,
            "answer": answer,
            "topic": topic,
            "content_type": content_type,
            "metrics": {
                "cached": metrics.get('cached', False),
                "inference_time": metrics.get('inference_time', 0),
                "total_time": metrics.get('total_time', 0),
                "tokens_generated": metrics.get('tokens_generated', 0),
                "web_search_used": metrics.get('web_search_used', False),
                "citations": metrics.get('citations', []),
                "web_search_enabled": web_search_enabled
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/batch', methods=['POST'])
def batch_chat():
    """
    Batch chat endpoint - process multiple questions at once
    
    Request body:
    {
        "questions": ["Question 1?", "Question 2?", ...],
        "max_length": 512,  // optional
        "temperature": 0.3,  // optional
        "top_p": 0.85  // optional
    }
    
    Response:
    {
        "success": true,
        "results": [
            {
                "question": "Question 1?",
                "answer": "Answer 1...",
                "topic": "...",
                "content_type": "..."
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'questions' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'questions' field in request body"
            }), 400
        
        questions = data['questions']
        if not isinstance(questions, list) or len(questions) == 0:
            return jsonify({
                "success": False,
                "error": "Questions must be a non-empty list"
            }), 400
        
        max_length = data.get('max_length', 512)
        temperature = data.get('temperature', 0.3)
        top_p = data.get('top_p', 0.85)
        
        results = []
        for question in questions:
            answer, topic, content_type, metrics = generate_response(
                question,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p
            )
            results.append({
                "question": question,
                "answer": answer,
                "topic": topic,
                "content_type": content_type,
                "cached": metrics.get('cached', False)
            })
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API documentation"""
    return jsonify({
        "name": "MSU Chatbot API",
        "version": "2.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/chat": "POST - Single question chat",
            "/batch": "POST - Multiple questions at once",
            "/upload": "POST - Upload PDF/image and ask questions about it"
        },
        "documentation": {
            "chat_example": {
                "url": "/chat",
                "method": "POST",
                "body": {
                    "question": "What courses do I need for CS degree?",
                    "max_length": 512,
                    "temperature": 0.3,
                    "top_p": 0.85
                }
            },
            "upload_example": {
                "url": "/upload",
                "method": "POST",
                "content_type": "multipart/form-data",
                "form_data": {
                    "file": "transcript.pdf (or image file)",
                    "question": "What is my GPA?",
                    "max_length": 512,
                    "temperature": 0.3,
                    "top_p": 0.8
                },
                "supported_formats": ["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "gif"]
            }
        }
    })

if __name__ == '__main__':
    print("="*80)
    print("MSU CHATBOT API SERVER")
    print("="*80)
    
    # Load model at startup
    load_model()
    
    print("="*80)
    print(" STARTING SERVER")
    print("="*80)
    print("\n Server will be available at:")
    print("   - Local: http://localhost:8080")
    print("   - Network: http://My_MAC_IP:8080")
    print("\n Available endpoints:")
    print("   - GET  /health - Health check")
    print("   - POST /chat   - Single question")
    print("   - POST /batch  - Multiple questions")
    print("   - POST /upload - Upload PDF/image + question")
    print("\n Press CTRL+C to stop the server\n")
    
    # Start Flask server
    # host='0.0.0.0' allows external connections (from phones/other devices)
    # port=8080 (changed from 5000 - macOS uses 5000 for Control Center)
    app.run(host='0.0.0.0', port=8080, debug=False)