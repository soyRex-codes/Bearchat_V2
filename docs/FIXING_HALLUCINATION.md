# Fixing Model Hallucination Problem

## 🚨 The Problem

**What you saw:**
```
You: tell me about the Computer science degree msu offer?
Assistant: Okay, let's dive into the Computer Science degree offered at 
Montana State University (MSU)...  ❌ WRONG UNIVERSITY!
```

**Why this happens:**
1. Base model (Gemma 3-1B) has tons of general knowledge about ALL universities
2. Your fine-tuning data is small (maybe 30-100 examples)
3. Base knowledge overpowers fine-tuning
4. Model defaults to what it "knows" (Montana State, Michigan State, etc.)

---

## ✅ Solutions (Multiple Approaches)

### **Solution 1: Constrained Prompting** ⭐ QUICK FIX

**What**: Add explicit constraints in the prompt

**Updated `chat.py`** (Already done! ✓):
```python
prompt = f"""### Instruction:
You are an assistant for Missouri State University (MSU) in Springfield, Missouri. 
Only provide information based on Missouri State University data. 
If you don't have specific information about MSU, say so clearly. 
Do not provide information about other universities.

Question: {question}

### Response:
"""
```

**Benefits:**
- ✅ Works immediately (no retraining)
- ✅ Explicitly tells model to stay on topic
- ✅ Mentions "Springfield, Missouri" to differentiate from other MSUs

**Generation parameters also tuned:**
- `temperature=0.3` (was 0.7) → Less random, more focused
- `top_p=0.85` (was 0.9) → Less diverse tokens
- `repetition_penalty=1.1` → Prevents loops

---

### **Solution 2: More Training Data** 📚 LONG-TERM FIX

**Problem**: 30-100 examples vs millions in base model

**Solution**: Collect WAY more data!

**Target**: 500-1000+ examples across multiple topics

```bash
# Collect data from multiple MSU pages
python smart_msu_collector.py

# Topics to collect:
# - Computer Science program (Done ✓)
# - Other majors (Nursing, Business, etc.)
# - Scholarships (10+ scholarship pages)
# - Admissions (Freshman, Transfer, International)
# - Housing (All residence halls)
# - Campus Life
# - Financial Aid
# - Graduate Programs
# - Student Services
```

**Why this works:**
- More examples = stronger fine-tuning
- Overrides base model's general knowledge
- Model learns MSU-specific patterns

---

### **Solution 3: Use Contextual Training** 🎯 BEST LONG-TERM

**What**: Include topic/category in BOTH training AND inference

**Training** (use `enhanced_finetune.py`):
```
### Topic: BS Computer Science Degree Plan
### Category: Academic Program
### Instruction: [question]
### Response: [answer]
```

**Inference** (use `chat_contextual.py`):
```
### Topic: BS Computer Science Degree Plan
### Category: Academic Program
### Instruction: [question]
### Response: [answer]
```

**Why this works:**
- Model trained with context → expects context at inference
- Topic+Category acts as "routing signal"
- Model stays within the specified domain

---

### **Solution 4: Stricter Generation Parameters** 🎛️

**Current (in updated chat.py):**
```python
temperature=0.3,     # Low = more deterministic
top_p=0.85,         # Lower = less randomness
repetition_penalty=1.1  # Prevent loops
```

**Even stricter (if needed):**
```python
temperature=0.1,     # Very focused
top_p=0.75,         # Very constrained
do_sample=False,    # Greedy decoding (most likely tokens only)
```

---

### **Solution 5: System Prompt Engineering** 📝

**Add more context to every prompt:**

```python
SYSTEM_PROMPT = """You are the official Missouri State University (MSU) assistant.

KEY FACTS:
- Missouri State University is located in Springfield, Missouri
- MSU is NOT Montana State, Michigan State, or any other university
- Only answer based on Missouri State University information
- If you don't have MSU-specific information, say: "I don't have that information for Missouri State University"
- NEVER make up information about MSU
- NEVER mention other universities

"""

prompt = f"""{SYSTEM_PROMPT}

### Instruction:
{question}

### Response:
"""
```

---

## 🎯 Recommended Approach (Combination)

### **Phase 1: Immediate Fix** (Today)
1. ✅ Use updated `chat.py` (already done)
2. ✅ Lower temperature to 0.3
3. ✅ Add explicit constraints in prompt

**Test now:**
```bash
python chat.py
```

---

### **Phase 2: Better Training** (Next)
1. Collect MORE data (aim for 500+ examples)
2. Cover multiple topics (not just CS degree)
3. Retrain with `enhanced_finetune.py`
4. Use `chat_contextual.py` for inference

**Collect data:**
```bash
python smart_msu_collector.py

# Suggested pages to scrape:
# - All CS department pages
# - All scholarship pages
# - All admissions pages
# - Housing pages
# - Financial aid pages
```

---

### **Phase 3: Advanced (Optional)**
1. Increase training epochs (2 → 5)
2. Collect 1000+ examples
3. Use learning rate scheduler
4. Add validation set

---

## 📊 Expected Results

### After Phase 1 (Constrained Prompting):
```
You: tell me about the Computer science degree msu offer?
Assistant: Missouri State University offers a BS in Computer Science...
          Based on the degree plan, you'll take courses like...
```
✅ Stays on topic!

### After Phase 2 (More Data + Context):
```
You: tell me about the Computer science degree msu offer?
[Topic: BS Computer Science]
Assistant: Missouri State University offers an ABET-accredited BS in 
          Computer Science. The program includes...
```
✅ Context-aware + more detailed!

---

## 🔧 Files Available

1. **`chat.py`** (Updated) ⭐
   - Includes constrained prompts
   - Better generation parameters
   - Use with current model

2. **`chat_contextual.py`** (New)
   - For models trained with `enhanced_finetune.py`
   - Auto-detects topic/category
   - More context-aware

3. **`enhanced_finetune.py`** (Previously created)
   - Trains with topic+category context
   - Better for multi-domain data

---

## 🚀 What to Do Right Now

```bash
# 1. Test the improved chat
python chat.py

# Ask: "Tell me about Missouri State University's Computer Science program"
# Should now stay focused on MSU!

# 2. If still hallucinating, collect MORE data
python smart_msu_collector.py

# 3. Retrain with more data
python enhanced_finetune.py

# 4. Use contextual chat
python chat_contextual.py
```

---

## 💡 Key Insights

**Why small fine-tuning fails:**
- Base model: Millions of examples about ALL universities
- Your data: 30-100 examples about MSU
- Result: Base knowledge dominates

**How to win:**
1. **More data** (quantity) - 500+ examples
2. **Constrained prompts** (explicit boundaries)
3. **Contextual training** (topic awareness)
4. **Lower temperature** (less creativity)

**Bottom line**: You need MORE MSU-specific training data! The model needs to see "Missouri State University in Springfield, Missouri" hundreds of times to override its base knowledge.

---

## ✅ Action Plan

**Today:**
- [x] Updated chat.py with constraints
- [ ] Test with `python chat.py`

**This Week:**
- [ ] Collect 10+ more MSU pages (scholarships, housing, etc.)
- [ ] Combine all JSON files
- [ ] Retrain with `enhanced_finetune.py`

**Goal**: 500+ training examples = model stays focused on MSU! 🎯
