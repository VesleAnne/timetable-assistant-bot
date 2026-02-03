# LLM Integration Guide

## Overview

The bot now supports LLM-based parsing for improved time detection with typos and natural language.

## Benefits

- ✅ Handles typos: `10;30`, `1o:30`, `10.30` → `10:30`
- ✅ Natural language: "half past ten" → `10:30`
- ✅ City typos: "Berln" → "Berlin", "Amsterdm" → "Amsterdam"
- ✅ Russian support with typos

## Quick Start (Ollama - Free)
```bash
# 1. Install Ollama
brew install ollama  # Mac
# or download from https://ollama.ai

# 2. Pull model
ollama pull llama3.2 #or any other model of your choice

# 3. Start Ollama server (keep running)
ollama serve

# 4. Configure .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_TIMEOUT=60

# 5. Run bot
python -m src.main telegram
```

## Alternative Providers

### OpenAI 
```bash
# Install
pip install openai

# Configure
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

### Google Gemini 
```bash
# Install
pip install google-generativeai

# Configure
LLM_PROVIDER=google
LLM_API_KEY=AIza...
LLM_MODEL=gemini-2.0-flash
```

### Anthropic Claude
```bash
# Install
pip install anthropic

# Configure
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
```

### Ollama


```bash

# No pip install needed, just install Ollama app
# Download from: https://ollama.ai
#Then pull the model of your choice

# Configure
LLM_PROVIDER=ollama
LLM_MODEL='gemma3:1b'
OLLAMA_BASE_URL=http://localhost:11434
```

## How It Works
```
Message arrives
    ↓
Regex parser (fast, free)
    ↓
Found time? YES → Use it ✅
    ↓ NO
LLM enabled? NO → Empty result ❌
    ↓ YES
LLM parser (smart, handles typos)
    ↓
Found time? YES → Use it ✅
    ↓ NO
Empty result ❌
```

## Troubleshooting

### Timeout errors
```bash
# Increase timeout in .env
LLM_TIMEOUT=60
```


### LLM not being used
```bash
# Check environment
env | grep LLM

# Should show:
# LLM_PROVIDER=ollama (or openai, google, anthropic)
```

## Disable LLM

Remove LLM variables from `.env` or set:
```bash
LLM_PROVIDER=disabled
```

Bot will use only regex parser (still works perfectly for clean input).
