"""
LLM-based message parser.

This parser uses Language Models to extract time mentions and locations,
with better handling of typos and natural language than regex.
"""

from __future__ import annotations

import logging
from datetime import time
from typing import Optional

from ..models import (
    ExplicitTimezoneMention,
    Language,
    ParseResult,
    TimeMention,
    TimeMentionKind,
    TimeStyle,
)

# Import from files we just created
from .providers import BaseLLMProvider, create_provider, load_config_from_env
from .prompts import TIME_EXTRACTION_SYSTEM_PROMPT, get_user_prompt

logger = logging.getLogger(__name__)


class LLMParser:
    """Parser using LLM for time extraction."""
    
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        """
        Initialize LLM parser.
        
        Args:
            provider: LLM provider instance. If None, loads from environment.
        """
        if provider is None:
            config = load_config_from_env()
            if config is None:
                raise ValueError(
                    "LLM provider not configured. Set LLM_PROVIDER environment variable."
                )
            provider = create_provider(config)
        
        self.provider = provider
    
    def parse(self, text: str) -> ParseResult:
        """
        Parse message using LLM.
        
        Args:
            text: Message text to parse
            
        Returns:
            ParseResult with extracted times, location, and language
        """
        try:
            # Get LLM response
            system_prompt = TIME_EXTRACTION_SYSTEM_PROMPT
            user_prompt = get_user_prompt(text)
            
            response_text = self.provider.complete(system_prompt, user_prompt)
            
            # Parse JSON response
            llm_output = self.provider.parse_json_response(response_text)
            
            # Convert to ParseResult
            return self._convert_to_parse_result(llm_output)
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}", exc_info=True)
            # Return empty result on error
            return ParseResult(
                language=Language.EN,
                times=[],
                explicit_timezone=None,
                date_anchor=None,
            )
    
    def _convert_to_parse_result(self, llm_output: dict) -> ParseResult:
        """Convert LLM JSON output to ParseResult."""
        # Extract language
        lang_str = llm_output.get("language", "en")
        language = Language.RU if lang_str == "ru" else Language.EN
        
        # Extract times
        times = []
        for time_data in llm_output.get("times", []):
            try:
                hour = time_data["hour"]
                minute = time_data.get("minute", 0)
                is_24h = time_data.get("is_24h", True)
                raw = time_data.get("raw", f"{hour}:{minute:02d}")
                
                # Determine style
                style = TimeStyle.H24 if is_24h else TimeStyle.H12
                
                # Create TimeMention
                times.append(TimeMention(
                    raw=raw,
                    style=style,
                    kind=TimeMentionKind.TIME,
                    start=time(hour=hour, minute=minute)
                ))
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid time data: {time_data}, error: {e}")
                continue
        
        # Extract location/timezone
        location_str = llm_output.get("location")
        explicit_tz = None
        if location_str:
            explicit_tz = ExplicitTimezoneMention(raw=location_str)
        
        return ParseResult(
            language=language,
            times=times,
            explicit_timezone=explicit_tz,
            date_anchor=None,  # Date anchors handled separately or by regex
        )


# Global singleton instance (lazy-initialized)
_llm_parser_instance: Optional[LLMParser] = None


def get_llm_parser() -> Optional[LLMParser]:
    """
    Get or create global LLM parser instance.
    
    Returns:
        LLMParser if configured, None if LLM is disabled
    """
    global _llm_parser_instance
    
    if _llm_parser_instance is None:
        config = load_config_from_env()
        if config is None:
            return None  # LLM disabled
        
        try:
            provider = create_provider(config)
            _llm_parser_instance = LLMParser(provider)
        except Exception as e:
            logger.error(f"Failed to initialize LLM parser: {e}")
            return None
    
    return _llm_parser_instance


def parse_with_llm(text: str) -> Optional[ParseResult]:
    """
    Convenience function to parse with LLM.
    
    Args:
        text: Message to parse
        
    Returns:
        ParseResult if LLM is enabled and successful, None otherwise
    """
    parser = get_llm_parser()
    if parser is None:
        return None
    
    return parser.parse(text)