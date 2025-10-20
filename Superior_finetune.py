"""
Enhanced Fine-tuning with Contextual Metadata + Smart Checkpoint Management
===========================================================================
This version uses topic and content_type metadata to help the model:
1. Understand what domain/topic it's answering about
2. Avoid mixing answers from different topics
3. Provide context-aware responses

Checkpoint Management:
- Keeps only 2 versions: models/latest/ and models/previous/
- Auto-backs up before training
- Auto-deletes old checkpoints
- Easy rollback with rollback_checkpoint.py

The model learns: "I'm answering about [TOPIC] in the [CONTENT_TYPE] category"

Note: Some type warnings from Pylance are false positives and can be ignored.
The code works correctly despite the warnings.
"""

import torch
import os
import shutil
from datetime import datetime
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig

# ===== CONFIGURATION =====
model_id = "meta-llama/Llama-3.2-3B-Instruct"  # Switched to Llama 3.2-3B for better quality
HF_TOKEN = "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"

# Checkpoint directories
CHECKPOINT_DIR = "./models"
LATEST_DIR = os.path.join(CHECKPOINT_DIR, "latest")
PREVIOUS_DIR = os.path.join(CHECKPOINT_DIR, "previous")

# ===== CHECKPOINT MANAGEMENT =====
def manage_checkpoints():
    """Manage checkpoint versions before training."""
    print("\n" + "="*80)
    print(" CHECKPOINT MANAGEMENT")
    print("="*80)
    
    # Create models directory if needed
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    
    # If latest exists, backup to previous
    if os.path.exists(LATEST_DIR):
        print(f"\n Backing up current model...")
        
        # Remove old previous if exists
        if os.path.exists(PREVIOUS_DIR):
            print(f"   Removing old backup...")
            shutil.rmtree(PREVIOUS_DIR)
        
        # Move latest to previous
        print(f"   latest/ → previous/")
        shutil.move(LATEST_DIR, PREVIOUS_DIR)
        print(f"    Backup complete")
    else:
        print(f"\n No existing checkpoint to backup")
    
    # Clean up old checkpoint directories (from old runs)
    old_dirs = [
        "llama-3.2-3b-final",
        "llama-3.2-3b-final-checkpoint",
        "llama-3.2-3b-contextual",
        "llama-3.2-3b-contextual-checkpoint"
    ]
    
    cleaned = []
    for old_dir in old_dirs:
        if os.path.exists(old_dir) and os.path.isdir(old_dir):
            print(f"     Removing old checkpoint: {old_dir}/")
            shutil.rmtree(old_dir)
            cleaned.append(old_dir)
    
    if cleaned:
        print(f"    Cleaned up {len(cleaned)} old checkpoint(s)")
    
    print(f"\n Checkpoint Status:")
    print(f"   Latest: {'Will be created' if not os.path.exists(LATEST_DIR) else ' Exists'}")
    print(f"   Previous: {' Exists (backup)' if os.path.exists(PREVIOUS_DIR) else ' No backup'}")

# Run checkpoint management
manage_checkpoints()

# 1. --- Model and Tokenizer Loading ---
print("\n" + "="*80)
print(" LOADING MODEL")
print("="*80)

print(f"\n Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_id, token=HF_TOKEN)
tokenizer.padding_side = 'right'

print(f" Loading base model: {model_id}")
# Force model to load on MPS (not meta device) to avoid training errors
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    dtype=torch.bfloat16,
    device_map={"": device},  # Force all layers to MPS
    token=HF_TOKEN
)
print(f" Model loaded successfully")

# 2. --- LoRA Configuration ---
print("\n" + "="*80)
print(" CONFIGURING LoRA")
print("="*80)

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
print("\n Trainable Parameters:")
model.print_trainable_parameters()

# 3. --- Dataset Preparation ---
print("\n" + "="*80)
print(" LOADING TRAINING DATA")
print("="*80)

# Change path to your new data file path as needed
DATA_FILE = "Json_data_storage/smart_cost_of_attendance_for_missouri_state_university_training.json"
# Or use combined file: DATA_FILE = "combined_msu_training_20251018.json"

print(f"\n Loading: {DATA_FILE}")

if not os.path.exists(DATA_FILE):
    print(f"\n ERROR: File not found: {DATA_FILE}")
    print(f"\n Options:")
    print(f"   1. Collect data: python superiror_msu_collector.py")
    print(f"   2. Combine multiple files: python combine_training_data.py")
    print(f"   3. Update DATA_FILE path in this script (line 124)")
    exit(1)

