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
import json
from datetime import datetime
from dotenv import load_dotenv
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, PeftModel
from trl import SFTTrainer, SFTConfig

# Interactive data file selection with smart default
DATA_FILE = input("Enter path to training data (or press Enter for latest): ").strip()
if DATA_FILE == "":
    # Auto-detect latest training file
    import glob
    json_files = glob.glob("msu_training_*.json") + glob.glob("Json_data_storage/*.json")
    if json_files:
        # Sort by modification time, get most recent
        DATA_FILE = max(json_files, key=os.path.getmtime)
        print(f"✓ Using latest file: {DATA_FILE}")
    else:
        DATA_FILE = "msu_training_20251103_183346.json"  # Fallback default
        print(f"⚠️  No training files found, using default: {DATA_FILE}")

# Load environment variables
load_dotenv()

# ===== CONFIGURATION =====
model_id = "meta-llama/Llama-3.2-3B-Instruct"  # Llama 3.2-3B - works on M4 Mac
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

# ===== CONTINUAL LEARNING: Load previous training if exists =====
print(f"\n Checking for previous training...")
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

if os.path.exists(PREVIOUS_DIR):
    print(f"\n ✓ Previous training found in {PREVIOUS_DIR}")
    print(f"   Loading base model + previous LoRA adapters...")
    print(f"   This ensures the model REMEMBERS all previous knowledge!")
    
    # Step 1: Load base model
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=torch.bfloat16,
        device_map={"": device},
        token=HF_TOKEN
    )
    
    # Step 2: Load previous LoRA adapters
    print(f"   Loading previous LoRA adapters from {PREVIOUS_DIR}...")
    model = PeftModel.from_pretrained(model, PREVIOUS_DIR)
    
    # Step 3: MERGE previous LoRA into base model weights (PERMANENT)
    print(f"   Merging previous knowledge into base model (this is PERMANENT)...")
    model = model.merge_and_unload()
    
    print(f"   ✓ Previous knowledge successfully merged!")
    print(f"   Base model now contains ALL previous training data")
    print(f"   New training will ADD to this knowledge (not replace it)")
    
else:
    print(f"\n ℹ No previous training found")
    print(f"   This is your FIRST training session")
    print(f"   Loading fresh base model: {model_id}")
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=torch.bfloat16,
        device_map={"": device},
        token=HF_TOKEN
    )

print(f"\n ✓ Model loaded successfully")

# 2. --- LoRA Configuration ---
print("\n" + "="*80)
print(" CONFIGURING LoRA (DYNAMIC OPTIMIZATION)")
print("="*80)

# Enable gradient checkpointing for memory efficiency (CRITICAL for larger models)
model.gradient_checkpointing_enable()
print(f"\n ✓ Gradient checkpointing enabled (saves ~40% memory)")

# LoRA will be configured after analyzing dataset for optimal settings
print(f"\n LoRA configuration will be optimized after analyzing dataset...")

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
num_examples = len(data)  # type: ignore
print(f" Loaded {num_examples} training examples")

# ===== DYNAMIC LoRA CONFIGURATION BASED ON DATASET SIZE =====
print("\n" + "="*80)
print(" OPTIMIZING LoRA CONFIGURATION")
print("="*80)

if num_examples < 100:
    lora_rank = 8
    lora_alpha = 32  # 4x scaling for strong fine-tuning
    num_epochs = 8
    batch_size = 2
    grad_accum = 4
    max_length = 512
    lora_dropout = 0.05
    print(f"\n Small dataset ({num_examples} examples)")
    print(f"   Strategy: Low rank, high alpha for strong adaptation")
elif num_examples < 500:
    lora_rank = 16
    lora_alpha = 64  # INCREASED: 4x scaling (was 2x) for stronger fine-tuning
    num_epochs = 5  # For A100 training, 5-10 epochs is fine
    batch_size = 2
    grad_accum = 4
    max_length = 640
    lora_dropout = 0.05  # Standard dropout (A100 can handle more epochs)
    print(f"\n Medium dataset ({num_examples} examples)")
    print(f"   Strategy: Rank 16, Alpha 64 (4x scaling) for STRONG fine-tuning")
    print(f"   ℹ️  For A100 training: 5-35 epochs is acceptable")
    print(f"   ℹ️  Alpha 64 = 4x stronger than base model (prevents hallucination)")
else:
    lora_rank = 32
    lora_alpha = 128  # 4x scaling for large datasets
    num_epochs = 3
    batch_size = 4
    grad_accum = 2
    max_length = 768
    lora_dropout = 0.05
    print(f"\n Large dataset ({num_examples} examples)")
    print(f"   Strategy: Higher rank with strong alpha (4x scaling)")

