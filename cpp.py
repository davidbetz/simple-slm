import os
import re
import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from llama_cpp import Llama

# -------------------------
# 1) Configure model path
# -------------------------
MODEL_NAME = "qwen2-0_5b-instruct-q4_k_m"
MODEL_PATH = os.path.join(os.getcwd(), "models", f"{MODEL_NAME}.gguf")

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=1024,
    verbose=False,
)

# -------------------------
# 2) Prompt
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
# 3) Helpers
# -------------------------
def extract_first_json_object(text: str) -> Optional[str]:
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
    raw_json = extract_first_json_object(text)
    if raw_json is None:
        return None, "no_json_found"
    try:
        return json.loads(raw_json), None
    except Exception as e:
        return None, f"json_decode_error: {e}"


def normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    ambiguities = data.get("ambiguities", [])
    missing_fields = data.get("missing_fields", [])

    if not isinstance(ambiguities, list):
        ambiguities = [str(ambiguities)]

    if not isinstance(missing_fields, list):
        missing_fields = [str(missing_fields)]

    conf = data.get("model_confidence", 0.0)
    if not isinstance(conf, (int, float)):
        conf = 0.0

    return {
        "intent": data.get("intent", "unknown"),
        "process_id": data.get("process_id", None),
        "ambiguities": ambiguities,
        "missing_fields": missing_fields,
        "model_confidence": float(conf),
    }


def extract_numeric_ids(text: str) -> List[int]:
    return [int(x) for x in re.findall(r"\b\d+\b", text)]


def patch_process_id_from_text(message: str, result: Dict[str, Any]) -> Dict[str, Any]:
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


def validate_result(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
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
# 4) Model call
# -------------------------
def build_user_prompt(message: str) -> str:
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

def sanitize_result(message: str, result: Dict[str, Any]) -> Dict[str, Any]:
    msg = message.lower()

    # Remove impossible negation flags if no negation words exist
    if "negated request" in result["ambiguities"]:
        if not re.search(r"\b(don't|do not|dont|not)\b", msg):
            result["ambiguities"] = [a for a in result["ambiguities"] if a != "negated request"]

    # If no process id exists, intent should usually be unknown
    if result["process_id"] is None and result["intent"] in {"disable_process", "enable_process", "get_status"}:
        result["intent"] = "unknown"

    return result

def parse_command(message: str, max_tokens: int = 48, debug: bool = False) -> Dict[str, Any]:
    last_model_text = ""

    for _ in range(2):
        response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(message)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=max_tokens,
        )

        model_text = response["choices"][0]["message"]["content"]
        last_model_text = model_text
        parsed, _parse_error = parse_json_safely(model_text)

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
# 5) Test set
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
# 6) Run evaluation
# -------------------------
if __name__ == '__main__':
    rows = []

    for case in TEST_CASES:
        result = parse_command(case["input"], debug=True)
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

    print(df.to_string(index=False))

    # -------------------------
    # 7) One-message demo
    # -------------------------
    message = "turn off process 94 plz"
    result = parse_command(message, debug=True)
    validation_ok, validation_errors = validate_result(result)
    decision = system_decision(result, validation_ok)

    print("\nINPUT:")
    print(message)

    print("\nPARSED RESULT:")
    print(json.dumps({k: v for k, v in result.items() if k != "_raw_model_output"}, indent=2))

    print("\nVALIDATION:")
    print(json.dumps({
        "validation_ok": validation_ok,
        "validation_errors": validation_errors,
        "decision": decision,
    }, indent=2))

    if decision == "confirm":
        print(f'\nCONFIRMATION MESSAGE:\nI understand that you want to disable process {result["process_id"]}. Is this correct?')
    else:
        print("\nCLARIFICATION MESSAGE:")
        if result["missing_fields"]:
            print(f"Please clarify the missing fields: {', '.join(result['missing_fields'])}")
        elif result["ambiguities"]:
            print(f"Please clarify: {', '.join(result['ambiguities'])}")
        else:
            print("I could not safely determine your intent. Please restate your request with a numeric process ID.")