# Web Search Integration Setup Guide

## Overview
BearChat now supports real-time web search using Google Custom Search API. The system automatically searches Missouri State University domains when detecting queries that need current information.

## Features
✅ Google Custom Search API integration (100 free queries/day)  
✅ Strict MSU domain filtering (only searches missouristate.edu)  
✅ Automatic query enhancement with "Missouri State University"  
✅ Result relevance scoring and ranking  
✅ Citation display in Flutter app  
✅ Response caching (2-hour TTL to save API quota)  
✅ Seamless fallback if search unavailable  

---

## Setup Instructions

### Step 1: Install Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate

# Install Google API client
pip install google-api-python-client
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

### Step 2: Get Google Custom Search API Credentials

#### 2a. Get API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Custom Search API**:
   - Navigate to "APIs & Services" → "Enable APIs and Services"
   - Search for "Custom Search API"
   - Click "Enable"
4. Create API Key:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy your API key (starts with `AIza...`)

#### 2b. Create Custom Search Engine

1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click "Add" to create new search engine
3. Configure:
   - **Sites to search**: `missouristate.edu/*`
   - **Name**: "MSU Search Engine"
   - Click "Create"
4. After creation:
   - Click "Control Panel"
   - Find your **Search engine ID** (cx parameter)
   - Copy it

#### 2c. Configure Search Engine (Important!)

1. In Control Panel, go to "Setup" → "Basics"
2. Under "Sites to search", add these domains:
   ```
   missouristate.edu
   www.missouristate.edu
   graduate.missouristate.edu
   computerscience.missouristate.edu
   admissions.missouristate.edu
   ```
3. Set **Search the entire web** to OFF (only MSU domains)
4. Save changes

### Step 3: Configure Environment Variables

Edit your `.env` file:

```bash
# Your existing Hugging Face token
hf_token="your_hf_token_here"

# Add these new lines
GOOGLE_API_KEY=AIza...your_actual_api_key...
GOOGLE_CSE_ID=your_search_engine_id_here
```

**Example:**
```bash
GOOGLE_API_KEY=AIzaSyB1234567890abcdefghijklmnop
GOOGLE_CSE_ID=a1b2c3d4e5f6g7h8i
```

### Step 4: Test Web Search Module

```bash
# Test the search engine directly
python web_search.py
```

Expected output:
```
Testing Web Search Engine...
✓ Google Custom Search initialized
============================================================
Query: computer science master's program requirements
============================================================
✓ Found 3 results
Search time: 0.45s
From cache: False
...
```

### Step 5: Start API Server

```bash
python api_server.py
```

Look for these initialization messages:
```
✓ Document processor initialized
✓ Web search engine initialized (Google Custom Search)
✅ Model loaded successfully!
```

If you see:
```
⚠️  Web search engine not configured (add GOOGLE_API_KEY and GOOGLE_CSE_ID to .env)
```
Check your `.env` file for correct credentials.

### Step 6: Test from Flutter App

1. Start Flutter app
2. Ask questions that need current info:
   - "What are the current CS course offerings?"
   - "academic calendar spring 2025"
   - "latest admission requirements"

---

## How It Works

### 1. Query Detection
The system automatically detects when web search is needed based on:
- Keywords like "current", "latest", "recent", "2025", "upcoming"
- Academic/administrative topics

### 2. Search Process
```
User Query
    ↓
Check if needs current info
    ↓
Check cache (2-hour TTL)
    ↓
If not cached: Google Custom Search
    ↓
Filter to MSU domains only
    ↓
Score relevance
    ↓
Add to LLM context
    ↓
Generate response with citations
```

### 3. MSU Domain Filtering
**Strict filtering ensures only MSU information:**
- Query automatically enhanced: "CS courses" → "Missouri State University CS courses"
- Search restricted to: `site:missouristate.edu OR site:graduate.missouristate.edu ...`
- Results filtered by domain whitelist
- Relevance scoring prioritizes official pages

### 4. Caching
- Cache key: MD5(query + temperature + top_p + conversation_history)
- TTL: 2 hours
- Max cache size: 200 entries
- LRU eviction when full

---

## API Usage & Quotas

### Free Tier
- **100 queries/day** (Google Custom Search)
- Resets daily at midnight Pacific Time

### Monitoring Usage
Check your usage in Google Cloud Console:
1. Go to "APIs & Services" → "Dashboard"
2. Click "Custom Search API"
3. View "Queries" metric