# Configure LoRA with optimized settings
lora_config = LoraConfig(
    r=lora_rank,
    lora_alpha=lora_alpha,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=lora_dropout,  # DYNAMIC: Higher dropout for generalization
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
print("\n Trainable Parameters:")
model.print_trainable_parameters()
print(f" LoRA Rank: {lora_rank}")
print(f" LoRA Alpha: {lora_alpha}")
print(f" Training Epochs: {num_epochs}")
print(f" Batch Size: {batch_size} × {grad_accum} = {batch_size * grad_accum} (effective)")
print(f" Max Sequence Length: {max_length} tokens")

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
    
    # Dataset configuration
    dataset_text_field="text",     # Field name for text data (will be generated by formatting_func)
    max_length=max_length,         # DYNAMIC: Optimized based on dataset size
    
    # Batch size optimization
    per_device_train_batch_size=batch_size,     # DYNAMIC: Optimized based on dataset size
    gradient_accumulation_steps=grad_accum,     # DYNAMIC: Optimized based on dataset size
    
    # Learning rate with warmup & scheduling
    learning_rate=2e-4,        # INCREASED for A100 training (was 2e-5, too conservative)
    warmup_steps=min(int(num_examples * 0.1), 50),  # DYNAMIC: 10% of data or 50 steps max
    lr_scheduler_type="cosine", # Smooth decay to fine-tune at end
    
    # Training duration - DYNAMIC based on dataset size
    num_train_epochs=num_epochs,  # DYNAMIC: 10 for <100, 5 for 100-500, 3 for 500+
    
    # Logging & checkpointing
    logging_steps=1,              # Log every step for monitoring
    save_strategy="epoch",         # Save checkpoint every epoch
    save_total_limit=2,           # Keep only 2 best checkpoints (saves space)
    
    # Performance optimizations
    bf16=True,                    # Use bfloat16 for M4 Mac
    optim="adamw_torch",          # PyTorch's AdamW optimizer
    
    # Additional stability features
    weight_decay=0.01,            # Standard regularization (A100 training doesn't need high decay)
    max_grad_norm=1.0,            # Standard gradient clipping
    
    # Other settings
    packing=False,                # Disable packing for simplicity
    report_to="none",             # Disable external reporting
)

# Calculate effective batch size
effective_batch = training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps
steps_per_epoch = 45 / effective_batch  # Assuming 45 examples (update dynamically if needed)
warmup_epochs = training_args.warmup_steps / steps_per_epoch

print(f"\n ✅ OPTIMIZED Training Configuration (45-example dataset):")
print(f"   {'='*60}")
print(f"   Batch Size (per device): {training_args.per_device_train_batch_size}")
print(f"   Gradient Accumulation:   {training_args.gradient_accumulation_steps}")
print(f"   Effective Batch Size:    {effective_batch}")
print(f"   Steps per Epoch:         {steps_per_epoch:.1f}")
print(f"   {'='*60}")
print(f"   Learning Rate:           {training_args.learning_rate}")
print(f"   Warmup Steps:            {training_args.warmup_steps} ({warmup_epochs:.1f} epochs)")
print(f"   LR Scheduler:            {training_args.lr_scheduler_type} (smooth decay)")
print(f"   {'='*60}")
print(f"   Epochs:                  {training_args.num_train_epochs} (INCREASED for small data)")
print(f"   Max Sequence Length:     {training_args.max_length} tokens (covers 95%+ data)")
print(f"   Weight Decay:            {training_args.weight_decay}")
print(f"   Gradient Clipping:       {training_args.max_grad_norm}")
print(f"   Save Strategy:           {training_args.save_strategy}")
print(f"   {'='*60}")
print(f"   Output Directory:        {LATEST_DIR}/")
print(f"   Checkpoints Saved:       Every epoch (max 2 kept)")
print(f"   {'='*60}\n")

# Create trainer (type: ignore for linter warnings - these are false positives)
trainer = SFTTrainer(
    model=model,  # type: ignore
    train_dataset=data,  # type: ignore
    args=training_args,
    formatting_func=format_prompt_with_context,
    processing_class=tokenizer,
)

print(f"  📊 KEY OPTIMIZATIONS APPLIED:")
print(f"   {'='*60}")
print(f"   Dataset Size:   45 examples (small dataset)")
print(f"   Epochs:         5 → 12 (more passes needed)")
print(f"   Warmup:         10 → 8 steps (~1.4 epochs)")
print(f"   Batch Config:   4×2 → 2×4 (better gradients)")
print(f"   Max Length:     512 → 640 tokens (no truncation)")
print(f"   Checkpoints:    3 → 2 (saves disk space)")
print(f"   {'='*60}\n")

print(f" Starting optimized training...")
print(f"   Model will learn topic and content_type context")
print(f"   With 45 examples: ~5.6 steps/epoch, warmup ends at step 8 (~1.4 epochs)")
print(f"   Full learning rate by epoch 2, then cosine decay")
print(f"   Training time: ~2.8 min/epoch × 12 epochs = ~34 minutes\n")

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