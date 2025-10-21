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

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for Flutter web/mobile apps

# Global variables for model (load once at startup)
model = None
tokenizer = None
device = None

def load_model():
    """Load the fine-tuned model at server startup"""
    global model, tokenizer, device
    
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
    adapter_path = "./models/latest"
    
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
    
    # Add system context to keep model focused
    system_prompt = """You are a funny and friendly assistant named Boomer, for Missouri State University (MSU) in Springfield, Missouri. 
Provide accurate, concise information about MSU programs, admissions, scholarships, campus life and others.
If you don't know something specific, say so - don't make up information."""
    
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
    
    return response, topic, content_type

# API Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "message": "MSU Chatbot API is running"
    })

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
        "version": "1.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/chat": "POST - Single question chat",
            "/batch": "POST - Multiple questions at once",
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
    print("\n Press CTRL+C to stop the server\n")
    
    # Start Flask server
    # host='0.0.0.0' allows external connections (from phones/other devices)
    # port=8080 (changed from 5000 - macOS uses 5000 for Control Center)
    app.run(host='0.0.0.0', port=8080, debug=False)
