"""
LLM provider abstraction supporting multiple APIs.

Supported providers:
- OpenAI (GPT-4, GPT-5)
- Anthropic (Claude)
- Google (Gemini)
- Ollama (local models)
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LLMProvider(str, Enum):
    """Available LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    """LLM configuration."""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For Ollama
    temperature: float = 0.0  # Deterministic parsing
    max_tokens: int = 300
    timeout: int = 10  # seconds


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str:
        """Send completion request and return response text."""
        raise NotImplementedError
    
    def parse_json_response(self, text: str) -> dict:
        """Extract and parse JSON from LLM response."""
        # Many LLMs wrap JSON in markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        return json.loads(text)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import openai
            self.client = openai.OpenAI(api_key=config.api_key)
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Install with: pip install openai>=1.0.0"
            )
    
    def complete(self, system_prompt: str, user_message: str) -> str:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout,
        )
        return response.choices[0].message.content


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=config.api_key)
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. Install with: pip install anthropic>=0.18.0"
            )
    
    def complete(self, system_prompt: str, user_message: str) -> str:
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=self.config.timeout,
        )
        return response.content[0].text


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.api_key)
            self.model = genai.GenerativeModel(
                model_name=config.model,
                generation_config={
                    "temperature": config.temperature,
                    "max_output_tokens": config.max_tokens,
                }
            )
        except ImportError:
            raise RuntimeError(
                "google-generativeai package not installed. Install with: pip install google-generativeai>=0.3.0"
            )
    
    def complete(self, system_prompt: str, user_message: str) -> str:
        # Gemini doesn't have separate system prompt, combine them
        full_prompt = f"{system_prompt}\n\nUser message: {user_message}\n\nJSON response:"
        response = self.model.generate_content(full_prompt)
        return response.text


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise RuntimeError(
                "requests package not installed. Install with: pip install requests>=2.31.0"
            )
    
    def complete(self, system_prompt: str, user_message: str) -> str:
        url = f"{self.config.base_url}/api/generate"
        
        full_prompt = f"{system_prompt}\n\nUser message: {user_message}\n\nJSON response:"
        
        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
            }
        }
        
        response = self.requests.post(url, json=payload, timeout=self.config.timeout)
        response.raise_for_status()
        
        return response.json()["response"]


def create_provider(config: LLMConfig) -> BaseLLMProvider:
    """Factory function to create LLM provider."""
    providers = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.ANTHROPIC: AnthropicProvider,
        LLMProvider.GOOGLE: GoogleProvider,
        LLMProvider.OLLAMA: OllamaProvider,
    }
    
    provider_class = providers.get(config.provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {config.provider}")
    
    return provider_class(config)


def load_config_from_env() -> Optional[LLMConfig]:
    """Load LLM configuration from environment variables."""
    provider_str = os.getenv("LLM_PROVIDER", "").lower()
    
    if not provider_str or provider_str == "disabled":
        return None
    
    try:
        provider = LLMProvider(provider_str)
    except ValueError:
        raise ValueError(
            f"Invalid LLM_PROVIDER: {provider_str}. "
            f"Must be one of: {', '.join(p.value for p in LLMProvider)}"
        )
    
    # Default models for each provider
    default_models = {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.ANTHROPIC: "claude-3-5-haiku-20241022",
        LLMProvider.GOOGLE: "gemini-2.0-flash",
        LLMProvider.OLLAMA: "llama3.2",
    }
    
    return LLMConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL", default_models[provider]),
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "300")),
        timeout=int(os.getenv("LLM_TIMEOUT", "10")),
    )