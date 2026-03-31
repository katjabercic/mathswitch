# Categorizer Module

The categorizer module provides LLM-powered categorization of mathematical concepts.

## Setup

### 1. Install Required Dependencies

**For FREE local models (recommended):**
```bash
make install
```

**For paid API models (optional):**

For OpenAI:
```bash
pip install openai
```

For Anthropic Claude:
```bash
pip install anthropic
```

**For Ollama (free local alternative):**
1. Install Ollama: https://ollama.com/download
2. Install langchain-community: `pip install langchain-community`
3. Pull the models you want to use:
```bash
ollama pull deepseek-r1:14b
ollama pull qwen2.5:14b
ollama pull gemma3:12b
```

### 2. Configure API Keys (only for paid models)

Set the appropriate environment variable for your chosen LLM provider:

**For OpenAI:**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

**For Anthropic Claude:**
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

**For Ollama (optional):**
```bash
export OLLAMA_MODEL="llama2"  # Default is llama2
```

You can also add these to a `.env` file or your shell configuration file (`.bashrc`, `.zshrc`, etc.).

## Usage

### Basic Usage

Categorize all items using the default FREE LLM (HuggingFace FLAN-T5):
```bash
python manage.py categorize
```

### With Options

Categorize a limited number of items:
```bash
python manage.py categorize --limit 10
make categorize
# OR
```

Use a specific LLM provider:

**FREE models (run locally):**
```bash
# Use HuggingFace FLAN-T5 (default, free, good for instruction following)
python manage.py categorize --llm huggingface_flan_t5

# Use HuggingFace GPT-2 (free, generative model)
python manage.py categorize --llm huggingface_gpt2

# Use HuggingFace DialoGPT (free, conversational model)
python manage.py categorize --llm huggingface_dialogpt

# Use Ollama (free, requires Ollama installed)
python manage.py categorize --llm ollama
```

**Free local models via Ollama (~12GB VRAM, Q4 quantization):**

First pull the models you want to use:
```bash
ollama pull deepseek-r1:14b
ollama pull qwen2.5:14b
ollama pull gemma3:12b
```

Then run the categorizer with each:
```bash
python manage.py categorize --llm ollama_deepseek_r1_14b --limit 10
python manage.py categorize --llm ollama_qwen25_14b --limit 10
python manage.py categorize --llm ollama_gemma3_12b --limit 10
```

**Paid API models:**
```bash
# Use OpenAI GPT-4 (requires API key)
python manage.py categorize --llm openai_gpt4

# Use OpenAI GPT-3.5 Turbo (requires API key)
python manage.py categorize --llm openai_gpt35

# Use Anthropic Claude (requires API key)
python manage.py categorize --llm anthropic_claude
```

Combine options:
```bash
python manage.py categorize --limit 5 --llm huggingface_flan_t5
```

## Architecture

- `categorizer_service.py` - Main service for categorizing items
- `llm_service.py` - Service for calling various LLM APIs
- `management/commands/categorize.py` - Django management command

## Supported LLMs

### Free Models (No API Key Required)
1. **HuggingFace FLAN-T5** - Google's instruction-following model (recommended for tasks)
2. **HuggingFace GPT-2** - OpenAI's classic generative model
3. **HuggingFace DialoGPT** - Microsoft's conversational model
4. **Ollama** - Run any Ollama model locally (default: llama2)

### Free Ollama Models (~12GB VRAM at Q4 quantization)
| Model | `--llm` value | ~VRAM | Notes |
|---|---|---|---|
| DeepSeek-R1 7B | `ollama_deepseek_r1_7b` | ~5 GB | Reasoning, lightweight |
| DeepSeek-R1 14B | `ollama_deepseek_r1_14b` | ~10-11 GB | Best DeepSeek for 12GB GPUs |
| Gemma 3 12B | `ollama_gemma3_12b` | ~9 GB | Multimodal, 128K context |
| Llama 3.1 8B | `ollama_llama31_8b` | ~5 GB | Solid all-rounder |
| Mistral 7B | `ollama_mistral_7b` | ~5 GB | Fast, good at classification |
| Qwen 2.5 7B | `ollama_qwen25_7b` | ~5 GB | Multilingual, structured output |
| Qwen 2.5 14B | `ollama_qwen25_14b` | ~10-11 GB | Best quality-per-VRAM |
| Phi-3.5 Mini | `ollama_phi35_mini` | ~4 GB | Tiny but capable |

### Paid API Models (Require API Key)
1. **OpenAI GPT-4** - Most capable, but expensive
2. **OpenAI GPT-3.5 Turbo** - Fast and cheaper than GPT-4
3. **Anthropic Claude** - High quality, good reasoning

## Performance Notes

- **Free models** run locally and don't require internet/API keys, but:
  - First run downloads the model (~1-3GB depending on model)
  - Requires sufficient RAM (4-8GB+ recommended)
  - Slower than API models (especially without GPU)

- **API models** are faster but cost money per request

- **Ollama** is a good middle ground - free, local, and supports many models

## Extending

To add support for additional LLM providers:

1. Add a new entry to the `LLMType` enum in `llm_service.py`
2. Implement a new private method (e.g., `_call_new_provider`) in the `LLMService` class
3. Add the new provider to the `call_llm` method's conditional logic
4. Update the command choices in `management/commands/categorize.py`
