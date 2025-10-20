# 🎓 MSU Scholarship Fine-Tuned Gemma Model

## 🎉 Training Complete!

Your Gemma 3-1B model has been successfully fine-tuned on Missouri State University scholarship information!

### 📊 Training Results
- **Training Time:** ~14 seconds (2 epochs)
- **Initial Loss:** 2.8106 → **Final Loss:** 2.7047 ✅
- **Token Accuracy:** 48.4% → 50.5% ✅
- **Trainable Parameters:** 1,490,944 / 1,001,376,896 (0.15% with LoRA)
- **Hardware:** M4 MacBook Pro (16GB RAM)

---

## 📁 Files Created

- **`finetune.py`** - Training script
- **`test_model.py`** - Batch testing script
- **`chat.py`** - Interactive chat interface
- **`models/latest/`** - Current model checkpoints
- **`models/previous/`** - Previous model backup (for rollback)

---

## 🚀 How to Use Your Model

### Option 1: Interactive Chat (Recommended)

```bash
python chat.py
```

This will start an interactive chat session where you can ask questions about MSU scholarships:

```
MSU SCHOLARSHIP ASSISTANT (Fine-tuned)
================================================================================

Ask me anything about Missouri State University scholarships!
Type 'quit' or 'exit' to end the conversation.

You: What scholarships are available for freshmen?
Assistant: [Model's response]
```

### Option 2: Batch Testing

```bash
python test_model.py
```

This will test your model on 6 pre-defined questions and show all responses.

### Option 3: Use in Your Own Code

```python
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Load model
model_id = "meta-llama/Llama-3.2-3B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id, token="YOUR_TOKEN")
base_model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    dtype=torch.bfloat16, 
    device_map="auto",
    token="YOUR_TOKEN"
)
model = PeftModel.from_pretrained(base_model, "./models/latest")
model.eval()

# Ask a question
question = "What scholarships are available for transfer students?"
prompt = f"### Instruction:\n{question}\n\n### Response:\n"
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.7)

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(response.split("### Response:\n")[-1])
```

---

## 📚 Training Data

The model was trained on 5 instruction-response pairs covering:
- Freshmen Scholarships
- Transfer Student Scholarships
- Current Student Scholarships
- Graduate Student Scholarships
- MSU Foundation Scholarships

**Data Format:**
```json
{
  "instruction": "Question about MSU scholarships",
  "response": "Detailed answer with specific information"
}
```

---

## ⚙️ Technical Details

### Model Configuration
- **Base Model:** meta-llama/Llama-3.2-3B-Instruct (3B parameters)
- **Fine-tuning Method:** LoRA (Low-Rank Adaptation)
- **Precision:** bfloat16
- **LoRA Rank (r):** 8
- **LoRA Alpha:** 16
- **Target Modules:** q_proj, k_proj, v_proj, o_proj
- **LoRA Dropout:** 0.05

### Training Configuration
- **Batch Size:** 2 per device
- **Gradient Accumulation:** 4 steps (effective batch size: 8)
- **Learning Rate:** 2e-4
- **Epochs:** 2
- **Optimizer:** AdamW (PyTorch)
- **Max Sequence Length:** 1024 tokens
- **Packing:** Disabled

### Hardware Requirements
- **Minimum:** 16GB RAM (tested on M4 MacBook Pro)
- **Recommended:** Apple Silicon Mac (M1/M2/M3/M4) for optimal performance
- **Training Time:** ~10-15 seconds for 2 epochs on M4

---

## 🔄 Retraining or Expanding

To add more data or retrain:

1. **Edit `msu_scholarship.json`** - Add more instruction-response pairs
2. **Run:** `python finetune.py`
3. **New model saved to:** `./models/latest/`

Tips for better results:
- Add at least 10-50 examples per topic
- Keep responses consistent in format
- Include edge cases and variations
- Balance the dataset across different scholarship types

---

## 📤 Sharing Your Model

### Option 1: Share LoRA Adapters Only (Recommended)
The adapters are much smaller (~3-6MB) than the full model:

```bash
# Zip the adapters
zip -r msu-scholarship-lora.zip models/latest/
```

Others can use them by:
```python
from peft import PeftModel
model = PeftModel.from_pretrained(base_model, "path/to/adapters")
```

### Option 2: Push to Hugging Face Hub

```python
trainer.push_to_hub("your-username/gemma-msu-scholarship")
```

### Option 3: Merge and Save Full Model

```python
model = model.merge_and_unload()
model.save_pretrained("./merged-model")
tokenizer.save_pretrained("./merged-model")
```

---

## 🐛 Troubleshooting

### "Out of memory" error
- Reduce `per_device_train_batch_size` to 1
- Reduce `max_length` to 512

### Model generates repetitive text
- Increase `temperature` (0.8-1.0)
- Add `repetition_penalty=1.2` to generate()

### Poor quality responses
- Add more training examples (aim for 50+)
- Train for more epochs (3-5)
- Increase LoRA rank to 16 or 32

---

## 📝 Next Steps

1. **Test thoroughly** with various questions
2. **Add more training data** to improve coverage
3. **Fine-tune parameters** for better responses
4. **Deploy** as a web API or chatbot
5. **Share** with the MSU community!

---

## 🙏 Credits

- **Base Model:** Google Gemma 3-1B-IT
- **Framework:** Hugging Face Transformers + TRL
- **Method:** PEFT (Parameter-Efficient Fine-Tuning) with LoRA

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the code comments in `finetune.py`
3. Consult Hugging Face documentation

**Happy chatting with your MSU Scholarship Assistant! 🎓**
