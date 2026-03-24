#!/usr/bin/env python3
"""
Fast test recorder - uses the running API server to record results.
Much faster than record_tests.py since model is already loaded.
"""

import csv
import json
import sys
import requests
from datetime import datetime
from typing import List, Dict, Any

API_URL = "http://localhost:5000"

# Comprehensive test cases
TEST_CASES = [
    # Clear disable commands
    "turn off process 94",
    "disable process 94",
    "disable 94",
    "kill process 94",
    "stop process 94",
    "shut off process 94",
    "shut down process 94",
    "turn off 94",
    
    # Clear enable commands
    "enable process 12",
    "turn on process 12",
    "start process 12",
    "resume process 12",
    "enable 12",
    "start 12",
    
    # Clear status queries
    "what is process 94 doing",
    "status of process 77",
    "check process 94",
    "is process 94 running",
    "process 94 status",
    "what's process 94 doing",
    
    # Polite variations
    "turn off process 94 please",
    "can you disable process 94",
    "please enable process 12",
    "turn off process 94 plz",
    "could you stop process 94",
    
    # Missing process ID
    "disable process",
    "turn off that process",
    "enable the process",
    "stop it",
    "kill that",
    "start the process",
    "what is the process doing",
    
    # Ambiguous - negated
    "don't disable process 94",
    "do not turn off process 94",
    "don't stop process 94",
    "not disable 94",
    
    # Ambiguous - multiple IDs
    "disable process 94 and 95",
    "stop processes 94 and 95",
    "turn off 94 and 77",
    "kill 12, 13, and 14",
    "disable 94 95 96",
    
    # Ambiguous - unclear
    "maybe disable process 94",
    "disable process ninety four",
    "turn off the first process",
    "stop all processes",
    
    # Edge cases
    "process 94",
    "94",
    "disable",
    "enable",
    "status",
    "",
    "hello",
    "what processes are running",
    "list all processes",
    
    # Numbers in different positions
    "process 94 disable",
    "94 needs to be stopped",
    "let's kill 94",
    "shut 94 off",
    
    # Complex phrasing
    "I need to turn off process 94",
    "could you please disable process 94 for me",
    "process 94 should be stopped",
    "we should enable process 12",
    "make sure process 94 is off",
    "check if process 94 is running",
]


