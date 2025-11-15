# Web Search Data Collection - Quick Reference

## 📦 What You Got

### Automatic Data Collection
Every web search interaction is automatically saved to:
```
web_search_data_collection.txt
```

Format: **JSON Lines** (one entry per line)

### Converter Tool
```bash
python3 convert_web_search_data.py
```

Converts collected data to training-ready format.

---

## 🚀 Quick Start

### 1. Use Your App
- Enable web search toggle (🌐 button)
- Ask questions
- Data saves automatically ✅

### 2. Check Progress
```bash
python3 convert_web_search_data.py stats
```

### 3. View Recent Entries
```bash
python3 convert_web_search_data.py view 5
```

### 4. Convert When Ready
```bash
python3 convert_web_search_data.py convert
```

Output: `web_search_training_data.json`

---

## 📊 Commands

| Command | What It Does |
|---------|--------------|
| `python3 convert_web_search_data.py` | Show stats + convert |
| `python3 convert_web_search_data.py stats` | Show statistics |
| `python3 convert_web_search_data.py view 10` | View last 10 entries |
| `python3 convert_web_search_data.py convert` | Convert to training format |

---

## 📈 Collection Goals

| Phase | Target | Purpose |
|-------|--------|---------|
| **Phase 1** | 50-100 entries | Initial dataset |
| **Phase 2** | 200-500 entries | Diverse coverage |
| **Phase 3** | 1000+ entries | Production quality |

---

## 🔄 Fine-Tuning Workflow

```
1. Collect 100+ entries
   ↓
2. python3 convert_web_search_data.py convert
   ↓
3. Merge with existing training data
   ↓
4. python3 finetune.py
   ↓
5. Test improved model
   ↓
6. Repeat!
```

---

## ✅ What's Collected

- ✅ Questions (anonymous)
- ✅ Answers with web sources
- ✅ Citations (URLs, titles)
- ✅ Topic classification
- ✅ Timestamps
- ❌ No personal data

---

## 🎯 Data Quality

**Good Examples:**
```
Q: What are the current CS course offerings?
A: Based on the Missouri State University website...
Citations: 3 MSU sources
```

**Poor Examples:**
```
Q: Hi
A: Hello!
Citations: 0
```

System automatically filters casual conversations.

---

## 📁 File Structure

```
web_search_data_collection.txt    ← Raw collected data (JSON Lines)
web_search_training_data.json     ← Converted for training
convert_web_search_data.py        ← Conversion tool
```

---

## 💡 Pro Tips

1. **Let it collect naturally** - Don't force queries
2. **Review weekly** - Check stats and quality
3. **Convert monthly** - Prepare training batches
4. **Backup before fine-tuning** - Never lose data
5. **Combine datasets** - Web search + manual = best

---

## 🔍 Example Workflow

**Week 1:**
```bash
# Just use the app, data collects automatically
# End of week:
python3 convert_web_search_data.py stats
# Output: 45 entries collected
```

**Week 2-3:**
```bash
# Continue using, reach 100+ entries
python3 convert_web_search_data.py view 20
# Review quality, looks good!
```

**Week 4:**
```bash
# Convert and prepare for training
python3 convert_web_search_data.py convert
# Merge with existing data
# Fine-tune model
# Deploy improved version!
```

---

## 📊 Expected Data

**After 1 month** (moderate usage):
- ~300-500 entries
- File size: ~500 KB - 1 MB
- Training data: Ready to use

**Topics covered:**
- Admissions (30%)
- Academic programs (25%)
- Course information (20%)
- Campus life (15%)
- Faculty/staff (10%)

---

## 🛠️ Maintenance

**Daily:** Nothing! Automatic  
**Weekly:** Check stats  
**Monthly:** Convert + review  
**Quarterly:** Fine-tune model  

---

## 🎉 Benefits

✅ Continuously improving dataset  
✅ Real user queries (not synthetic)  
✅ Verified with web sources  
✅ Up-to-date information  
✅ Zero manual effort  
✅ Ready for fine-tuning  

---

**Status**: 🟢 Active - Collecting Now!  
**Format**: JSON Lines → Training JSON  
**Privacy**: ✅ Anonymous, no PII  
**Effort**: 🤖 Fully Automatic
