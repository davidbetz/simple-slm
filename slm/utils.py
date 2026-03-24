"""
Generic utility functions for data processing and normalization.
These are domain-agnostic helpers that can be used in any project.
"""
import json
from typing import Any, Dict, Optional, Tuple


def extract_first_json_object(text: str) -> Optional[str]:
    """Extract the first complete JSON object from text.
    
    Handles cases where JSON is embedded in other text by finding
    the first '{' and tracking bracket depth to find the matching '}'.
    
    Args:
        text: String that may contain JSON
        
    Returns:
        The first complete JSON object as a string, or None if not found
        
    Example:
        >>> extract_first_json_object('Sure! {"key": "value"} Done.')
        '{"key": "value"}'
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def parse_json_safely(text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Safely parse JSON from text, handling malformed content.
    
    First extracts JSON using extract_first_json_object, then attempts to parse.
    Returns both the result and any error that occurred.
    
    Args:
        text: Text containing JSON
        
    Returns:
        Tuple of (parsed_dict, error_message)
        - If successful: (dict, None)
        - If failed: (None, error_description)
        
    Example:
        >>> parse_json_safely('{"valid": true}')
        ({"valid": true}, None)
        >>> parse_json_safely('invalid')
        (None, "no_json_found")
    """
    raw_json = extract_first_json_object(text)
    if raw_json is None:
        return None, "no_json_found"
    try:
        return json.loads(raw_json), None
    except Exception as e:
        return None, f"json_decode_error: {e}"


class ResultNormalizer:
    """Utilities for normalizing and validating parsed results.
    
    Provides static methods to coerce values into expected types,
    useful for handling inconsistent model outputs or API responses.
    """
    
    @staticmethod
    def ensure_list(value: Any) -> list:
        """Convert a value to a list if it isn't already.
        
        Args:
            value: Any value to normalize to a list
            
        Returns:
            - If value is already a list: returns as-is
            - If value is None or empty: returns []
            - Otherwise: returns [str(value)]
            
        Example:
            >>> ResultNormalizer.ensure_list([1, 2, 3])
            [1, 2, 3]
            >>> ResultNormalizer.ensure_list("single")
            ["single"]
            >>> ResultNormalizer.ensure_list(None)
            []
        """
        if not isinstance(value, list):
            return [str(value)] if value else []
        return value
    
    @staticmethod
    def ensure_float(value: Any, default: float = 0.0) -> float:
        """Convert a value to float, with fallback.
        
        Args:
            value: Value to convert to float
            default: Default value if conversion fails
            
        Returns:
            Float representation of value, or default if not convertible
            
        Example:
            >>> ResultNormalizer.ensure_float(3.14)
            3.14
            >>> ResultNormalizer.ensure_float(5)
            5.0
            >>> ResultNormalizer.ensure_float("invalid", default=0.0)
            0.0
        """
        if isinstance(value, (int, float)):
            return float(value)
        return default
    
    @staticmethod
    def ensure_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """Convert a value to int, with optional fallback.
        
        Args:
            value: Value to convert to int
            default: Default value if conversion fails (can be None)
            
        Returns:
            Int representation of value, or default if not convertible
            
        Example:
            >>> ResultNormalizer.ensure_int(42)
            42
            >>> ResultNormalizer.ensure_int("100")
            100
            >>> ResultNormalizer.ensure_int("invalid", default=None)
            None
        """
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return default
    
    @staticmethod
    def ensure_string(value: Any, default: str = "") -> str:
        """Convert a value to string, with fallback.
        
        Args:
            value: Value to convert to string
            default: Default value if value is None
            
        Returns:
            String representation of value, or default if None
            
        Example:
            >>> ResultNormalizer.ensure_string(123)
            "123"
            >>> ResultNormalizer.ensure_string(None, default="N/A")
            "N/A"
        """
        if value is None:
            return default
        return str(value)
