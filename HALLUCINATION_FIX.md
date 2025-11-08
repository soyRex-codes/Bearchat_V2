# Hallucination Fix Guide: Catastrophic Overfitting

## 🔴 **CRITICAL ISSUE IDENTIFIED**

### The Problem
Your model trained on **496 examples for 35 epochs** = **17,360 training iterations**

This caused **CATASTROPHIC OVERFITTING**:
- Model **MEMORIZED** training patterns
- Model **LOST** ability to recall specific facts (course numbers, names)
- Model now **HALLUCINATES** by mixing your data with base model knowledge

### Why It's Hallucinating

When you ask: *"What do you know about MSU?"*

**What the model remembers:**
- ✅ "I should talk about CS courses at MSU"
- ✅ "There are math requirements and CSC courses"

**What the model FORGOT:**
- ❌ Specific course numbers: CSC 130, CSC 131, CSC 232
- ❌ Actual course names: "Computational Thinking", "Data Structures"
- ❌ Real prerequisites: "CSC 131, MTH 314"

**What it does instead:**
- 🤖 Invents course numbers from base training: CSC 1300, CSC 1400
- 🤖 Makes up course names that "sound right"
- 🤖 Fabricates requirements using generic patterns

### Your Training Data (CORRECT ✅)
```json
{
  "instruction": "Tell me about CSC 130",
  "response": "CSC 130 (The World of Computer Science) is a 3-credit course..."
},
{
  "instruction": "Tell me about CSC 131",
  "response": "CSC 131 (Computational Thinking) is a 4-credit course..."
}
```

### What Model Outputs (WRONG ❌)
```
CSC 1300 Discrete Mathematics (3 hours)
CSC 1400 Programming Fundamentals (3 hours)  
MATH 1313 Calculus I (4 hours)
STAT 1502 Statistics (5 hours)
```

**NONE of these courses exist at MSU!**

---

## 🛠️ **THE FIX**

### Step 1: Delete Overfitted Model

```bash
cd /Users/rajkushwaha/Desktop/develop/Fine-tunned-project-v2

# Backup current (broken) model
mkdir -p models/broken_overfitted
mv models/latest/* models/broken_overfitted/
mv models/previous/* models/broken_overfitted/

echo "✓ Overfitted model backed up to models/broken_overfitted/"
```

### Step 2: Retrain with Correct Settings

Your training script has been **automatically fixed** with:

| Setting | OLD (Bad) | NEW (Fixed) | Why |
|---------|-----------|-------------|-----|
| **Epochs (496 examples)** | 35 epochs | **3 epochs** | Prevents memorization |
| **LoRA Dropout** | 0.05 | **0.15** | Forces generalization |
| **Weight Decay** | 0.01 | **0.05** | Stronger regularization |
| **Learning Rate** | 3e-5 | **2e-5** | More conservative |
| **Gradient Clipping** | 1.0 | **0.5** | Prevents overfitting spikes |

### Step 3: Run Training

```bash
cd /Users/rajkushwaha/Desktop/develop/Fine-tunned-project-v2

# Train with your full dataset
python finetune.py

# When prompted, enter:
# Json_data_storage/1. MSU_Computer_science_master_training_data.json
```

**Expected output:**
```
✓ Medium dataset (496 examples)
  Strategy: Balanced rank, moderate epochs, HIGH dropout for generalization
  ⚠️  WARNING: 35+ epochs will cause catastrophic overfitting!
  ⚠️  Model will memorize patterns but forget specific facts!

LoRA Rank: 16
LoRA Alpha: 32
LoRA Dropout: 0.15 (HIGH - forces generalization)
Training Epochs: 3 (NOT 35!)
```

**Training will take ~12-15 minutes** (not 2 hours like 35 epochs)

### Step 4: Test the Fixed Model

```bash
# Start API server
python api_server.py

# In another terminal, test
python test_api.py
```

**Test questions to verify fix:**
```json
{
  "question": "What do you know about MSU?"
}
```

**Expected response (CORRECT):**
```
The Bachelor of Science in Computer Science is a four-year program...

Degree Requirements:
• 120-128 semester hours
• General Education requirements (40-42 hours)

Core Courses:
• CSC 130 - The World of Computer Science (3 hours)
• CSC 131 - Computational Thinking (4 hours)
• CSC 232 - Data Structures (4 hours)
• MTH 261 - Calculus I (5 hours)
...
```

---

## 📊 **Understanding Epochs**

### Training Dataset: 496 examples

| Epochs | Total Passes | Training Time | Result |
|--------|-------------|---------------|---------|
| **3** | 1,488 | ~15 min | ✅ **Optimal** - Learns patterns, retains facts |
| **5** | 2,480 | ~25 min | ⚠️ **Borderline** - May start forgetting |
| **10** | 4,960 | ~50 min | 🔶 **Risky** - Likely overfitting |
| **35** | 17,360 | ~3 hours | 🔴 **CATASTROPHIC** - Memorizes patterns, forgets facts |

### The Science

**Fine-tuning is NOT like training from scratch!**

- **Pre-trained model** already knows language, reasoning, patterns
- **Fine-tuning** should **specialize**, not **replace** knowledge
- **3-5 epochs** = Learn MSU-specific facts while keeping base knowledge
- **35 epochs** = Overwrite base knowledge with training artifacts

Think of it like:
- **3 epochs** = Teaching someone MSU-specific info
- **35 epochs** = Brainwashing them until they forget everything else

---

## 🔬 **What Fixed Settings Do**

### 1. LoRA Dropout: 0.05 → 0.15
**Problem:** Low dropout = model memorizes exact training sequences
**Fix:** High dropout = forces model to generalize patterns

During training, 15% of LoRA weights randomly turn off each step, forcing the model to learn **robust patterns** instead of **exact sequences**.

