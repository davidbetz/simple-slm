"""
SLM (Small Language Model) Intent Parser
A lightweight framework for building structured parsers with small language models.
"""

from slm.core import SLMParser
from slm.utils import ResultNormalizer, parse_json_safely, extract_first_json_object
from slm.process_intents import (
    ProcessCommandParser,
    parse_command,
    validate_result,
    system_decision,
    ALLOWED_INTENTS,
    REQUIRED_KEYS,
)

__version__ = "0.1.0"

__all__ = [
    # Core infrastructure
    "SLMParser",
    
    # Utilities
    "ResultNormalizer",
    "parse_json_safely",
    "extract_first_json_object",
    
    # Process parser (domain-specific)
    "ProcessCommandParser",
    "parse_command",
    "validate_result",
    "system_decision",
    "ALLOWED_INTENTS",
    "REQUIRED_KEYS",
]
