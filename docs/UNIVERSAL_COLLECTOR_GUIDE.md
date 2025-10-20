# 🌐 Universal MSU Data Collector - Complete Guide

## ✨ **What Changed: Now FULLY FLEXIBLE!**

### **Before (Limited):**
- ❌ Only scholarships
- ❌ Fixed categories
- ❌ Hardcoded URLs

### **Now (Unlimited!):**
- ✅ **ANY topic** on MSU website
- ✅ **ANY page** you want
- ✅ Academics, courses, housing, services, admissions, **anything!**

---

## 🚀 **How to Use**

### **Run the Tool:**
```bash
python msu_collector.py
```

### **You'll See 4 Options:**

```
================================================================================
UNIVERSAL MSU DATA COLLECTOR
================================================================================

Collect data from ANY page on Missouri State University website!

Options:
  1. Enter specific MSU URL
  2. Browse suggested pages by category
  3. Enter search keywords (auto-find relevant pages)
  4. Batch collect from multiple URLs
================================================================================
```

---

## 📖 **Option 1: Enter Specific URL**

**Best for:** When you know exactly what page you want

### **Example:**
```
📝 Select option (1-4): 1

Enter URL examples:
  - /admissions/freshman.htm
  - /academics/biology/
  - https://www.missouristate.edu/registrar/

📝 Enter URL: /academics/computerscience/

📝 Topic name: computer_science_program

✅ Will collect data and save to: msu_computer_science_program_training.json
```

### **Works with:**
- `/admissions/costs.htm` → Tuition costs
- `/academics/english/` → English department  
- `/housing/residence-halls.htm` → Dorm information
- `/careers/` → Career services
- `/library/` → Library info
- `/registrar/calendars.htm` → Academic calendar
- **ANY MSU page!**

---

## 📚 **Option 2: Browse Categories**

**Best for:** Exploring what's available

### **Example:**
```
📝 Select option (1-4): 2

Categories:
  1. Scholarships
  2. Academics
  3. Admissions
  4. Campus Life
  5. Costs & Aid
  6. Student Services
  7. Graduate Programs

📝 Select category: 3

Admissions pages:
  1. /admissions/
  2. /admissions/freshman.htm
  3. /admissions/transfer.htm
  4. /admissions/international.htm
  5. Custom URL in this category

📝 Select page: 2

✅ Will collect freshman admissions data
```

---

## 🔍 **Option 3: Search Keywords**

**Best for:** Finding pages by topic

### **Example:**
```
📝 Select option (1-4): 3

Enter keywords: biology major requirements

💡 Searching MSU website for: 'biology major requirements'

📝 Enter URL: /academics/biology/
📝 Topic name: biology_requirements
```

---

## 📦 **Option 4: Batch Collection**

**Best for:** Collecting multiple topics at once

### **Example:**
```
📝 Select option (1-4): 4

Enter multiple URLs (one per line).
Format: URL,topic_name

📝 URL,topic: /admissions/freshman.htm,freshman_admission
  ✅ Added: freshman_admission

📝 URL,topic: /housing/,campus_housing
  ✅ Added: campus_housing

📝 URL,topic: /academics/biology/,biology_program
  ✅ Added: biology_program

📝 URL,topic: DONE

✅ Will collect all 3 topics automatically!
```

---

## 🎯 **Real-World Examples**

### **Example 1: Computer Science Program**
```bash
python msu_collector.py
# Select: 1 (Custom URL)
# URL: /academics/computerscience/
# Topic: cs_program
# Output: msu_cs_program_training.json
```

### **Example 2: Housing Information**
```bash
python msu_collector.py
# Select: 1
# URL: /housing/residence-halls.htm
# Topic: dorms
# Output: msu_dorms_training.json
```

### **Example 3: Graduate Admissions**
```bash
python msu_collector.py
# Select: 2 (Browse categories)
# Category: Graduate Programs
# Select specific grad page
# Output: msu_graduate_admissions_training.json
```

### **Example 4: Multiple Topics at Once**
```bash
python msu_collector.py
# Select: 4 (Batch)
# Add:
#   /admissions/costs.htm,tuition
#   /financialaid/,financial_aid
#   /academics/biology/,biology
#   /housing/,housing
# Output: 4 different JSON files!
```

---

## 📊 **What You Can Collect**

### **Academics:**
- `/academics/` - Overview
- `/academics/[department]/` - Any department
- `/catalog/` - Course catalog
- `/registrar/` - Registration info

### **Admissions:**
- `/admissions/` - General info
- `/admissions/freshman.htm` - Freshman requirements
- `/admissions/transfer.htm` - Transfer requirements
- `/admissions/international.htm` - International students
- `/admissions/costs.htm` - Tuition & fees

