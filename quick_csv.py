#!/usr/bin/env python3
"""
Quick test recorder - records a small set of representative tests to CSV quickly.
For full testing, edit TEST_CASES list or use record_tests_api.py.
"""

import csv
import json
import sys
import requests
from datetime import datetime

API_URL = "http://localhost:5000"

# Quick representative test set (add more as needed)
TEST_CASES = [
    # Expected: confirm
    "turn off process 94",
    "disable process 94",
    "enable process 12",
    "what is process 94 doing",
    "kill process 77",
    "start process 55",
    
    # Expected: clarify - missing ID
    "disable process",
    "turn off that process",
    "enable",
    
    # Expected: clarify - ambiguous
    "don't disable process 94",
    "disable process 94 and 95",
    "maybe stop process 12",
    
    # Expected: clarify - edge cases
    "hello",
    "94",
    "process 94",
]


def check_server():
    try:
        return requests.get(f"{API_URL}/health", timeout=2).status_code == 200
    except:
        return False


def run_test(input_text):
    try:
        resp = requests.post(f"{API_URL}/parse", json={"message": input_text}, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {
            "input": input_text,
            "intent": data.get("intent"),
            "process_id": data.get("process_id"),
            "decision": data.get("decision"),
            "model_confidence": data.get("model_confidence"),
            "ambiguities": ", ".join(data.get("ambiguities", [])) or "none",
            "missing_fields": ", ".join(data.get("missing_fields", [])) or "none",
            "suggested_message": data.get("suggested_message", ""),
        }
    except Exception as e:
        return None


def main():
    if not check_server():
        print(f"❌ Server not running at {API_URL}")
        print("Start with: make start")
        sys.exit(1)
    
    print(f"🚀 Quick CSV Test Recorder")
    print(f"   Running {len(TEST_CASES)} tests...\n")
    
    results = []
    for i, test_input in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {test_input[:50]}...")
        result = run_test(test_input)
        if result:
            results.append(result)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.csv"
    
    fieldnames = ["input", "intent", "process_id", "decision", "model_confidence", 
                  "ambiguities", "missing_fields", "suggested_message"]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✅ Done! Saved {len(results)} results to: {filename}")
    print(f"\n📊 Summary:")
    confirms = sum(1 for r in results if r['decision'] == 'confirm')
    clarifies = sum(1 for r in results if r['decision'] == 'clarify')
    print(f"   Confirm: {confirms}")
    print(f"   Clarify: {clarifies}")
    print(f"\n💡 Open {filename} in Excel/Sheets for review")
    print(f"   Add more tests to TEST_CASES list in this file\n")


if __name__ == '__main__':
    main()
