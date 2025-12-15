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
1. Install Ollama from https://ollama.ai
2. Install langchain-community: `pip install langchain-community`
3. Pull a model: `ollama pull llama2`

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
4. **Ollama** - Run any Ollama model locally (llama2, mistral, etc.)

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