### **Student Life:**
- `/housing/` - Housing options
- `/dining/` - Meal plans
- `/campuslife/` - Activities
- `/recreation/` - Rec center

### **Services:**
- `/careers/` - Career services
- `/health/` - Health services
- `/counseling/` - Counseling
- `/library/` - Library
- `/tutoring/` - Tutoring services

### **Financial:**
- `/financialaid/` - Financial aid
- `/bursar/` - Payment info
- `/financialaid/scholarships.htm` - Scholarships

### **Graduate:**
- `/graduate/` - Graduate programs
- `/graduatecollege/` - Graduate college info

### **Literally ANY MSU Page:**
Just enter the URL and topic name!

---

## 💡 **Pro Tips**

### **1. Start Specific:**
```bash
# Good: /academics/computerscience/
# Not: /academics/ (too broad)
```

### **2. Meaningful Topic Names:**
```bash
# Good: cs_program, dorm_housing, grad_admission
# Not: page1, stuff, data
```

### **3. Review Before Training:**
```bash
# Always check the JSON file first
cat msu_cs_program_training.json
```

### **4. Combine Related Topics:**
```python
import json

# Merge multiple files
files = [
    'msu_freshman_admission_training.json',
    'msu_transfer_admission_training.json'
]

combined = []
for f in files:
    with open(f) as file:
        combined.extend(json.load(file))

with open('msu_all_admissions.json', 'w') as f:
    json.dump(combined, f, indent=2)
```

### **5. Collect Gradually:**
```bash
# Day 1: Collect scholarships
# Day 2: Collect admissions  
# Day 3: Collect academics
# Then train with combined data!
```

---

## 🎓 **Complete Workflow Example**

### **Goal: Create AI Assistant for MSU Freshmen**

```bash
# 1. Collect relevant topics
python msu_collector.py

# Collect these:
- Freshman admissions (/admissions/freshman.htm)
- Freshman scholarships (/FinancialAid/Scholarships/Freshman.htm)
- Housing (/housing/)
- Campus life (/campuslife/)
- Tuition costs (/admissions/costs.htm)

# 2. Review generated files
ls msu_*_training.json

# 3. Combine files (optional)
python combine_data.py  # (create this script to merge)

# 4. Update finetune.py
# Use combined file or train with each separately

# 5. Train model
python finetune.py

# 6. Test with freshman questions
python chat.py
```

---

## 🔧 **Customization**

### **Add Your Own Categories:**
Edit `msu_collector.py` line 25:
```python
self.suggested_pages = {
    'Your Category': [
        '/your/url1.htm',
        '/your/url2.htm',
    ],
}
```

### **Adjust Question Generation:**
The tool automatically generates relevant questions based on:
- Topic keywords (admission, scholarship, program, etc.)
- Title content
- Context

Questions adapt to ANY topic automatically!

---

## 📝 **Output Format**

### **Every topic creates:**
```json
[
  {
    "instruction": "Tell me about [topic].",
    "response": "Full content from MSU page..."
  },
  {
    "instruction": "What is [topic]?",
    "response": "Full content from MSU page..."
  },
  {
    "instruction": "How do I [action] for [topic]?",
    "response": "Full content from MSU page..."
  }
]
```

**Ready for training immediately!**

---

## ✅ **Summary**

### **What This Tool Does:**

| Feature | Description |
|---------|-------------|
| **Any URL** | Enter ANY MSU page URL |
| **Any Topic** | Scholarships, courses, housing, **anything** |
| **Smart Questions** | Auto-generates relevant questions |
| **Clean Data** | Removes navigation, formatting |
| **Organized** | Topic-based filenames |
| **Batch Mode** | Collect multiple at once |
| **Flexible** | 4 different ways to collect |

### **No Limitations:**
- ❌ Not restricted to scholarships
- ✅ Works with **any MSU webpage**
- ✅ **You control** what to collect
- ✅ **Unlimited topics**

---

## 🚀 **Ready to Use!**

```bash
python msu_collector.py
```

**Collect data about:**
- 🎓 Academics & Programs
- 💰 Scholarships & Financial Aid
- 🏠 Housing & Campus Life
- 📚 Courses & Majors
- 🎯 Admissions & Requirements
- 🔬 Research & Labs
- 🏅 Student Services
- 🎉 Events & Activities
- **...Anything on MSU website!**

---

## ❓ **Questions?**

Just ask! The tool is:
- ✅ Fully flexible
- ✅ Works with ANY MSU page
- ✅ Easy to use
- ✅ Creates training-ready data

**Go collect some data! 🎉**
