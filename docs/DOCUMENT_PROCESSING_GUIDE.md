# Document Processing - Quick Start Guide

## What We Built

A complete pipeline for processing PDFs and images (transcripts, syllabi, course catalogs) and answering questions about them using your fine-tuned Llama model.

## Architecture

```
User uploads PDF/Image
        ↓
[Document Processor]
  ├─ Image? → Convert to PDF
  ├─ Extract text from PDF
  └─ OCR fallback (if needed)
        ↓
[Text Chunking]
  └─ Split for context window
        ↓
[Llama-3.2-3B Model]
  └─ Generate contextual answer
        ↓
Return response
```

## Installation

### 1. Install Python packages
```bash
pip install -r requirements.txt
```

### 2. Install Tesseract OCR

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 3. Verify setup
```bash
python setup_document_processing.py
```

## Usage

### Start the API Server
```bash
python api_server.py
```

Server runs on: `http://localhost:8080`

### Test Document Upload

**Option 1: Using the test script**
```bash
python test_document_upload.py
```

**Option 2: Using curl**
```bash
curl -X POST http://localhost:8080/upload \
  -F "file=@transcript.pdf" \
  -F "question=What is my GPA?"
```

**Option 3: Using Python**
```python
import requests

with open('transcript.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8080/upload',
        files={'file': f},
        data={'question': 'What courses did I complete?'}
    )

print(response.json()['answer'])
```

## Supported File Types

- **PDFs**: Native text PDFs or scanned PDFs (uses OCR)
- **Images**: PNG, JPG, JPEG, BMP, TIFF, GIF

## How It Works

### 1. Image Processing
Images are automatically converted to PDF before text extraction:
```python
Image (PNG/JPG) → PDF → Text Extraction
```

### 2. Text Extraction
- **Native PDFs**: Direct text extraction using PyPDF2
- **Scanned PDFs**: OCR using Tesseract
- **Fallback**: Automatically tries OCR if extraction yields minimal text

### 3. Smart Chunking
Long documents are split into chunks that fit Llama's 4096 token context window.

### 4. Contextual Responses
The model receives:
- Extracted document text
- User's question
- Topic/category metadata
- System instructions for document-specific answers

## API Endpoints

### `/upload` - Document Upload
```json
POST /upload

Form Data:
{
  "file": <PDF or image file>,
  "question": "What is my GPA?",
  "max_length": 1024,
  "temperature": 0.3,
  "top_p": 0.85
}

Response:
{
  "success": true,
  "question": "What is my GPA?",
  "answer": "Based on your transcript, your GPA is 3.85...",
  "document_info": {
    "file_name": "transcript.pdf",
    "file_type": "pdf",
    "processing_method": "pdf_extraction",
    "num_characters": 5234,
    "num_chunks": 1
  }
}
```

### `/chat` - Regular Chat (No Document)
```json
POST /chat

Body:
{
  "question": "What scholarships are available?",
  "max_length": 512,
  "temperature": 0.3
}
```

### `/health` - Health Check
```json
GET /health

Response:
{
  "status": "healthy",
  "model_loaded": true,
  "document_processor_ready": true
}
```

## Example Use Cases

### 1. Transcript Analysis
```bash
# Upload transcript and ask about GPA
curl -X POST http://localhost:8080/upload \
  -F "file=@transcript.pdf" \
  -F "question=What is my cumulative GPA?"
```

### 2. Course Catalog Queries
```bash
# Upload catalog and ask about prerequisites
curl -X POST http://localhost:8080/upload \
  -F "file=@cs_catalog.pdf" \
  -F "question=What are the prerequisites for CSC 325?"
```

### 3. Syllabus Information
```bash
# Upload syllabus and ask about grading
curl -X POST http://localhost:8080/upload \
  -F "file=@cs_232_syllabus.pdf" \
  -F "question=What is the grading breakdown?"
```

### 4. Degree Audit Screenshot
```bash
# Upload screenshot and ask about requirements
curl -X POST http://localhost:8080/upload \
  -F "file=@degree_audit.png" \
  -F "question=How many credit hours do I still need?"
```

## Troubleshooting

### Tesseract not found
```
Error: Tesseract OCR not found
```
**Solution:** Install Tesseract (see installation section above)

### File too large
```
Error: File too large: 55.2MB (max: 50MB)
```
**Solution:** Reduce file size or compress PDF

### No text extracted
```
Error: No text could be extracted from document
```
**Possible causes:**
- Empty document
- Corrupted file
- Poor image quality (for OCR)

**Solution:** Try with a different file or improve image quality

### Model not loaded
```
Error: Model not loaded
```
**Solution:** 
1. Ensure fine-tuned model exists in `models/latest/`
2. Check Hugging Face token in `.env` file
3. Restart the server

## Performance Notes

- **Small PDFs (< 5 pages)**: ~2-5 seconds processing
- **Large PDFs (10+ pages)**: ~10-20 seconds processing
- **Images with OCR**: +5-10 seconds for OCR
- **Response generation**: ~2-5 seconds

## Flutter Integration

To integrate with your Flutter app:

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<String> uploadDocument(File file, String question) async {
  var request = http.MultipartRequest(
    'POST',
    Uri.parse('http://YOUR_SERVER_IP:8080/upload'),
  );
  
  request.files.add(await http.MultipartFile.fromPath('file', file.path));
  request.fields['question'] = question;
  
  var response = await request.send();
  var responseData = await response.stream.bytesToString();
  var jsonData = json.decode(responseData);
  
  return jsonData['answer'];
}
```

## Next Steps

1. ✅ Install dependencies
2. ✅ Verify setup with `setup_document_processing.py`
3. ✅ Start API server with `python api_server.py`
4. ✅ Test with `test_document_upload.py`
5. 🔄 Integrate with Flutter app
6. 🔄 Deploy to production

## Security Notes

- Files are stored temporarily and deleted after processing
- Max file size: 50MB
- Uploads are not permanently stored
- For production: Add authentication, rate limiting, virus scanning
