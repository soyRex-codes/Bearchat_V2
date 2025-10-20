# MSU Cost of Attendance Chatbot

A fine-tuned Llama-3.2-3B-Instruct model designed to answer questions about Missouri State University's Cost of Attendance. This project uses Retrieval-Augmented Generation (RAG) techniques and provides multiple interfaces for interacting with the model.

## Features

- **Fine-tuned Llama-3.2-3B-Instruct**: Optimized for domain-specific responses about MSU's cost of attendance
- **Contextual Prompting**: Uses topic and content type metadata for accurate, context-aware answers
- **Multiple Interfaces**: API server, interactive chat, and batch testing
- **Smart Checkpoint Management**: Automatic backup and rollback capabilities
- **Data Scraping Tools**: Scripts to collect and process training data from web sources

## Project Structure

```
├── api_server.py                 # Flask API server for model serving
├── chat_contextual.py            # Interactive chat with topic detection
├── Superior_finetune.py          # Main fine-tuning script with LoRA
├── test_model.py                 # Batch testing script
├── rollback_checkpoint.py        # Checkpoint rollback utility
├── convert_csv_to_json.py        # Data conversion utility
├── Use_when_scarpping_multiple_web_pages_combine_training_data.py  # Web scraping script
├── smart_cost_of_attendance_for_missouri_state_university_training.json  # Training data
├── requirements.txt              # Python dependencies
├── docs/                         # Documentation
├── models/                       # Model checkpoints and adapters
│   ├── latest/                   # Current fine-tuned model
│   └── previous/                 # Backup of previous version
└── _origianl_model_backup_gemma-1b-it-contextual/  # Legacy backups
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

4. Set up Hugging Face token:
   - Get your token from [Hugging Face](https://huggingface.co/settings/tokens)
   - Create a `.env` file or set environment variable `HF_TOKEN`
   - Alternatively, update the token directly in the scripts (not recommended for public repos)

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
python chat_contextual.py
```

The chat includes topic detection to provide context-aware responses.

### API Server

Start the Flask API server:
```bash
python api_server.py
```

The server will be available at `http://localhost:5000` with CORS enabled for web/mobile apps.

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

## Acknowledgments

- Missouri State University for the cost of attendance information
- Meta for the Llama model series
- Hugging Face for the transformers library
- The PEFT and TRL libraries for efficient fine-tuning