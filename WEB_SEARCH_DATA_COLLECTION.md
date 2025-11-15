# Web Search Data Collection for Training

## Overview

Automatically collects web search queries and responses to build a training dataset for future model fine-tuning. Every time a user gets an answer with web search, the data is saved.

---

## How It Works

### Automatic Collection

When web search is used:
1. User enables web search toggle
2. Asks a question (e.g., "What are current CS courses?")
3. System searches MSU websites
4. Generates response with citations
5. **Automatically saves** to `web_search_data_collection.txt`

### Data Format

**Saved as JSON Lines** (one JSON object per line):

```json
{
  "timestamp": "2025-11-14T10:30:45.123456",
  "question": "What are the current CS course offerings?",
  "answer": "Based on the Missouri State University website...",
  "topic": "Computer Science",
  "content_type": "academic_program",
  "citations": [
    {
      "title": "CS Course Catalog 2024-2025",
      "url": "https://www.missouristate.edu/cs/courses",
      "snippet": "..."
    }
  ],
  "source": "web_search",
  "model_version": "llama-3.2-3b-instruct-finetuned"
}
```

---

## Usage

### View Recent Entries

```bash
python3 convert_web_search_data.py view 10
```

Shows last 10 collected queries with details.

### Get Statistics

```bash
python3 convert_web_search_data.py stats
```

Shows:
- Total entries collected
- Date range
- Topic breakdown
- Citation statistics

### Convert to Training Format

```bash
python3 convert_web_search_data.py convert
```

Converts to standard fine-tuning format:

```json
[
  {
    "instruction": "What are the current CS course offerings?",
    "input": "",
    "output": "Based on the Missouri State University website...",
    "topic": "Computer Science",
    "content_type": "academic_program",
    "metadata": {
      "source": "web_search",
      "date_collected": "2025-11-14",
      "citations": [...]
    }
  }
]
```

Output: `web_search_training_data.json` (ready for fine-tuning)

---

## Fine-Tuning Workflow

### 1. Collect Data (Automatic)

Just use your app normally with web search enabled. Data saves automatically.

```bash
# Check collection progress
python3 convert_web_search_data.py stats
```

### 2. Review & Clean (Recommended)

After collecting ~50-100 entries:

```bash
# View recent entries
python3 convert_web_search_data.py view 20

# Check for quality
# Look for:
# - Clear questions
# - Accurate answers
# - Relevant citations
```

### 3. Convert to Training Format

```bash
python3 convert_web_search_data.py convert
```

Creates `web_search_training_data.json`

### 4. Merge with Existing Training Data

```python
import json

# Load existing training data
with open('Json_data_storage/comprehensive_data_MSU.json', 'r') as f:
    existing_data = json.load(f)

# Load web search data
with open('web_search_training_data.json', 'r') as f:
    web_search_data = json.load(f)

# Merge
combined_data = existing_data + web_search_data

# Save
with open('Json_data_storage/training_data_with_web_search.json', 'w') as f:
    json.dump(combined_data, f, indent=2, ensure_ascii=False)

print(f"✅ Combined dataset: {len(combined_data)} entries")
```

### 5. Fine-Tune Model

Use your existing fine-tuning script:

```bash
python3 finetune.py --data Json_data_storage/training_data_with_web_search.json
```

---

## Data Quality Tips

### Good Training Examples

✅ **Clear, specific questions:**
- "What are the admission requirements for CS master's program?"
- "When is spring break 2025?"
- "Current CS faculty members"

✅ **Well-cited answers:**
- References specific MSU pages
- Includes dates and specific info
- Has 2-3 citations

✅ **Accurate information:**
- Directly from MSU website
- Current/recent data
- Verified facts

### Poor Training Examples

❌ **Vague questions:**
- "Tell me about MSU"
- "What's new?"

❌ **Generic answers:**
- No MSU-specific details
- Unverified information
- No citations

❌ **Errors:**
- Incorrect facts
- Broken citations
- Hallucinated information

---

## Monitoring Collection

### Real-time Monitoring

Watch the log when API server is running:

```
✓ Added 3 web sources to context
Generated response in 3.45s (245 tokens)
✓ Saved web search training data: What are current CS courses?...
```

### File Size Tracking

```bash
# Check collection file size
ls -lh web_search_data_collection.txt

# Count entries
wc -l web_search_data_collection.txt
```

### Periodic Review