data = load_dataset("json", data_files=DATA_FILE, split="train")

# Type hint workaround for linter
try:
    num_examples = len(data)  # type: ignore
    print(f" Loaded {num_examples} training examples")
    
    # Show data summary
    if num_examples > 0:
        sample = data[0]  # type: ignore
        if 'metadata' in sample:
            print(f"\n Data includes:")
            print(f"   - Topic context: {sample['metadata'].get('topic', 'N/A')}")
            print(f"   - Content type: {sample['metadata'].get('content_type', 'N/A')}")
except:
    print(f" Data loaded successfully")

def format_prompt_with_context(sample):
    """
    Enhanced prompt format that includes topic and content_type.
    This helps the model learn WHAT it's talking about.
    
    Format:
    ### Topic: [topic]
    ### Category: [content_type]
    ### Instruction:
    [question]
    
    ### Response:
    [answer]
    """
    # Extract metadata
    metadata = sample.get('metadata', {})
    topic = metadata.get('topic', 'Missouri State University')
    content_type = metadata.get('content_type', 'general_info')
    
    # Format content_type to be more readable
    content_type_readable = content_type.replace('_', ' ').title()
    
    # Create enhanced prompt
    prompt = f"""### Topic: {topic}
### Category: {content_type_readable}
### Instruction:
{sample['instruction']}

### Response:
{sample['response']}"""
    
    return prompt

# Optional: Simple format without metadata (if you want to compare)
def format_prompt_simple(sample):
    """Simple format without context - just instruction and response."""
    return f"### Instruction:\n{sample['instruction']}\n\n### Response:\n{sample['response']}"

# 4. --- Training ---
print("\n" + "="*80)
print(" STARTING TRAINING")
print("="*80)

training_args = SFTConfig(
    output_dir=LATEST_DIR,  # Save to models/latest/
    per_device_train_batch_size=2,  # Reduced batch size for 16-bit training
    gradient_accumulation_steps=4,  # Gradient accumulation steps
    learning_rate=2e-4,  # Learning rate
    num_train_epochs=3,  # REDUCED: 3 epochs instead of 10 to prevent overfitting
    logging_steps=1,  # Log every step
    bf16=True, # Use bfloat16 for M4 Mac
    optim="adamw_torch", # Use PyTorch's AdamW
    save_strategy="epoch", # Save checkpoint every epoch
    report_to="none", # Disable reporting
    max_length=1024,  # Max sequence length
    packing=False, # Disable packing for simplicity
)

# Create trainer (type: ignore for linter warnings - these are false positives)
trainer = SFTTrainer(
    model=model,  # type: ignore
    train_dataset=data,  # type: ignore
    args=training_args,
    formatting_func=format_prompt_with_context,
    processing_class=tokenizer,
)

print(f"\n  Training will take ~1-2 minutes per epoch...")
print(f" Config:")
print(f"   - Batch size: {training_args.per_device_train_batch_size}")
print(f"   - Epochs: {training_args.num_train_epochs}")
print(f"   - Learning rate: {training_args.learning_rate}")
print(f"   - Output: {LATEST_DIR}/")
print(f"\n Starting training with contextual metadata...")
print(f"   Model will learn topic and content_type context")
print(f"   This helps prevent answer mixing!\n")

# Start training!
trainer.train()

# 5. --- Save the model ---
trainer.save_model(LATEST_DIR)

print("\n" + "="*80)
print(" TRAINING COMPLETE!")
print("="*80)

print(f"\n Model Checkpoints:")
print(f"    Latest: {LATEST_DIR}/")
if os.path.exists(PREVIOUS_DIR):
    print(f"   Previous (backup): {PREVIOUS_DIR}/")

print(f"\n Next Steps:")
print(f"   1. Test the model:")
print(f"      python chat_contextual.py")
print(f"")
print(f"   2. If model is bad, rollback:")
print(f"      python rollback_checkpoint.py")
print(f"")
print(f"   3. Collect more data:")
print(f"      python superior_msu_collector.py")

print(f"\n Checkpoint Management:")
print(f"   - Only 2 versions kept: latest + previous")
print(f"   - Old checkpoints auto-deleted")
print(f"   - Total space: ~4-8GB")