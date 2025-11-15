# Web Search Toggle Feature - Quick Guide

## What Changed

Added a **user-controlled toggle button** for web search in the Flutter app, giving users full control over when to use web search vs. model-only responses.

## Features

✅ **Toggle button in AppBar** - Globe icon that turns green when enabled  
✅ **Visual feedback** - Shows tooltip and snackbar notification  
✅ **Saves API quota** - Only searches when user enables it  
✅ **Smart defaults** - Starts disabled (model-only mode)  
✅ **Instant toggle** - No app restart needed  

---

## How to Use

### For Users:

1. **Look for the globe icon** 🌐 in the top-right of the app (next to delete button)

2. **Tap to toggle:**
   - **Gray/outlined**: Web search OFF (faster, model knowledge only)
   - **Green/filled**: Web search ON (searches MSU websites for current info)

3. **You'll see a notification:**
   - "🔍 Web search enabled - Will search MSU websites for current info"
   - "📚 Web search disabled - Using model knowledge only"

4. **Ask your question** - The system respects your preference

---

## When to Enable Web Search

### ✅ Enable when you need:
- Current information (dates, schedules, recent changes)
- Latest updates (admission requirements, course offerings)
- Specific facts from MSU website
- Verified sources with citations

### ❌ Keep disabled when:
- Asking general questions
- Casual conversation
- Already know the info might be in model's training data
- Want faster responses
- Want to save API quota

---

## Visual Guide

```
┌──────────────────────────────────────┐
│  BearChat           🌐  🗑️           │ ← Toggle button here
├──────────────────────────────────────┤
│                                      │
│  User: What are current CS courses?  │
│                                      │
│  BearChat: [Response with sources]   │
│  ┌────────────────────────────────┐  │
│  │ 🔍 Sources (3)                 │  │ ← Citations appear
│  │ [1] MSU CS Courses 2024-25     │  │    when enabled
│  │     missouristate.edu/...      │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## Technical Details

### Frontend (Flutter):
- **State variable**: `_webSearchEnabled` (boolean)
- **Default**: `false` (disabled)
- **Location**: AppBar actions, before delete button
- **Icons**: 
  - OFF: `Icons.travel_explore_outlined` (gray)
  - ON: `Icons.travel_explore` (green)

### Backend (Python):
- **Parameter**: `web_search_enabled` (boolean)
- **Endpoint**: `/chat` (POST)
- **Behavior**: Only performs search if:
  1. User enabled toggle (`web_search_enabled=true`)
  2. Search engine available (credentials configured)
  3. Query needs current information (automatic detection)

### API Request:
```json
{
  "question": "What are current CS courses?",
  "conversation_history": [...],
  "web_search_enabled": true  ← New parameter
}
```

---

## Resource Savings

**Scenario**: 100 questions asked

| Mode | API Calls | Cost |
|------|-----------|------|
| Always ON | ~30 searches | Uses quota |
| Toggle (selective) | ~10 searches | Saves 67% |
| Always OFF | 0 searches | No quota used |

**Best practice**: Enable only when you need current/verified info!

---

## Troubleshooting

### Toggle button not working?
- Check if API server is running
- Verify Google API credentials in `.env`
- Look for initialization message: "✓ Web search engine initialized"

### Citations not showing?
- Make sure toggle is enabled (green)
- Ask a question with "current", "latest", or "2025"
- Check server logs for "🔍 Performing web search"

### Want to change default state?
Edit `main.dart`:
```dart
bool _webSearchEnabled = true; // Start with web search ON
```

---

## Comparison to ChatGPT

This works similar to ChatGPT's web browsing toggle:
- **ChatGPT**: Click "Browse with Bing" before asking
- **BearChat**: Toggle globe icon before asking
- **Both**: User decides when to search vs. use model knowledge

---

## Summary

**Before**: Web search was automatic (always tried to search)  
**After**: User controls when to search (saves resources)

**Benefits**:
- ✅ User control
- ✅ Saves API quota
- ✅ Faster responses (when disabled)
- ✅ Modern UX pattern (like ChatGPT)
- ✅ Clear visual feedback

---

**Implementation Date**: November 14, 2025  
**Status**: ✅ Complete & Ready to Use
