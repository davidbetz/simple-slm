import json
from flask import Flask, request, jsonify
from slm.process_intents import (
    parse_command,
    validate_result,
    system_decision,
)

app = Flask(__name__)

# Model is already loaded when cpp.py is imported
print("Model loaded and ready!")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "model_loaded": True})


@app.route('/parse', methods=['POST'])
def parse():
    """Parse a command and return structured result"""
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400
    
    message = data['message']
    result = parse_command(message)
    validation_ok, validation_errors = validate_result(result)
    decision = system_decision(result, validation_ok)
    
    # Remove raw output for cleaner response (unless requested)
    include_raw = data.get('include_raw', False)
    response = {
        "intent": result.get("intent"),
        "process_id": result.get("process_id"),
        "ambiguities": result.get("ambiguities"),
        "missing_fields": result.get("missing_fields"),
        "model_confidence": result.get("model_confidence"),
        "validation": {
            "ok": validation_ok,
            "errors": validation_errors,
        },
        "decision": decision,
    }
    
    if include_raw:
        response["raw_model_output"] = result.get("_raw_model_output")
    
    # Add suggested response message
    if decision == "confirm":
        response["suggested_message"] = f'I understand that you want to {result["intent"].replace("_", " ")} {result["process_id"]}. Is this correct?'
    else:
        if result["missing_fields"]:
            response["suggested_message"] = f"Please clarify the missing fields: {', '.join(result['missing_fields'])}"
        elif result["ambiguities"]:
            response["suggested_message"] = f"Please clarify: {', '.join(result['ambiguities'])}"
        else:
            response["suggested_message"] = "I could not safely determine your intent. Please restate your request with a numeric process ID."
    
    return jsonify(response)


@app.route('/batch', methods=['POST'])
def batch():
    """Process multiple commands in one request"""
    data = request.get_json()
    
    if not data or 'messages' not in data:
        return jsonify({"error": "Missing 'messages' field (array)"}), 400
    
    messages = data['messages']
    if not isinstance(messages, list):
        return jsonify({"error": "'messages' must be an array"}), 400
    
    results = []
    for message in messages:
        result = parse_command(message)
        validation_ok, validation_errors = validate_result(result)
        decision = system_decision(result, validation_ok)
        
        results.append({
            "input": message,
            "intent": result.get("intent"),
            "process_id": result.get("process_id"),
            "ambiguities": result.get("ambiguities"),
            "missing_fields": result.get("missing_fields"),
            "model_confidence": result.get("model_confidence"),
            "decision": decision,
        })
    
    return jsonify({"results": results})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Process Command Parser API Server")
    print("="*60)
    print("\nEndpoints:")
    print("  GET  /health       - Health check")
    print("  POST /parse        - Parse single command")
    print("  POST /batch        - Parse multiple commands")
    print("\nExample usage:")
    print('  curl -X POST http://localhost:5000/parse \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": "turn off process 94"}\'')
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
