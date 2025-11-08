# Conversation Memory Feature - Implementation Guide

## What Was Added

Added conversation memory so the model can answer follow-up questions naturally by remembering the last 3 Q&A pairs.

### Example Conversation:
```
User: "What is the Computer Science program?"
Bot: "The BS in Computer Science is a 4-year, 120-credit hour program..."

User: "What courses are in the first year?"  ← No need to say "CS program"!
Bot: "In the first year, you'll take CSC 130, CSC 131..." ← Knows context!

User: "How long does it take?"  ← Using "it"!
Bot: "The program takes 4 years to complete..." ← Still knows we're talking about CS!
```

---

## Changes Made

### 1. API Server (`api_server.py`)

**Updated `generate_response()` function:**
- Added `conversation_history` parameter
- Builds conversation context from last 3 Q&A pairs
- Includes history in the prompt so model sees previous exchanges

**Updated `/chat` endpoint:**
- Now accepts optional `conversation_history` array
- Format: `[{"question": "...", "answer": "..."}, ...]`
- Validates history format
- Passes history to `generate_response()`

### 2. Flutter App (`bearchat_ai/lib/api_service.dart`)

**Updated `sendMessage()` function:**
- Automatically builds history from last 6 messages (3 Q&A pairs)
- Filters out incomplete pairs
- Sends history with each request
- No changes needed to UI code!

---

## How It Works

### Request Format (NEW):
```json
{
  "question": "What courses are in the first year?",
  "conversation_history": [
    {
      "question": "What is the CS program?",
      "answer": "The BS in Computer Science is a 4-year program..."
    }
  ]
}
```

### What Happens Internally:
1. Flutter app tracks all messages
2. On new question, takes last 3 Q&A pairs
3. Sends them with current question
4. API builds prompt with history:
   ```
   ### Conversation History:
   User: What is the CS program?
   Assistant: The BS in Computer Science...
   
   ### Instruction:
   What courses are in the first year?
   
   ### Response:
   ```
5. Model sees context and answers naturally!

---

## Testing

### Method 1: Use Python Test Script
```bash
# Make sure API server is running in another terminal
python test_conversation_memory.py
```

### Method 2: Test from Flutter App
Just use the app normally! The conversation memory is automatic:

1. Ask: "What is the Computer Science program?"
2. Then ask: "What are the first year courses?" (no need to say "CS program" again!)
3. Then ask: "How long is it?" (model knows "it" = CS program)

### Method 3: Test with curl
```bash
# First question
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the CS program?"
  }'

# Follow-up question WITH history
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What courses are in year 1?",
    "conversation_history": [
      {
        "question": "What is the CS program?",
        "answer": "The previous answer here..."
      }
    ]
  }'
```

---

## Configuration

### How Many Messages to Remember?

**Current: Last 3 Q&A pairs (6 messages total)**

To change this, edit `api_service.dart`:
```dart
// Change 6 to different number:
// 4 = 2 Q&A pairs
// 8 = 4 Q&A pairs
// 10 = 5 Q&A pairs
int startIndex = conversationHistory.length > 6 ? conversationHistory.length - 6 : 0;
```

And in `api_server.py`:
```python
# Change -3 to different number:
for i, exchange in enumerate(conversation_history[-3:], 1):  # Last 3 exchanges
```

### Why Only 3 Pairs?

- **Token limit:** Too much history uses up the 512 max_new_tokens
- **Relevance:** Older messages are usually not relevant
- **Performance:** Less context = faster generation

**Recommended:** 3-5 pairs maximum

---

## Benefits

1. **Natural conversations** - No need to repeat context
2. **Better UX** - Users can ask follow-up questions naturally
3. **No retraining needed** - Works with existing model
4. **Lightweight** - No database, just in-memory tracking
5. **Works offline** - History tracked locally in Flutter app

---

## Restart Instructions

### 1. Restart API Server:
```bash
# Stop current server (CTRL+C in Python terminal)
# Restart:
python api_server.py
```

### 2. Restart Flutter App:
```bash
# In dart terminal:
flutter run
# Or just hot reload if already running: press 'r'
```

### 3. Test It:
Ask a question, then ask a follow-up using pronouns like "it", "that", "the program", etc.

---

## Troubleshooting

**Q: Model doesn't remember context?**
- Check server logs - history should appear in prompt
- Verify Flutter is sending `conversation_history` in request
- Make sure history format is correct: `[{"question": "...", "answer": "..."}]`

**Q: Getting timeout errors?**
- History adds tokens, may slow generation
- Reduce history size (2 pairs instead of 3)
- Or increase timeout in `api_service.dart` from 120s to 180s

**Q: Model gives wrong context?**
- History might include irrelevant old questions
- Try reducing to 2 Q&A pairs instead of 3
- Or clear history when user changes topics

---

## Next Steps (Optional Enhancements)

1. **Add "Clear History" button** - Let users start fresh conversation
2. **Smart history filtering** - Only include relevant previous Q&As
3. **Topic detection** - Auto-clear history when topic changes
4. **Session persistence** - Save history to local storage (Flutter)
5. **Multi-user support** - Use session IDs to track different conversations

---

## That's It!

You now have a chatbot with conversation memory. The model can handle follow-up questions naturally without requiring users to repeat context. 

Simple, lightweight, and works with your existing fine-tuned model!
