"""
Process management command parser.
Business logic for parsing operations commands like "disable process 94".
"""
import re
from typing import Any, Dict, List, Tuple

from .core import SLMParser
from .utils import ResultNormalizer


# -------------------------
# Domain Configuration
# -------------------------
SYSTEM_PROMPT = """Extract an operations command as JSON.

Allowed intents:
disable_process
enable_process
get_status
unknown

Return only JSON with exactly these keys:
intent
process_id
ambiguities
missing_fields
model_confidence

Rules:
- process_id must be null unless explicitly provided in the user examples below
- Do not invent values
- If the request is unclear, set intent to "unknown"
- If the request is negated, set intent to "unknown"
- ambiguities and missing_fields must always be arrays
- model_confidence must be a number from 0 to 1
- Do not output any keys other than the five required keys
"""

ALLOWED_INTENTS = {"disable_process", "enable_process", "get_status", "unknown"}

REQUIRED_KEYS = {
    "intent",
    "process_id",
    "ambiguities",
    "missing_fields",
    "model_confidence",
}


# -------------------------
# Process-Specific Helpers
# -------------------------
def extract_numeric_ids(text: str) -> List[int]:
    """Extract all numeric IDs from text."""
    return [int(x) for x in re.findall(r"\b\d+\b", text)]


def build_user_prompt(message: str) -> str:
    """Build few-shot prompt with process command examples."""
    return f"""Examples:

Input: turn off process 94
Output: {{"intent":"disable_process","process_id":94,"ambiguities":[],"missing_fields":[],"model_confidence":0.95}}

Input: enable process 12
Output: {{"intent":"enable_process","process_id":12,"ambiguities":[],"missing_fields":[],"model_confidence":0.95}}

Input: what is process 77 doing
Output: {{"intent":"get_status","process_id":77,"ambiguities":[],"missing_fields":[],"model_confidence":0.90}}

Input: disable process
Output: {{"intent":"unknown","process_id":null,"ambiguities":[],"missing_fields":["process_id"],"model_confidence":0.20}}

Input: don't disable process 94
Output: {{"intent":"unknown","process_id":94,"ambiguities":["negated request"],"missing_fields":[],"model_confidence":0.20}}

Now parse this.

Input: {message}
Output:"""


def normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize model output to expected schema."""
    ambiguities = ResultNormalizer.ensure_list(data.get("ambiguities", []))
    missing_fields = ResultNormalizer.ensure_list(data.get("missing_fields", []))
    conf = ResultNormalizer.ensure_float(data.get("model_confidence", 0.0))

    return {
        "intent": data.get("intent", "unknown"),
        "process_id": data.get("process_id", None),
        "ambiguities": ambiguities,
        "missing_fields": missing_fields,
        "model_confidence": float(conf),
    }


def patch_process_id_from_text(message: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract process ID from message text and update result."""
    ids = extract_numeric_ids(message)

    # Clear any model-provided process_id if it isn't an int
    if result["process_id"] is not None and not isinstance(result["process_id"], int):
        result["process_id"] = None

    if len(ids) == 1:
        result["process_id"] = ids[0]
        result["missing_fields"] = [x for x in result["missing_fields"] if x != "process_id"]
    elif len(ids) > 1:
        result["intent"] = "unknown"
        result["process_id"] = None
        if "multiple process ids" not in result["ambiguities"]:
            result["ambiguities"].append("multiple process ids")
        result["missing_fields"] = [x for x in result["missing_fields"] if x != "process_id"]
    else:
        result["process_id"] = None
        if result["intent"] in {"disable_process", "enable_process", "get_status"}:
            if "process_id" not in result["missing_fields"]:
                result["missing_fields"].append("process_id")

    return result


