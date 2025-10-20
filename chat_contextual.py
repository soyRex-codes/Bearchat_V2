"""
Interactive chat with contextual prompting for MSU Assistant.
Uses the same format as enhanced_finetune.py with topic and category context.
"""

import os
import torch
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Load environment variables
load_dotenv()

# --- Configuration ---
model_id = "meta-llama/Llama-3.2-3B-Instruct"  # Switched to Llama 3.2-3B for better quality
adapter_path = "./models/latest"  # Latest fine-tuned model

# --- Model Loading ---
print("Loading model... (this may take a moment)")

tokenizer = AutoTokenizer.from_pretrained(model_id, token=os.environ['hf_token'])

base_model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.bfloat16,
    device_map="auto",
    token=os.environ['hf_token']
)

print("Loading fine-tuned LoRA adapters...")
model = PeftModel.from_pretrained(base_model, adapter_path)
model.eval()

# Topic detection helpers
def detect_topic_and_category(question):
    """Detect what topic/category the question is about."""
    question_lower = question.lower()
    
    # Computer Science / Academic Programs
    if any(word in question_lower for word in ['computer science', 'cs degree', 'programming', 'coding', 'software']):
        return "BS Computer Science Degree Plan", "Academic Program"
    
    # Scholarships / Financial Aid
    if any(word in question_lower for word in ['scholarship', 'financial aid', 'tuition', 'cost', 'funding']):
        return "Scholarships and Financial Aid", "Financial Aid"
    
    # Admissions
    if any(word in question_lower for word in ['admission', 'apply', 'application', 'requirements', 'gpa']):
        return "Admissions", "Admissions"
    
    # Housing
    if any(word in question_lower for word in ['housing', 'dorm', 'residence', 'room']):
        return "Housing and Residence Life", "Housing"
    
    # Default to general
    return "Missouri State University", "General Information"

print("\n" + "="*80)
print("MSU ASSISTANT (Contextual Fine-tuned)")
print("="*80)
print("\nAsk me anything about Missouri State University!")
print("Type 'quit' or 'exit' to end the conversation.")
print("\n Tip: I can answer questions about:")
print("   • Computer Science programs")
print("   • Scholarships and Financial Aid")
print("   • Admissions")
print("   • Housing")
print("   • And more!\n")

while True:
    question = input("You: ").strip()
    
    if question.lower() in ['quit', 'exit', 'q']:
        print("\nThank you for using the MSU Assistant!")
        break
    
    if not question:
        continue
    
    # Detect topic and category
    topic, category = detect_topic_and_category(question)
    
    # Use contextual prompt format (same as training)
    prompt = f"""### Topic: {topic}
### Category: {category}
### Instruction:
You are an assistant for Missouri State University (MSU) in Springfield, Missouri. Only provide information based on Missouri State University data. If you don't have specific information, say so clearly.

Question: {question}

### Response:
"""
    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.5,  # Low temperature for focused answers
            do_sample=True,  # Enable sampling for diverse responses
            top_p=0.85,  # Top-p sampling for controlled randomness
            repetition_penalty=1.1,  # Prevent repetition
            pad_token_id=tokenizer.eos_token_id,
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract only the response part
    if "### Response:" in response:
        response = response.split("### Response:")[-1].strip()
    
    print(f"\n [Topic: {topic}]")
    print(f"Assistant: {response}\n")
    print("-" * 80 + "\n")
