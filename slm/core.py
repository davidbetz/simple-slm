"""
SLM (Small Language Model) infrastructure for structured intent parsing.
Provides the core model loading and JSON generation capabilities.
"""
import os
from typing import Any, Dict, Optional, Tuple
from llama_cpp import Llama

from .utils import parse_json_safely


class SLMParser:
    """Base class for SLM-based structured parsing tasks.
    
    Handles model loading (via llama.cpp) and JSON-formatted generation.
    Use this as a base for building domain-specific parsers.
    
    Example:
        >>> parser = SLMParser("qwen2-0_5b-instruct-q4_k_m")
        >>> result, raw = parser.generate_json(
        ...     system_prompt="Extract intent as JSON",
        ...     user_prompt="User said: turn off process 94"
        ... )
    """
    
    def __init__(self, model_name: str, n_ctx: int = 1024, verbose: bool = False):
        """Initialize the SLM with a GGUF model.
        
        Args:
            model_name: Name of the GGUF model file (without .gguf extension)
            n_ctx: Context window size
            verbose: Whether to print llama.cpp debug output
        """
        model_path = os.path.join(os.getcwd(), "models", f"{model_name}.gguf")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            verbose=verbose,
        )
    
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 48,
        temperature: float = 0.0,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Generate structured JSON using the model.
        
        Uses llama.cpp's constrained generation to force valid JSON output,
        then parses it safely using utility functions.
        
        Args:
            system_prompt: System instructions for the model
            user_prompt: User query/input
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0 = deterministic)
            
        Returns:
            Tuple of (parsed_json, raw_model_text)
            - parsed_json may be None if parsing failed
            - raw_model_text always contains the model's output
            
        Example:
            >>> parsed, raw = parser.generate_json(
            ...     system_prompt="Return JSON with 'intent' field",
            ...     user_prompt="Input: disable process"
            ... )
        """
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )

        model_text = response["choices"][0]["message"]["content"]
        parsed, _error = parse_json_safely(model_text)
        return parsed, model_text