**Weekly:**
```bash
python3 convert_web_search_data.py stats
```

**Monthly:**
```bash
python3 convert_web_search_data.py convert
# Review web_search_training_data.json
```

---

## Privacy & Data Management

### What's Collected

- ✅ User questions (anonymous)
- ✅ System responses
- ✅ Web citations
- ✅ Timestamps
- ❌ No user IDs
- ❌ No personal information

### Data Cleanup

**Remove specific entries:**
```python
import json

# Read all entries
with open('web_search_data_collection.txt', 'r') as f:
    entries = [json.loads(line) for line in f if line.strip()]

# Filter out unwanted entries
filtered = [e for e in entries if e['timestamp'] > '2025-11-01']

# Save back
with open('web_search_data_collection.txt', 'w') as f:
    for entry in filtered:
        f.write(json.dumps(entry) + '\n')
```

**Start fresh:**
```bash
# Backup first
cp web_search_data_collection.txt web_search_data_collection_backup.txt

# Clear file
> web_search_data_collection.txt
```

---

## Advanced Usage

### Custom Conversion

```python
from convert_web_search_data import convert_to_training_format

# Custom output location
convert_to_training_format(
    input_file='web_search_data_collection.txt',
    output_file='custom_training_data.json'
)
```

### Filter by Date Range

```python
import json
from datetime import datetime

entries = []
with open('web_search_data_collection.txt', 'r') as f:
    for line in f:
        entry = json.loads(line.strip())
        date = datetime.fromisoformat(entry['timestamp'].split('T')[0])
        
        # Only November 2025
        if date.month == 11 and date.year == 2025:
            entries.append(entry)

print(f"Filtered: {len(entries)} entries")
```

### Topic-Specific Training

```python
# Extract only CS-related queries
cs_entries = []
with open('web_search_data_collection.txt', 'r') as f:
    for line in f:
        entry = json.loads(line.strip())
        if 'Computer Science' in entry.get('topic', ''):
            cs_entries.append(entry)

# Save for CS-specific fine-tuning
with open('cs_specific_training.json', 'w') as f:
    json.dump(cs_entries, f, indent=2)
```

---

## Expected Growth

| Usage | Daily Entries | Weekly | Monthly |
|-------|---------------|--------|---------|
| **Light** (10 searches/day) | 10 | 70 | 300 |
| **Medium** (30 searches/day) | 30 | 210 | 900 |
| **Heavy** (100 searches/day) | 100 | 700 | 3,000 |

**File size**: ~1-2 KB per entry

- 100 entries ≈ 100-200 KB
- 1,000 entries ≈ 1-2 MB
- 10,000 entries ≈ 10-20 MB

---

## Best Practices

1. **Collect Before Fine-Tuning**
   - Gather 100-500 entries first
   - Covers diverse topics
   - Quality over quantity

2. **Regular Review**
   - Check statistics weekly
   - Review sample entries
   - Remove low-quality data

3. **Incremental Fine-Tuning**
   - Fine-tune with 100 entries
   - Test model improvements
   - Add 100 more, repeat

4. **Backup Regularly**
   ```bash
   cp web_search_data_collection.txt backups/web_search_$(date +%Y%m%d).txt
   ```

5. **Combine with Manual Data**
   - Web search data = current info
   - Manual training data = core knowledge
   - Best results = both combined

---

## Troubleshooting

### No data being collected?

Check:
- Web search toggle is enabled
- API server logs show "✓ Saved web search training data"
- File exists and has write permissions
- web_search_enabled=True in API requests

### File growing too large?

Options:
- Convert and archive monthly
- Filter by date range
- Extract topic-specific subsets
- Start fresh after conversion

### Conversion errors?

```bash
# Validate JSON format
python3 -c "
import json
with open('web_search_data_collection.txt') as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except Exception as e:
            print(f'Line {i}: {e}')
"
```

---

## Summary

✅ **Automatic** - Saves every web search interaction  
✅ **JSON Lines** - Easy to parse and append  
✅ **Rich metadata** - Citations, topics, timestamps  
✅ **Conversion tool** - Ready for fine-tuning  
✅ **Privacy-safe** - No personal data  
✅ **Incremental** - Grow dataset over time  

**Result**: Continuously improving model with real user queries and verified web sources!

---

**Implementation Date**: November 14, 2025  
**Status**: ✅ Active & Collecting