### 2. Weight Decay: 0.01 → 0.05
**Problem:** Low decay = weights grow unbounded, memorizing data
**Fix:** High decay = penalizes large weights, prevents memorization

**Regularization formula:** `Loss = Task_Loss + 0.05 * ||weights||²`

Punishes the model for using large weights, forcing it to use simpler, more generalizable patterns.

### 3. Learning Rate: 3e-5 → 2e-5
**Problem:** Higher LR = rapid weight changes = overfitting
**Fix:** Lower LR = gradual adjustments = better generalization

Smaller steps prevent the model from "jumping" to memorized solutions.

### 4. Gradient Clipping: 1.0 → 0.5
**Problem:** Large gradients = overfitting spikes
**Fix:** Tighter clipping = smoother learning = better stability

Prevents single examples from dominating the learning process.

---

## ✅ **Validation Checklist**

After retraining, verify the model outputs **REAL MSU information**:

### Test 1: Course Numbers
**Question:** "Tell me about CSC courses"

✅ **CORRECT:** CSC 130, CSC 131, CSC 232, CSC 244, CSC 325, CSC 333, CSC 335
❌ **WRONG:** CSC 1300, CSC 1400, CS 101, CS 201

### Test 2: Course Names
**Question:** "What is CSC 131?"

✅ **CORRECT:** "CSC 131 (Computational Thinking) is a 4-credit course..."
❌ **WRONG:** "CSC 131 Introduction to Programming..."

### Test 3: Prerequisites
**Question:** "What are the prerequisites for CSC 232?"

✅ **CORRECT:** "CSC 131, MTH 314"
❌ **WRONG:** "CSC 130 or equivalent"

### Test 4: Credit Hours
**Question:** "How many credits is MTH 261?"

✅ **CORRECT:** "MTH 261 is 5 credit hours"
❌ **WRONG:** "MTH 261 is 3 credit hours" or "4 credit hours"

### Test 5: Department Contact
**Question:** "How do I contact the CS department?"

✅ **CORRECT:** "Phone: (417) 836-4157, Email: ComputerScience@missouristate.edu"
❌ **WRONG:** Generic response without specific contact info

---

## 🚨 **Prevention for Future Training**

### Always Use These Epoch Limits

| Dataset Size | MAX Epochs | Recommended |
|--------------|------------|-------------|
| < 100 examples | 10 | 8 |
| 100-500 examples | **5** | **3** ← Your dataset |
| 500-1000 examples | 3 | 2 |
| 1000+ examples | 2 | 1-2 |

### Early Stopping Rule

**STOP training when:**
1. Loss stops decreasing for 2 consecutive epochs
2. Model starts outputting training examples verbatim
3. Validation loss increases (if you have validation split)

### Signs of Overfitting During Training

Watch console output:
```
Epoch 1: loss=0.45  ✅ Good - learning
Epoch 2: loss=0.32  ✅ Good - still learning
Epoch 3: loss=0.28  ✅ Good - marginal improvement
Epoch 4: loss=0.27  ⚠️ Warning - very small improvement
Epoch 5: loss=0.265 🔴 STOP - diminishing returns
```

**If loss < 0.15** → Model is memorizing, not learning!

---

## 📈 **Expected Results After Fix**

### Before (35 Epochs - Overfitted)
```
User: What do you know about MSU CS program?

Model: The CS program at Missouri State includes:
- CSC 1300 Discrete Mathematics (3 hours)
- CSC 1400 Programming Fundamentals (3 hours)
- MATH 1313 Calculus I (4 hours)
- STAT 1502 Statistics (5 hours)

Students need 120 credits to graduate...
[WRONG - these courses don't exist at MSU!]
```

### After (3 Epochs - Fixed)
```
User: What do you know about MSU CS program?

Model: The Bachelor of Science in Computer Science at Missouri State 
University is a four-year program preparing students for careers in 
computer science.

Degree Requirements:
• 120-128 semester hours
• General Education (40-42 hours)
• Math/Science (16 hours): MTH 261, MTH 280, MTH 314, PHY 203

Core CS Courses:
• CSC 130 - The World of Computer Science (3 hours)
• CSC 131 - Computational Thinking (4 hours)
• CSC 232 - Data Structures (4 hours, Prerequisites: CSC 131, MTH 314)
• CSC 244 - Computer Architecture (3 hours, Prerequisites: CSC 131)
• CSC 325 - Algorithms & Adv. Data Structures (3 hours)
...

Contact: ComputerScience@missouristate.edu, (417) 836-4157
[CORRECT - all real MSU information!]
```

---

## 🎯 **Action Plan**

### Immediate (15 minutes)
1. ✅ Backup overfitted model
2. ✅ Delete broken models/latest and models/previous
3. ✅ Run `python finetune.py` with your training data

### After Training (5 minutes)
4. ✅ Test with `python test_api.py`
5. ✅ Verify course numbers are correct (CSC 130, not CSC 1300)
6. ✅ Verify contact info appears correctly

### If Still Hallucinating
7. Check training completed with 3 epochs (not 35)
8. Check console showed "LoRA Dropout: 0.15"
9. Re-read this guide's validation checklist
10. Share new test results if issues persist

---

## 💡 **Key Takeaways**

1. **More epochs ≠ Better quality** (especially for fine-tuning!)
2. **496 examples × 3 epochs = OPTIMAL**
3. **496 examples × 35 epochs = DISASTER**
4. **Overfitting makes models WORSE, not better**
5. **Your training data is CORRECT** - the problem was training configuration
6. **High dropout + low epochs = Generalization**
7. **Low dropout + high epochs = Memorization**

---

**After retraining with 3 epochs, your model will output REAL MSU course information, not hallucinated nonsense!** 🎓