def check_server():
    """Check if API server is running."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def run_test_via_api(input_text: str) -> Dict[str, Any]:
    """Run a single test via API and return results."""
    try:
        response = requests.post(
            f"{API_URL}/parse",
            json={"message": input_text, "include_raw": True},
            timeout=10
        )
        
        if response.status_code != 200:
            return {
                "input": input_text,
                "intent": "error",
                "process_id": None,
                "ambiguities": json.dumps([f"API error: {response.status_code}"]),
                "missing_fields": "[]",
                "model_confidence": 0,
                "decision": "error",
                "validation_ok": False,
                "validation_errors": json.dumps([f"HTTP {response.status_code}"]),
                "raw_output": response.text,
            }
        
        data = response.json()
        
        return {
            "input": input_text,
            "intent": data.get("intent"),
            "process_id": data.get("process_id"),
            "ambiguities": json.dumps(data.get("ambiguities", [])),
            "missing_fields": json.dumps(data.get("missing_fields", [])),
            "model_confidence": data.get("model_confidence"),
            "decision": data.get("decision"),
            "validation_ok": data.get("validation", {}).get("ok", False),
            "validation_errors": json.dumps(data.get("validation", {}).get("errors", [])),
            "raw_output": data.get("raw_model_output", ""),
        }
    
    except Exception as e:
        return {
            "input": input_text,
            "intent": "error",
            "process_id": None,
            "ambiguities": json.dumps([str(e)]),
            "missing_fields": "[]",
            "model_confidence": 0,
            "decision": "error",
            "validation_ok": False,
            "validation_errors": json.dumps([str(e)]),
            "raw_output": "",
        }


def save_to_csv(results: List[Dict[str, Any]], filename: str):
    """Save results to CSV file."""
    if not results:
        print("No results to save")
        return
    
    fieldnames = [
        "input",
        "intent",
        "process_id",
        "decision",
        "model_confidence",
        "ambiguities",
        "missing_fields",
        "validation_ok",
        "validation_errors",
        "raw_output",
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✓ Results saved to: {filename}")
    print(f"  Total test cases: {len(results)}")


def print_summary(results: List[Dict[str, Any]]):
    """Print summary statistics."""
    total = len(results)
    
    # Count by intent
    intents = {}
    for r in results:
        intent = r["intent"]
        intents[intent] = intents.get(intent, 0) + 1
    
    # Count by decision
    decisions = {}
    for r in results:
        decision = r["decision"]
        decisions[decision] = decisions.get(decision, 0) + 1
    
    # Count validation failures
    validation_failures = sum(1 for r in results if not r["validation_ok"])
    
    # Count with ambiguities
    with_ambiguities = sum(1 for r in results if r["ambiguities"] != "[]")
    
    # Count missing fields
    with_missing = sum(1 for r in results if r["missing_fields"] != "[]")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nTotal test cases: {total}")
    
    print("\nIntents:")
    for intent, count in sorted(intents.items()):
        pct = (count/total)*100
        bar = "█" * int(pct/2)
        print(f"  {intent:20} {count:3} ({pct:5.1f}%) {bar}")
    
    print("\nDecisions:")
    for decision, count in sorted(decisions.items()):
        pct = (count/total)*100
        bar = "█" * int(pct/2)
        print(f"  {decision:20} {count:3} ({pct:5.1f}%) {bar}")
    
    print(f"\n  Validation failures: {validation_failures}")
    print(f"  Cases with ambiguities: {with_ambiguities}")
    print(f"  Cases with missing fields: {with_missing}")
    
    # Average confidence
    confidences = [r["model_confidence"] for r in results if r["model_confidence"] is not None and r["model_confidence"] > 0]
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        print(f"\n  Model confidence: avg={avg_conf:.3f}, min={min_conf:.3f}, max={max_conf:.3f}")


def print_interesting_cases(results: List[Dict[str, Any]]):
    """Print potentially interesting or problematic cases."""
    print("\n" + "="*60)
    print("INTERESTING CASES")
    print("="*60)
    
    # Low confidence confirms
    print("\n🤔 Low confidence but confirmed:")
    low_conf_confirm = [r for r in results if r["decision"] == "confirm" and r["model_confidence"] and r["model_confidence"] < 0.8]
    for r in low_conf_confirm[:5]:
        print(f"  '{r['input']}' → {r['intent']}, conf={r['model_confidence']}")
    if not low_conf_confirm:
        print("  None found ✓")
    
    # High confidence clarify
    print("\n🧐 High confidence but needs clarification:")
    high_conf_clarify = [r for r in results if r["decision"] == "clarify" and r["model_confidence"] and r["model_confidence"] > 0.5]
    for r in high_conf_clarify[:5]:
        print(f"  '{r['input']}' → {r['intent']}, conf={r['model_confidence']}")
    if not high_conf_clarify:
        print("  None found ✓")
    
    # Validation failures
    print("\n⚠️  Validation failures:")
    validation_fails = [r for r in results if not r["validation_ok"]]
    for r in validation_fails[:5]:
        print(f"  '{r['input']}' → errors: {r['validation_errors']}")
    if not validation_fails:
        print("  None found ✓")


def main():
    # Check if server is running
    if not check_server():
        print("❌ Error: API server not running at", API_URL)
        print("\nStart it with: make start")
        print("or: python server.py")
        sys.exit(1)
    
    print("="*60)
    print("Fast Test Recorder (using API server)")
    print("="*60)
    print(f"\n📝 Running {len(TEST_CASES)} test cases...")
    print(f"   API: {API_URL}")
    print()
    
    results = []
    
    for i, test_input in enumerate(TEST_CASES, 1):
        # Progress bar
        if i % 5 == 0 or i == 1:
            pct = (i / len(TEST_CASES)) * 100
            bar = "█" * int(pct/2)
            print(f"Progress: [{bar:<50}] {i}/{len(TEST_CASES)} ({pct:.0f}%)", end='\r')
        
        result = run_test_via_api(test_input)
        results.append(result)
    
    print()  # New line after progress bar
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.csv"
    
    # Save to CSV
    save_to_csv(results, filename)
    
    # Print summary
    print_summary(results)
    
    # Print interesting cases
    print_interesting_cases(results)
    
    print("\n" + "="*60)
    print(f"✅ Complete! Review the results:")
    print(f"   📊 Spreadsheet: {filename}")
    print(f"   💡 Tip: Open in Excel/Google Sheets for filtering")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
