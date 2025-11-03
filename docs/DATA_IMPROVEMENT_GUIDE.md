# 📊 Data Improvement Guide for BearChat Training

## ❌ **Critical Issues Found in Current Data**

### **1. Missing Responses (CS Degree Data)**
```json
// ❌ BAD - No response field!
{
  "instruction": "To graduate with Bachelors of Computer Science you need at least 120 hours of courses.",
  "metadata": {...}
}

// ✅ GOOD - Has both instruction AND response
{
  "instruction": "How many credit hours do I need to graduate with a CS degree?",
  "response": "You need at least 120 credit hours to graduate with a Bachelors of Computer Science from Missouri State University.",
  "metadata": {...}
}
```

### **2. Duplicate Questions**
```json
// ❌ BAD - Same question 3 times!
"What is the Cost of Attendance at Missouri State University?"
"What is the Cost of Attendance program at MSU?"
"What is the Cost of Attendance?"

// ✅ GOOD - Varied, natural questions
"What is the Cost of Attendance at MSU?"
"How much does it cost to attend Missouri State?"
"Can you explain COA?"
"What expenses are included in the Cost of Attendance?"
"Is COA the same as actual tuition?"
```

### **3. Wall-of-Text Responses**
```json
// ❌ BAD - Unreadable course dump
"response": "Core Computer Science Courses: CSC 130(3) The World of Computer Science , CSC 131(4) Computational Thinking, CSC 232(4) Data Structures, CSC 244(3) Computer Architecture, CSC 325(3) Algorithms & Adv. Data Structures..."

// ✅ GOOD - Structured, scannable
"response": "The Computer Science degree requires these core courses:\n\n**Programming Foundation:**\n- CSC 130: The World of Computer Science (3 credits)\n- CSC 131: Computational Thinking (4 credits)\n- CSC 232: Data Structures (4 credits)\n\n**Systems:**\n- CSC 244: Computer Architecture (3 credits)\n- CSC 360: Operating Systems (3 credits)\n\n**Theory:**\n- CSC 325: Algorithms & Advanced Data Structures (3 credits)\n- CSC 333: Language & Machines (2 credits)\n\nPlus 9 elective hours from CSC 300-596 courses."
```

### **4. Poor Question Variety**
```json
// ❌ BAD - All identical format
"what are the courses a student should take to complete Bachelors of Computer Science?"
"what are the Bachelors of Computer Science, academic year 2025-2026 courses..."

// ✅ GOOD - Natural, varied questions
"What classes do I need for a CS degree?"
"Can you list the required CS courses?"
"What's the curriculum for Computer Science majors?"
"Tell me about the CS degree requirements"
"I'm interested in CS - what courses will I take?"
```

---

## ✅ **How to Create Better Training Data**

### **Formula: 1 Topic = 5-10 Question Variations**

#### **Example: Cost of Attendance**

```json
[
  {
    "instruction": "What is the Cost of Attendance?",
    "response": "The Cost of Attendance (COA) is an estimate of your total educational expenses for the year. It includes tuition, fees, housing, meals, books, transportation, and personal expenses. The federal government requires all schools to calculate this before awarding financial aid.",
    "metadata": {
      "topic": "Cost of Attendance",
      "content_type": "general_info"
    }
  },
  {
    "instruction": "How much does MSU cost?",
    "response": "The actual cost varies by student, but Missouri State calculates a Cost of Attendance (COA) based on average student expenses. This includes tuition, fees, housing, meals, books, and other costs. Your actual expenses may differ from the COA estimate.",
    "metadata": {
      "topic": "Cost of Attendance",
      "content_type": "general_info"
    }
  },
  {
    "instruction": "Is COA the same as tuition?",
    "response": "No, the Cost of Attendance (COA) is more comprehensive than just tuition. While tuition is a major component, COA also includes fees, housing, meals, books, supplies, transportation, and personal expenses. It represents your total estimated cost to attend MSU for a year.",
    "metadata": {
      "topic": "Cost of Attendance",
      "content_type": "comparison"
    }
  },
  {
    "instruction": "Why is my actual cost different from COA?",
    "response": "The Cost of Attendance uses averages and includes all possible expense categories. Your actual costs may be lower if you live at home, have scholarships, or spend less on books. It may be higher if you have special needs or choose premium housing. COA is an estimate for planning purposes.",
    "metadata": {
      "topic": "Cost of Attendance",
      "content_type": "explanation"
    }
  }
]
```

---

## 📋 **Data Quality Checklist**

Before adding data, verify:

- [ ] **Every entry has BOTH `instruction` and `response`**
- [ ] **Responses are 50-200 words** (not 5 or 500)
- [ ] **Questions are conversational** ("What's...?" not "Provide information about...")
- [ ] **No duplicate questions** (vary wording for same topic)
- [ ] **Use formatting** (bullet points, **bold**, line breaks)
- [ ] **Responses are complete sentences** (not fragments)
- [ ] **Metadata is accurate** (topic, content_type match the Q&A)
- [ ] **Natural language** (how students actually ask questions)

---

## 🎯 **Question Variation Patterns**

### **For "Requirements" Topics:**
1. "What do I need to...?"
2. "How do I qualify for...?"
3. "What are the requirements for...?"
4. "Can you explain the [X] requirements?"
5. "I want to [X], what should I do?"

### **For "Process" Topics:**
1. "How do I...?"
2. "What's the process for...?"
3. "Can you walk me through...?"
4. "What steps do I take to...?"
5. "I need to [X], where do I start?"

### **For "Information" Topics:**
1. "What is...?"
2. "Can you explain...?"
3. "Tell me about...?"
4. "I'm confused about..."
5. "What's the difference between... and...?"

---

## 🔧 **Quick Fixes for Current Data**

### **Fix 1: Add Missing Responses**
```python
# Run this script to find entries missing responses
import json

with open('your_data.json', 'r') as f:
    data = json.load(f)

missing_response = [item for item in data if 'response' not in item]
print(f"Found {len(missing_response)} entries without responses")
for item in missing_response:
    print(f"- {item['instruction'][:60]}...")
```

### **Fix 2: Remove Duplicates**
```python
# Group identical responses and vary questions
seen = {}
for item in data:
    response = item['response']
    if response in seen:
        print(f"DUPLICATE: {item['instruction']}")
    else:
        seen[response] = item
```

### **Fix 3: Format Long Responses**
```python
# Split course lists into readable sections
def format_course_list(courses_text):
    # Split by category, add headers, use bullet points
    return formatted_text
```

---

## 💡 **Pro Tips**

1. **Think Like a Student**: How would you ask this question to a friend?
2. **Test Your Data**: Can you answer the question in 1-2 paragraphs?
3. **Use Real Examples**: Include actual course codes, dates, numbers
4. **Stay Consistent**: Same topic = same metadata
5. **Quality > Quantity**: 50 great examples beats 500 mediocre ones

---

## 📊 **Ideal Data Distribution**

For a well-balanced dataset:
- **40%** General info questions (what/who/where)
- **30%** Process questions (how/when)
- **20%** Comparison questions (difference/vs/or)
- **10%** Follow-up questions (why/more details)

---

## 🚀 **Next Steps**

1. **Audit Current Data**: Check for missing responses, duplicates
2. **Enhance CS Degree Data**: Break down course lists, add variety
3. **Add Conversational Examples**: Include casual language
4. **Balance Topics**: Ensure each topic has 5-10 variations
5. **Test with Model**: Train and see if responses improve

Remember: **The model can only be as good as the data you feed it!** 🎓
