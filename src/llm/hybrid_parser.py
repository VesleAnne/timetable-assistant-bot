"""
Hybrid parser: Combines regex parser with LLM fallback.

Strategy:
1. Try regex first (fast, free, reliable for well-formatted times)
2. If regex finds nothing and LLM is enabled, try LLM
3. Merge date anchors from regex with times/location from LLM

This gives best of both worlds:
- Fast path for clean messages
- Smart fallback for typos and natural language
"""

import logging
from typing import Optional

from ..models import ParseResult
from ..parser import parse_message as regex_parse  # Existing regex parser
from .llm_parser import parse_with_llm

logger = logging.getLogger(__name__)


def parse_message_hybrid(
    text: str,
    use_llm: bool = True,
    llm_only: bool = False
) -> ParseResult:
    """
    Parse message with hybrid regex + LLM approach.
    
    Args:
        text: Message text to parse
        use_llm: Whether to use LLM as fallback (default: True)
        llm_only: Skip regex, use only LLM (default: False)
        
    Returns:
        ParseResult with extracted information
    """
    # LLM-only mode (if client wants to force LLM)
    if llm_only:
        llm_result = parse_with_llm(text)
        if llm_result and llm_result.times:
            return llm_result
        # Fall back to regex if LLM fails
        logger.warning("LLM-only mode failed, falling back to regex")
    
    # Try regex first (fast path)
    regex_result = regex_parse(text)
    
    # If regex found times, use that (no need for LLM)
    if regex_result.times:
        logger.debug("Regex parser found times, using regex result")
        return regex_result
    
    # Regex found nothing, try LLM if enabled
    if not use_llm:
        logger.debug("LLM disabled, returning empty regex result")
        return regex_result
    
    llm_result = parse_with_llm(text)
    
    if llm_result is None:
        # LLM not configured or failed
        logger.debug("LLM not available, returning regex result")
        return regex_result
    
    if not llm_result.times:
        # LLM also found nothing
        logger.debug("LLM found no times, returning regex result")
        return regex_result
    
    # LLM found times! Merge with regex date anchors
    logger.info(f"LLM found {len(llm_result.times)} time(s) that regex missed")
    
    # Use LLM's times and location, but keep regex's date anchor if any
    return ParseResult(
        language=llm_result.language,
        times=llm_result.times,
        explicit_timezone=llm_result.explicit_timezone,
        date_anchor=regex_result.date_anchor or llm_result.date_anchor,
    )


# Convenience alias
parse_message = parse_message_hybrid