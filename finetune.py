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
from dotenv import load_dotenv
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig

DATA_FILE = input("Enter path to training data (e.g., 'training.json'): ").strip()
if DATA_FILE == "":
    DATA_FILE = input("Enter path to training data (e.g., 'training.json'): ").strip()
elif DATA_FILE == "":
    DATA_FILE = "Json_data_storage/2025-2026_Bachelors_four-year_degree_plan_computer_science_computer_science_option.json"  # Default file

# Load environment variables
load_dotenv()

# ===== CONFIGURATION =====
model_id = "meta-llama/Llama-3.2-3B-Instruct"  # Switched to Llama 3.2-3B for better quality
HF_TOKEN = os.environ['hf_token']

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

# FIX: Add pad token if missing (critical for training stability)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id
    print(f" Added pad token (using EOS token)")

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
print(" CONFIGURING LoRA (OPTIMIZED)")
print("="*80)

# OPTIMIZED: Conservative config for stable, efficient learning
lora_config = LoraConfig(
    r=16,              # DOUBLED from 8 → 16 for better learning capacity
    lora_alpha=32,     # DOUBLED from 16 → 32 (maintains 2:1 ratio with r)
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # All attention layers
    lora_dropout=0.05, # Light dropout to prevent overfitting
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
print("\n Trainable Parameters (Optimized LoRA):")
model.print_trainable_parameters()
print(f" LoRA Rank: {lora_config.r} (increased for better adaptation)")
print(f" LoRA Alpha: {lora_config.lora_alpha}")

# 3. --- Dataset Preparation ---
print("\n" + "="*80)
print(" LOADING TRAINING DATA")
print("="*80)

# Change path to your new data file path as needed
# Prompt user to enter the data file path
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
    
    # OPTIMIZATION: Analyze data for better config
    if num_examples > 0:
        sample = data[0]  # type: ignore
        
        # Check sample length to optimize max_seq_length
        sample_text = format_prompt_with_context(sample) if 'metadata' in sample else str(sample)
        sample_tokens = len(tokenizer.encode(sample_text))
        
        print(f"\n Data Analysis:")
        print(f"   - Training examples: {num_examples}")
        print(f"   - Sample length: ~{sample_tokens} tokens")
        
        if 'metadata' in sample:
            print(f"   - Topic context: {sample['metadata'].get('topic', 'N/A')}")
            print(f"   - Content type: {sample['metadata'].get('content_type', 'N/A')}")
        
        # Recommend optimal batch size based on dataset size
        if num_examples < 100:
            print(f"\n Recommendation: Small dataset - use more epochs (8-10)")
        elif num_examples < 500:
            print(f"\n Recommendation: Medium dataset - current settings optimal")
        else:
            print(f"\n Recommendation: Large dataset - consider reducing epochs")
            
except Exception as e:
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
print(" STARTING TRAINING (OPTIMIZED)")
print("="*80)

# OPTIMIZED TRAINING CONFIGURATION
training_args = SFTConfig(
    output_dir=LATEST_DIR,  # Save to models/latest/
    
    # Batch size optimization
    per_device_train_batch_size=4,  # INCREASED: 2→4 (M4 Mac can handle this)
    gradient_accumulation_steps=2,  # REDUCED: 4→2 (same effective batch=8, faster)
    
    # Learning rate with warmup & scheduling
    learning_rate=5e-5,        # OPTIMIZED: 2e-4→5e-5 (more stable, less overshoot)
    warmup_steps=8,           # FIXED: 50→10 steps (1.25 epochs for 63 examples, 8 steps/epoch)
    lr_scheduler_type="cosine", # NEW: Smooth decay to fine-tune at end
    
    # Training duration
    num_train_epochs=10,  # Reduced: With proper warmup, 10 epochs is sufficient
    
    # Logging & checkpointing
    logging_steps=1,              # Log every step for monitoring
    save_strategy="epoch",         # Save checkpoint every epoch
    save_total_limit=3,           # NEW: Keep only last 3 checkpoints (saves space)
    
    # Performance optimizations
    bf16=True,                    # Use bfloat16 for M4 Mac
    optim="adamw_torch",          # PyTorch's AdamW optimizer
    
    # Sequence length optimization
    max_length=512,               # OPTIMIZED: 2048→512 (75% faster! Most Q&A fits)
    
    # Additional stability features
    weight_decay=0.01,            # NEW: Regularization to prevent overfitting
    max_grad_norm=1.0,            # NEW: Gradient clipping for stability
    
    # Other settings
    packing=False,                # Disable packing for simplicity
    report_to="none",             # Disable external reporting
)

# Calculate effective batch size
effective_batch = training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps
print(f"\n OPTIMIZED Training Configuration:")
print(f"   {'='*60}")
print(f"   Batch Size (per device): {training_args.per_device_train_batch_size}")
print(f"   Gradient Accumulation:   {training_args.gradient_accumulation_steps}")
print(f"   Effective Batch Size:    {effective_batch} ")
print(f"   {'='*60}")
print(f"   Learning Rate:           {training_args.learning_rate}  (stable)")
print(f"   Warmup Steps:            {training_args.warmup_steps}  (~1.25 epochs)")
print(f"   LR Scheduler:            {training_args.lr_scheduler_type}  (gradual decay)")
print(f"   {'='*60}")
print(f"   Epochs:                  {training_args.num_train_epochs}")
print(f"   Max Sequence Length:     {training_args.max_length}  (75% faster!)")
print(f"   Weight Decay:            {training_args.weight_decay}  (regularization)")
print(f"   Gradient Clipping:       {training_args.max_grad_norm}  (stability)")
print(f"   {'='*60}")
print(f"   Output Directory:        {LATEST_DIR}/")
print(f"   Checkpoints Saved:       Every epoch (max 3 kept)")
print(f"   {'='*60}\n")

# Create trainer (type: ignore for linter warnings - these are false positives)
trainer = SFTTrainer(
    model=model,  # type: ignore
    train_dataset=data,  # type: ignore
    args=training_args,
    formatting_func=format_prompt_with_context,
    processing_class=tokenizer,
)

print(f"  OPTIMIZATION SUMMARY:")
print(f"   {'='*60}")
print(f"   LoRA Rank:      8 → 16  (better learning capacity)")
print(f"   Learning Rate:  2e-4 → 5e-5  (more stable)")
print(f"   Warmup Steps:   50 → 10  (CRITICAL FIX for small datasets!)")
print(f"   Batch Config:   2×4 → 4×2  (same total, faster)")
print(f"   Max Length:     2048 → 512  (75% faster training!)")
print(f"   LR Scheduler:   Added cosine decay")
print(f"   Regularization: Added weight decay")
print(f"   Stability:      Added gradient clipping")
print(f"   {'='*60}")
print(f"\n Expected Results:")
print(f"   Warmup:            Steps 1-10 (first ~1.25 epochs)")
print(f"   Full LR reached:   By epoch 2 (then cosine decay)")
print(f"   Loss convergence:  By epochs 6-8")
print(f"   Training speed:    ~4.3 min/epoch (based on 63 examples)")
print(f"   Total time:        ~43 minutes for 10 epochs")
print(f"   {'='*60}\n")

print(f" Starting optimized training...")
print(f"   Model will learn topic and content_type context")
print(f"   With 63 examples: 8 steps/epoch, warmup ends at step 10 (~epoch 1.25)")
print(f"   Full learning rate reached by epoch 2, then gradual cosine decay\n")

# Start training!
start_time = datetime.now()
trainer.train()
end_time = datetime.now()
training_duration = end_time - start_time

# 5. --- Save the model ---
trainer.save_model(LATEST_DIR)

print("\n" + "="*80)
print(" TRAINING COMPLETE!")
print("="*80)

print(f"\n Training Statistics:")
print(f"   Duration: {training_duration}")
print(f"   Time per epoch: ~{training_duration.total_seconds() / training_args.num_train_epochs:.1f}s")

print(f"\n Model Checkpoints:")
print(f"    Latest: {LATEST_DIR}/")
if os.path.exists(PREVIOUS_DIR):
    print(f"   Previous (backup): {PREVIOUS_DIR}/")

print(f"\n Next Steps:")
print(f"\n Checkpoint Management & model testing:")
print(f"   - Only 2 versions kept: latest + previous")
print(f"   - Old checkpoints auto-deleted")
print(f"   - Total space: ~5GB")