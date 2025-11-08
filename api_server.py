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

# Try to import PDF processing libraries
try:
    import PyPDF2
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("⚠️  PyPDF2 not installed - PDF upload will be disabled")

try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("⚠️  PIL/pytesseract not installed - Image OCR will be disabled")


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

# Response cache (in-memory LRU cache for frequent questions)
# Key: hash of (question + temperature + top_p)
# Value: (response, topic, content_type, timestamp)
response_cache = {}
CACHE_MAX_SIZE = 100  # Maximum cached responses
CACHE_TTL = 3600  # Cache time-to-live: 1 hour

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
    """Basic document processor for PDFs and images"""
    
    def process_document(self, file_path, original_filename=None):
        """Extract text from document"""
        file_ext = os.path.splitext(file_path)[1].lower()
        
        metadata = {
            'file_name': original_filename or os.path.basename(file_path),
            'file_type': file_ext,
            'processing_method': 'unknown',
            'num_characters': 0,
            'num_pages': 0
        }
        
        try:
            if file_ext == '.pdf':
                if not HAS_PDF:
                    return "PDF processing not available. Please install PyPDF2: pip install PyPDF2", metadata
                
                text, num_pages = self._extract_pdf(file_path)
                metadata['processing_method'] = 'pdf_extraction'
                metadata['num_pages'] = num_pages
                metadata['num_characters'] = len(text)
                return text, metadata
                
            elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
                if not HAS_OCR:
                    return "Image OCR not available. Please install: pip install pillow pytesseract", metadata
                
                text = self._extract_image_ocr(file_path)
                metadata['processing_method'] = 'ocr'
                metadata['num_characters'] = len(text)
                return text, metadata
            else:
                return f"Unsupported file type: {file_ext}", metadata
                
        except Exception as e:
            return f"Error processing document: {str(e)}", metadata
    
    def _extract_pdf(self, file_path):
        """Extract text from PDF with page limit for large files"""
        text = ""
        num_pages = 0
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            num_pages = total_pages
            
            # Limit to first 10 pages for large PDFs to avoid memory issues
            max_pages = min(10, total_pages)
            
            if total_pages > max_pages:
                print(f"  ⚠️  Large PDF detected ({total_pages} pages), processing first {max_pages} pages only")
            
            for i in range(max_pages):
                try:
                    page_text = pdf_reader.pages[i].extract_text()
                    text += page_text + "\n"
                except Exception as e:
                    print(f"  ⚠️  Error extracting page {i+1}: {str(e)}")
                    continue
        
        return text.strip(), num_pages
    
    def _extract_image_ocr(self, file_path):
        """Extract text from image using OCR"""
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    
    def chunk_text_for_llama(self, text, max_tokens=3000):
        """Split text into chunks that fit in context window"""
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return [text]
        
        # Split by paragraphs first
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
    global model, tokenizer, device, doc_processor
    
    print(" Loading model...")
    
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
    
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.bfloat16,
        device_map={"": device},
        token=os.environ['hf_token']
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
    
    # Initialize document processor
    doc_processor = SimpleDocumentProcessor()
    print(" Document processor initialized")
    
    print(" Model loaded successfully!\n")

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

def generate_response(question, max_length=512, temperature=0.6, top_p=0.8, conversation_history=None):
    """
    Generate response from the model with optional conversation history and caching
    
    Args:
        question: Current user question
        max_length: Max tokens to generate
        temperature: Sampling temperature
        top_p: Top-p sampling parameter
        conversation_history: List of {"question": str, "answer": str} dicts (last 3-5 exchanges)
    
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
    prompt = f"""### Topic: {topic}
### Category: {content_type_readable}
### Context: You are BearChat, an AI assistant specialized ONLY in Missouri State University (MSU) information. You must ONLY provide information about MSU. Do NOT provide general advice or information about other universities.{history_context}
### Instruction:
{question}

### Response:
"""
    
    # NO system prompt - use ONLY the training format
    # The model was fine-tuned without a system prompt prefix
    
    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    
    # Generate with parameters matching training
    # CRITICAL: Use same settings as training to prevent gibberish
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
        'tokens_generated': len(tokenizer.encode(response)) if tokenizer else 0
    }
    
    # Cache the response (skip casual conversations)
    if content_type != "casual":
        cache_response(cache_key, response, topic, content_type)
    
    logger.info(f"Generated response in {inference_time:.2f}s ({metrics['tokens_generated']} tokens)")
    
    return response, topic, content_type, metrics

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
        
        # Get optional parameters
        max_length = int(request.form.get('max_length', 512))
        temperature = float(request.form.get('temperature', 0.3))
        top_p = float(request.form.get('top_p', 0.85))
        
        # 2. Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # 3. Process document (extract text)
            print(f"\n📄 Processing document: {filename}")
            extracted_text, metadata = doc_processor.process_document(temp_path, original_filename=filename)
            
            # 4. Check if text was extracted
            if not extracted_text or len(extracted_text.strip()) < 10:
                return jsonify({
                    "success": False,
                    "error": "Could not extract text from document. It may be empty or corrupted.",
                    "document_info": metadata
                }), 400
            
            # 5. Chunk text if needed (to fit in context window)
            chunks = doc_processor.chunk_text_for_llama(extracted_text, max_tokens=3000)
            
            # Use first chunk or combine chunks intelligently
            if len(chunks) > 1:
                # For long documents, use first chunk + summary approach
                document_context = chunks[0]
                context_note = f"\n\n(Note: This is a multi-page document. Showing first section. Total {len(chunks)} sections.)"
            else:
                document_context = chunks[0]
                context_note = ""
            
            # 6. Create prompt with document context
            system_prompt = """You are Boomer, your should only include data in your response regarding Missouri State University and not anything random. answer data in a good formatted way, if you don't know something , just say you don't know yet, but you can go to misssouristate.edu to find info about it."""
            
            # Detect topic from question
            topic, content_type = detect_topic(question)
            content_type_readable = content_type.replace('_', ' ').title()
            
            full_prompt = f"""{system_prompt}

### Document Content:
{document_context}{context_note}

### Topic: {topic}
### Category: {content_type_readable}
### Question:
{question}

### Response:
"""
            
            # 7. Generate response
            print(f" Generating response...")
            inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=4096).to(device)
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the response part
            if "### Response:" in response:
                response = response.split("### Response:")[-1].strip()
            
            # Clean up system prompt if present
            if system_prompt in response:
                response = response.replace(system_prompt, "").strip()
            
            # APPLY POST-PROCESSING FORMATTER
            response = format_response_text(response)
            
            print(f" Response generated successfully")
            
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
        max_length = data.get('max_length', 512)
        temperature = data.get('temperature', 0.6)
        top_p = data.get('top_p', 0.8)

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
        
        # Generate response WITH conversation context
        answer, topic, content_type, metrics = generate_response(
            question, 
            max_length=max_length,
            temperature=temperature,
            top_p=top_p,
            conversation_history=conversation_history
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
                "total_time": metrics.get('total_time', 0)
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