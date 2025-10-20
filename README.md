# Bearchat_V2
LLM - fine tunned speacifically to answer missouri state University questions.

# 🐻 BearChat - Missouri State University RAG Chatbot

A production-ready Retrieval-Augmented Generation (RAG) system powered by **Pinecone**, **Sentence-Transformers**, and **Google Gemma-2-2B** for answering questions about Missouri State University.

## Features

- ** Cloud Vector Database**: Uses Pinecone FREE tier (100K vectors, $0/month)
- ** Smart Incremental Updates**: Only re-processes new/changed data (5 seconds vs 20 minutes!)
- ** Fast Retrieval**: 20-40ms query speed from Pinecone
- ** AI-Powered**: LAMMA-3-3B-IT for natural language responses
- ** CPU Optimized**: Runs on Azure ML CPU environment

## Requirements

- Python 3.8+
- Pinecone account (FREE tier)
- Hugging Face account (free)
- Knowledge base JSON file

## Quick Start

### 1. Install Core Libraries (Cell 2)
```bash
pip install torch transformers accelerate sentence-transformers pinecone-client
```

### 2. Setup Pinecone
- Sign up at: https://www.pinecone.io/
- Get your API key
- Run Cell 1 to configure API key

### 3. Build Knowledge Base (Cell 5)
- Automatically creates embeddings
- Uploads to Pinecone cloud
- Smart caching for fast updates

### 4. Start Chatting! (Cell 6)
- Loads Gemma-2-2B model
- Ask questions about Missouri State University
- Get context-aware responses in 30-60 seconds

## System Architecture

```
User Question
    ↓
Sentence-Transformers (all-MiniLM-L6-v2)
    ↓
384-dimension vector
    ↓
Pinecone Cloud (retrieves top 3 matches)
    ↓
Context + Question → Gemma-2-2B
    ↓
Natural Language Answer
```

## Performance

- **First-time setup**: 10-15 minutes
- **Daily startup**: 5-7 minutes
- **Query speed**: 30-60 seconds per response (CPU)
- **Pinecone retrieval**: 20-40ms
- **Incremental updates**: 5 seconds for new data

## Technical Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Vector Database | Pinecone (FREE) | Cloud storage for embeddings |
| Embeddings | Sentence-Transformers | Convert text to 384D vectors |
| LLM | LAMMA LAMMA-3-3B-IT | Generate natural language responses |
| Framework | PyTorch 2.7.1 | Deep learning framework |
| Environment | Azure ML (Python 3.8) | Cloud compute |

## Project Structure

```
bearchat1/
├── README.md
├── .gitignore
├── myfinetune.ipynb              # Main notebook
├── missouri_state_university_data.json  # Knowledge base
└── .vscode/
    └── settings.json             # VS Code configuration
```

## Use Cases

- Student Q&A chatbot
- Campus information assistant
- Virtual tour guide
- Academic advisor helper
- Mobile app backend (production-ready!)

## Security Note

 **Never commit API keys to GitHub!**
- API keys are in `.gitignore`
- Store keys in environment variables
- Use separate keys for dev/prod

## License

MIT License - Feel free to use this for your own projects!

## Author

**rk33s (soyRex-codes)**
- GitHub: [@soyRex-codes](https://github.com/soyRex-codes)

## Acknowledgments

- Missouri State University for the knowledge base
- Pinecone for FREE vector database
- Google for LAMMA-3-3B-IT model
- HuggingFace for Sentence-Transformers

---

** Star this repo if it helped you!**

