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

# Import our document processor
from document_processor import DocumentProcessor

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
    base_model_name = "meta-llama/Llama-3.2-3B-Instruct"  # Switched to Llama 3.2-3B for better quality
    
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
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.bfloat16,
        device_map={"": device},
        token=os.environ['hf_token']
    )

    
    print(f" Loading fine-tuned adapters from: {adapter_path}")
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()  # Set to evaluation mode
    
    # Initialize document processor
    print(" Initializing document processor...")
    doc_processor = DocumentProcessor()
    
    print(" Model loaded successfully!\n")

def detect_topic(question):
    """Simple topic detection based on keywords"""
    question_lower = question.lower()
    
    # Topic detection logic
    if any(word in question_lower for word in ['computer science', 'cs', 'programming', 'coding', 'software']):
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
    
    # 2. Remove random special characters that don't belong (but keep bullets, numbers, basic punctuation)
    # Keep: . , ! ? : ; - • () [] "" '' 1234567890
    # Remove: weird unicode, excessive symbols
    text = re.sub(r'[^\w\s.,!?:;\-•()\[\]"\'•\n1-9]', '', text)
    
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

def generate_response(question, max_length=512, temperature=0.3, top_p=0.85):
    """Generate response from the model"""
    
    # Detect topic
    topic, content_type = detect_topic(question)
    
    # Format with contextual metadata (same as training)
    content_type_readable = content_type.replace('_', ' ').title()
    prompt = f"""### Topic: {topic}
### Category: {content_type_readable}
### Instruction:
{question}

### Response:
"""
    
    # Enhanced system prompt with formatting instructions
    system_prompt = """You are Boomer, Missouri State University's helpful assistant.

FORMATTING RULES (IMPORTANT):
- Write clear, well-structured responses
- Use line breaks between different ideas or sections
- For lists, use this format:
  • Item one
  • Item two
  • Item three
- For numbered steps:
  1. First step
  2. Second step
  3. Third step
- Keep sentences concise and readable
- Use proper spacing and avoid wall-of-text
- NO random symbols, special characters, or formatting artifacts
- Structure logically: give context, then details, then helpful conclusion

CONTENT RULES:
- Answer accurately about Missouri State University
- If unsure, clearly state: "I don't have that information, but you can find it at missouristate.edu"
- Be friendly, helpful, and professional"""
    
    full_prompt = system_prompt + "\n\n" + prompt
    
    # Tokenize
    inputs = tokenizer(full_prompt, return_tensors="pt").to(device)
    
    # Generate
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
    
    # Decode
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract only the response part (after "### Response:")
    if "### Response:" in response:
        response = response.split("### Response:")[-1].strip()
    
    # Remove the system prompt if it's still there
    if system_prompt in response:
        response = response.replace(system_prompt, "").strip()
    
    # APPLY POST-PROCESSING FORMATTER
    response = format_response_text(response)
    
    return response, topic, content_type

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
        max_length = int(request.form.get('max_length', 1024))
        temperature = float(request.form.get('temperature', 0.3))
        top_p = float(request.form.get('top_p', 0.85))
        
        # 2. Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # 3. Process document (extract text)
            print(f"\n📄 Processing document: {filename}")
            extracted_text, metadata = doc_processor.process_document(temp_path)
            
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
            system_prompt = """You are Boomer, a helpful assistant for Missouri State University. answer data in a good formatted way, if you don't know something , just say you don't know yet, but you can go to misssouristate.edu to find info about it."""
            
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
            print(f"🤖 Generating response...")
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
            
            print(f"✅ Response generated successfully")
            
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
        print(f"❌ Error in upload endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    
    Request body:
    {
        "question": "What courses do I need for CS degree?",
        "max_length": 512,  // optional, default 512
        "temperature": 0.3,  // optional, default 0.3 # lower values mean more focused and deterministic responses & less randomness & creativity & diversity & more focused answers
        "top_p": 0.85  // optional, default 0.85 ## higher values mean more random completions and creativity & diversity & less focused answers
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
        max_length = data.get('max_length', 512)
        temperature = data.get('temperature', 0.3)
        top_p = data.get('top_p', 0.85)
        
        # Validate parameters
        if not isinstance(question, str) or len(question.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "Question must be a non-empty string"
            }), 400
        
        # Generate response
        answer, topic, content_type = generate_response(
            question, 
            max_length=max_length,
            temperature=temperature,
            top_p=top_p
        )
        
        return jsonify({
            "success": True,
            "question": question,
            "answer": answer,
            "topic": topic,
            "content_type": content_type
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
            answer, topic, content_type = generate_response(
                question,
                max_length=max_length,
                temperature=temperature,
                top_p=top_p
            )
            results.append({
                "question": question,
                "answer": answer,
                "topic": topic,
                "content_type": content_type
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
                    "max_length": 1024,
                    "temperature": 0.3,
                    "top_p": 0.85
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