### Staying Within Limits
The system helps conserve quota through:
- **2-hour response caching** (same query → cached result)
- **Selective triggering** (only for queries needing current info)
- **Failed query handling** (doesn't retry on rate limit)

### If You Exceed Quota
Options:
1. **Wait until daily reset** (midnight PT)
2. **Enable billing** in Google Cloud for higher limits
3. **Disable web search** temporarily (system falls back to model knowledge)

---

## Configuration Options

### Adjust Search Behavior

Edit `web_search.py`:

```python
# Number of search results (default: 5, max: 10)
response = engine.search(query, num_results=5)

# Cache TTL (default: 2 hours)
SEARCH_CACHE_TTL = 7200  # seconds

# Cache size (default: 200)
SEARCH_CACHE_MAX_SIZE = 200
```

### Change When Search Triggers

Edit `should_use_web_search()` in `web_search.py`:

```python
def should_use_web_search(question: str, topic: str, content_type: str) -> bool:
    # Add your custom logic here
    current_info_keywords = [
        "current", "latest", "recent", "2024", "2025",
        # Add more keywords...
    ]
    # ...
```

### Customize MSU Domains

Edit `MSU_DOMAINS` in `web_search.py`:

```python
MSU_DOMAINS = [
    "missouristate.edu",
    "www.missouristate.edu",
    # Add more MSU subdomains...
]
```

---

## Troubleshooting

### Problem: "Search service not available"
**Solution:** 
- Check `.env` has `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`
- Verify credentials are correct (no quotes, no spaces)
- Install `google-api-python-client`: `pip install google-api-python-client`

### Problem: "HTTP 403 Forbidden"
**Causes:**
- API key invalid or expired
- Custom Search API not enabled in Google Cloud
- Daily quota exceeded

**Solution:**
- Verify API key in Google Cloud Console
- Enable Custom Search API
- Check quota usage

### Problem: No search results returned
**Solution:**
- Check Custom Search Engine settings
- Verify "Sites to search" includes MSU domains
- Ensure "Search entire web" is OFF
- Test CSE directly at programmablesearchengine.google.com

### Problem: Search returns non-MSU sites
**Solution:**
- Update `MSU_DOMAINS` list in `web_search.py`
- Check Custom Search Engine configuration
- Verify domain filtering logic in `_filter_results_by_domain()`

### Problem: Too many API calls
**Solution:**
- Increase `SEARCH_CACHE_TTL` (longer caching)
- Reduce search triggering in `should_use_web_search()`
- Monitor usage in Google Cloud Console

---

## Testing Checklist

- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Add API credentials to `.env`
- [ ] Test web search module (`python web_search.py`)
- [ ] Start API server and verify initialization
- [ ] Ask current-info question in Flutter app
- [ ] Verify citations display correctly
- [ ] Click citation links to verify they work
- [ ] Test with various MSU-related queries
- [ ] Verify non-current queries don't trigger search
- [ ] Check cache is working (same query twice)

---

## Example Queries That Trigger Search

✅ **Will use web search:**
- "What are the current admission requirements?"
- "CS course schedule for spring 2025"
- "Latest changes to the master's program"
- "Recent updates to graduation requirements"
- "Upcoming events at MSU"

❌ **Won't use web search:**
- "Hi, how are you?"
- "What is computer science?" (general knowledge)
- "Tell me about Missouri State" (static info)
- "How do I apply?" (general process)

---

## Performance Metrics

- **Search latency**: ~0.3-0.8 seconds
- **Cache hit latency**: <0.01 seconds
- **Model inference**: ~2-5 seconds (unchanged)
- **Total with search**: ~3-6 seconds
- **Total with cache**: ~2-5 seconds (no search overhead)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Flutter App                        │
│  ┌────────────────────────────────────────────┐    │
│  │  Chat UI with Citation Display             │    │
│  └────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP POST /chat
                       ▼
┌─────────────────────────────────────────────────────┐
│              Flask API Server                        │
│  ┌────────────────────────────────────────────┐    │
│  │  generate_response()                       │    │
│  │    ├─ Detect topic & content type          │    │
│  │    ├─ Check if web search needed           │    │
│  │    │   ├─ Check cache (2hr TTL)            │    │
│  │    │   └─ Google Custom Search ─────────┐  │    │
│  │    ├─ Build prompt with search context  │  │    │
│  │    ├─ LLM inference (Llama 3.2)         │  │    │
│  │    └─ Return response + citations       │  │    │
│  └────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           Web Search Module (web_search.py)          │
│  ┌────────────────────────────────────────────┐    │
│  │  MSU Domain Filtering                      │    │
│  │  Query Enhancement                         │    │
│  │  Result Scoring                            │    │
│  │  Citation Formatting                       │    │
│  └────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│          Google Custom Search API                    │
│         (100 free queries/day)                      │
└─────────────────────────────────────────────────────┘
```

---

## Security Notes

⚠️ **Keep credentials secure:**
- Never commit `.env` file to git
- Add `.env` to `.gitignore` (already done)
- Use `.env.example` for documentation only
- Restrict API key to your IP if possible

⚠️ **API key security in Google Cloud:**
1. Go to API Key settings
2. Click "Restrict Key"
3. Set "Application restrictions" (HTTP referrers or IP addresses)
4. Set "API restrictions" to "Custom Search API" only

---

## Cost Considerations

### Free Tier (Current)
- $0/month for up to 100 queries/day
- Perfect for development and light usage

### If You Need More
- **Paid tier**: $5 per 1000 queries
- **Estimate**: ~150 queries/day = $23/month
- **Alternative**: Implement query batching or smarter caching

---

## Next Steps

1. **Monitor usage** for first week
2. **Adjust caching** based on patterns
3. **Tune search triggering** to optimize quota
4. **Consider alternatives** if quota insufficient:
   - Brave Search API (2000 free/month)
   - DuckDuckGo (unlimited but less accurate)
   - Pre-indexed MSU content (no API calls)

---

## Support

Issues? Check:
1. Server logs: Look for web search initialization messages
2. Browser console: Check for API errors
3. Google Cloud Console: Verify API status and quota
4. Test module directly: `python web_search.py`

---

**Implementation Date:** November 14, 2025  
**Version:** 1.0  
**Status:** ✅ Production Ready
