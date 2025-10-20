"""
Test script for your fine-tuned Gemma model on MSU Scholarship questions.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Load the base model and tokenizer
model_id = "meta-llama/Llama-3.2-3B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id, token="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")

print("Loading base model...")
base_model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.bfloat16,
    device_map="auto",
    token="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"
)

# Load the fine-tuned LoRA adapters
print("Loading fine-tuned LoRA adapters...")
model = PeftModel.from_pretrained(base_model, "./models/latest")
model.eval()

# Test questions
test_questions = [
    "Tell me about the Freshmen Scholarships at Missouri State University.",
    "What scholarships are available for Transfer Students?",
    "Are there scholarships for Current Students?",
    "What about Graduate Student Scholarships?",
    "Can you explain the MSU Foundation Scholarships?",
    "What is the deadline for freshman scholarships?",
]

print("\n" + "="*80)
print("TESTING YOUR FINE-TUNED MODEL")
print("="*80 + "\n")

for question in test_questions:
    prompt = f"### Instruction:\n{question}\n\n### Response:\n"
    
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extract only the response part
    response = response.split("### Response:\n")[-1]
    
    print(f"Q: {question}")
    print(f"A: {response}\n")
    print("-" * 80 + "\n")

print("Testing complete!")
