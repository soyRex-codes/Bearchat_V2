# MSU Chatbot - trained on MSU knowledge

A fine-tuned Llama-3.2-3B-Instruct model designed to answer questions about Missouri State University's knwledgebase data. This project uses Retrieval-Augmented Generation (RAG) techniques and provides multiple interfaces for interacting with the model.

## Features

- **Fine-tuned Llama-3.2-3B-Instruct**: Optimized for domain-specific responses like MSU's cost of attendance, scholarship, degree, courses, and more.
- **Document Processing**: Upload PDFs and images (transcripts, syllabi, course catalogs) and ask questions about them
- **Contextual Prompting**: Uses topic and content type metadata for accurate, context-aware answers
- **Multiple Interfaces**: API server, interactive chat, and batch testing
- **Smart Checkpoint Management**: Automatic backup and rollback capabilities
- **Data Scraping Tools**: Scripts to collect and process training data from web sources

## Project Structure

```
├── api_server.py                 # Flask API server for model serving
├── chat_contextual.py            # Interactive chat with topic detection
├── document_processor.py         # PDF/image processing pipeline
├── test_document_upload.py       # Test document upload functionality
├── finetune.py                   # Main fine-tuning script with LoRA
├── test_model.py                 # Batch testing script
├── rollback_checkpoint.py        # Checkpoint rollback utility
├── superior_msu_collector.py     # Web scraping for training data
├── Use_when_scarpping_multiple_web_pages_combine_training_data.py  # Data combiner
├── requirements.txt              # Python dependencies
├── models/                       # Model checkpoints and adapters
│   ├── latest/                   # Current fine-tuned model
│   └── previous/                 # Backup of previous version
└── Json_data_storage/            # Training data files
```

## Setup

### Prerequisites

- Python 3.8+
- Hugging Face account with access to Llama models
- Sufficient RAM (16GB+ recommended for fine-tuning)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/soyRex-codes/Bearchat_V2.git
   cd Bearchat_V2
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Tesseract OCR (for scanned documents):
   ```bash
   # macOS
   brew install tesseract
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # Windows
   # Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

5. Set up Hugging Face token:
   - Get your token from [Hugging Face](https://huggingface.co/settings/tokens)
   - Create a `.env` file in the project root with: `hf_token=your_token_here`
   - The scripts will automatically load the token from the environment

## Usage

### Fine-tuning the Model

Run the fine-tuning script:
```bash
python Superior_finetune.py
```

This will:
- Load the Llama-3.2-3B-Instruct base model
- Apply LoRA adapters for efficient fine-tuning
- Train on the cost of attendance dataset
- Save checkpoints to `models/latest/`

### Testing the Model

Batch test the model:
```bash
python test_model.py
```

This runs predefined questions about MSU's cost of attendance and displays responses.

### Interactive Chat

Start an interactive chat session:
```bash
python chat_contextual.pyx
```

The chat includes topic detection to provide context-aware responses.

### API Server

Start the Flask API server:
```bash
python api_server.py
```

The server will be available at `http://localhost:8080` with CORS enabled for web/mobile apps.

#### API Endpoints

**1. Regular Chat**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What scholarships are available for CS students?",
    "max_length": 512,
    "temperature": 0.3
  }'
```

**2. Document Upload (NEW)**

Upload PDFs or images (transcripts, syllabi, degree audits) and ask questions:

```bash
curl -X POST http://localhost:8080/upload \
  -F "file=@transcript.pdf" \
  -F "question=What is my GPA?" \
  -F "max_length=1024"
```

Supported formats: PDF, PNG, JPG, JPEG, BMP, TIFF, GIF

**Python example:**
```python
import requests

# Upload transcript and ask question
with open('transcript.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8080/upload',
        files={'file': f},
        data={
            'question': 'What courses did I complete in Fall 2024?',
            'max_length': 1024
        }
    )
    
result = response.json()
print(result['answer'])
```

**3. Batch Processing**
```bash
curl -X POST http://localhost:8080/batch \
  -H "Content-Type: application/json" \
  -d '{
    "questions": [
      "What is the CS curriculum?",
      "What are the admission requirements?"
    ]
  }'
```

### Testing Document Upload

Test the document processing pipeline:
```bash
python test_document_upload.py
```

This will:
- Check if the API server is running
- Test regular chat functionality
- Test document upload with sample files
- Validate text extraction and response generation

### Data Collection

Scrape additional training data:
```bash
python Use_when_scarpping_multiple_web_pages_combine_training_data.py
```

Convert CSV data to JSON format:
```bash
python convert_csv_to_json.py
```

## Training Data

The model is trained on `smart_cost_of_attendance_for_missouri_state_university_training.json`, which contains:
- Questions and answers about MSU's cost of attendance
- Metadata including topics, source URLs, and content types
- Cleaned and validated data for optimal training

## Model Architecture

- **Base Model**: Meta-Llama/Llama-3.2-3B-Instruct
- **Fine-tuning**: LoRA (Low-Rank Adaptation) for parameter-efficient training
- **Training Framework**: TRL (Transformer Reinforcement Learning) with SFT
- **Context Window**: Supports up to 4096 tokens

## Checkpoint Management

The project includes smart checkpoint management:
- `models/latest/`: Current fine-tuned model
- `models/previous/`: Automatic backup before new training
- Use `rollback_checkpoint.py` to restore previous versions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Raj Kushwaha (soyRex-codes)
Bertrand Rusanganwa
Guillaume Girishya
Bekhrom Norkulov

## Acknowledgments

- Missouri State University for the cost of attendance information
- Meta for the Llama model series
- Hugging Face for the transformers library
- The PEFT and TRL libraries for efficient fine-tuning