def apply_rule_overrides(message: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Apply deterministic rules to override model output when clear."""
    msg = message.lower().strip()

    # Simple negation handling
    if re.search(r"\b(don't|do not|dont|not)\b", msg):
        result["intent"] = "unknown"
        if "negated request" not in result["ambiguities"]:
            result["ambiguities"].append("negated request")

    # Deterministic status hints
    if re.search(r"\b(status|what is|what's|doing|running)\b", msg):
        if result["intent"] == "unknown":
            ids = extract_numeric_ids(message)
            if len(ids) == 1:
                result["intent"] = "get_status"

    # Deterministic disable hints
    if re.search(r"\b(turn off|disable|stop|kill|shut off)\b", msg):
        ids = extract_numeric_ids(message)
        if len(ids) == 1 and "negated request" not in result["ambiguities"]:
            result["intent"] = "disable_process"

    # Deterministic enable hints
    if re.search(r"\b(enable|turn on|start)\b", msg):
        if result["intent"] == "unknown" and "negated request" not in result["ambiguities"]:
            ids = extract_numeric_ids(message)
            if len(ids) == 1:
                result["intent"] = "enable_process"

    return result


def sanitize_result(message: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up result to remove impossible flags."""
    msg = message.lower()

    # Remove impossible negation flags if no negation words exist
    if "negated request" in result["ambiguities"]:
        if not re.search(r"\b(don't|do not|dont|not)\b", msg):
            result["ambiguities"] = [a for a in result["ambiguities"] if a != "negated request"]

    # If no process id exists, intent should usually be unknown
    if result["process_id"] is None and result["intent"] in {"disable_process", "enable_process", "get_status"}:
        result["intent"] = "unknown"

    return result


def validate_result(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate result against schema requirements."""
    errors: List[str] = []

    extra_keys = set(data.keys()) - REQUIRED_KEYS - {"_raw_model_output"}
    if extra_keys:
        errors.append(f"extra_keys:{sorted(extra_keys)}")

    if data.get("intent") not in ALLOWED_INTENTS:
        errors.append("invalid_intent")

    pid = data.get("process_id")
    if pid is not None and not isinstance(pid, int):
        errors.append("process_id_not_int_or_null")

    if not isinstance(data.get("ambiguities"), list):
        errors.append("ambiguities_not_list")

    if not isinstance(data.get("missing_fields"), list):
        errors.append("missing_fields_not_list")

    conf = data.get("model_confidence")
    if not isinstance(conf, (int, float)):
        errors.append("model_confidence_not_number")
    elif conf < 0 or conf > 1:
        errors.append("model_confidence_out_of_range")

    if data.get("intent") in {"disable_process", "enable_process", "get_status"} and pid is None:
        errors.append("recognized_intent_missing_process_id")

    return len(errors) == 0, errors


def system_decision(data: Dict[str, Any], validation_ok: bool) -> str:
    """Determine if system should confirm or clarify with user."""
    if not validation_ok:
        return "clarify"
    if data["intent"] == "unknown":
        return "clarify"
    if data["process_id"] is None:
        return "clarify"
    if data["ambiguities"]:
        return "clarify"
    if data["missing_fields"]:
        return "clarify"
    return "confirm"


# -------------------------
# Main Parser
# -------------------------
class ProcessCommandParser:
    """Parser for process management commands."""
    
    def __init__(self, model_name: str = "qwen2-0_5b-instruct-q4_k_m"):
        """Initialize parser with specified model."""
        self.slm = SLMParser(model_name, n_ctx=1024, verbose=False)
    
    def parse_command(self, message: str, max_tokens: int = 48, debug: bool = False) -> Dict[str, Any]:
        """Parse a process management command into structured JSON.
        
        Args:
            message: Natural language command (e.g., "disable process 94")
            max_tokens: Maximum tokens for model generation
            debug: Whether to print debug information
            
        Returns:
            Dictionary with intent, process_id, ambiguities, etc.
        """
        last_model_text = ""

        for _ in range(2):
            parsed, model_text = self.slm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(message),
                max_tokens=max_tokens,
                temperature=0,
            )
            
            last_model_text = model_text

            if parsed is not None:
                normalized = normalize_result(parsed)
                before_overrides = normalized.copy()
                normalized = patch_process_id_from_text(message, normalized)
                after_patch = normalized.copy()
                normalized = apply_rule_overrides(message, normalized)
                sanitize_result(message, normalized)

                if debug:
                    print("MESSAGE:", message)
                    print("BEFORE_OVERRIDES:", before_overrides)
                    print("AFTER_PATCH:", after_patch)
                    print("AFTER_OVERRIDES:", normalized)
                    
                normalized["_raw_model_output"] = model_text
                return normalized

        # Fallback if parsing failed
        fallback = {
            "intent": "unknown",
            "process_id": None,
            "ambiguities": ["parse_failure"],
            "missing_fields": ["intent"],
            "model_confidence": 0.0,
            "_raw_model_output": last_model_text,
        }
        fallback = patch_process_id_from_text(message, fallback)
        fallback = apply_rule_overrides(message, fallback)
        return fallback


# -------------------------
# Test Cases
# -------------------------
TEST_CASES = [
    {"input": "turn off process 94", "expected_intent": "disable_process", "expected_pid": 94, "expected_decision": "confirm"},
    {"input": "disable 94", "expected_intent": "disable_process", "expected_pid": 94, "expected_decision": "confirm"},
    {"input": "kill process 94", "expected_intent": "disable_process", "expected_pid": 94, "expected_decision": "confirm"},
    {"input": "enable process 12", "expected_intent": "enable_process", "expected_pid": 12, "expected_decision": "confirm"},
    {"input": "what is process 94 doing", "expected_intent": "get_status", "expected_pid": 94, "expected_decision": "confirm"},
    {"input": "disable process", "expected_intent": "unknown", "expected_pid": None, "expected_decision": "clarify"},
    {"input": "turn off that process", "expected_intent": "unknown", "expected_pid": None, "expected_decision": "clarify"},
    {"input": "don't disable process 94", "expected_intent": "unknown", "expected_pid": 94, "expected_decision": "clarify"},
    {"input": "disable process 94 and 95", "expected_intent": "unknown", "expected_pid": None, "expected_decision": "clarify"},
]


# -------------------------
# Convenience Functions (for backward compatibility)
# -------------------------
_default_parser = None

def get_default_parser() -> ProcessCommandParser:
    """Get or create the default parser instance."""
    global _default_parser
    if _default_parser is None:
        _default_parser = ProcessCommandParser()
    return _default_parser


def parse_command(message: str, max_tokens: int = 48, debug: bool = False) -> Dict[str, Any]:
    """Parse a command using the default parser (backward compatibility)."""
    return get_default_parser().parse_command(message, max_tokens, debug)


# -------------------------
# Main
# -------------------------
if __name__ == '__main__':
    import pandas as pd
    
    parser = ProcessCommandParser()
    rows = []

    for case in TEST_CASES:
        result = parser.parse_command(case["input"], debug=True)
        validation_ok, validation_errors = validate_result(result)
        decision = system_decision(result, validation_ok)

        rows.append({
            "input": case["input"],
            "expected_intent": case["expected_intent"],
            "actual_intent": result.get("intent"),
            "expected_pid": case["expected_pid"],
            "actual_pid": result.get("process_id"),
            "expected_decision": case["expected_decision"],
            "actual_decision": decision,
            "model_confidence": result.get("model_confidence"),
            "ambiguities": result.get("ambiguities"),
            "missing_fields": result.get("missing_fields"),
            "validation_errors": validation_errors,
            "raw_model_output": result.get("_raw_model_output"),
        })

    df = pd.DataFrame(rows)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 180)
    
    print("\n" + "="*80)
    print("PROCESS COMMAND PARSER TEST RESULTS")
    print("="*80)
    print(df)
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    intent_match = (df["expected_intent"] == df["actual_intent"]).sum()
    pid_match = (df["expected_pid"] == df["actual_pid"]).sum()
    decision_match = (df["expected_decision"] == df["actual_decision"]).sum()
    print(f"Intent matches: {intent_match}/{len(df)}")
    print(f"Process ID matches: {pid_match}/{len(df)}")
    print(f"Decision matches: {decision_match}/{len(df)}")
