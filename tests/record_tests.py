#!/usr/bin/env python3
"""
Test recorder - runs test cases and saves results to CSV for analysis.
"""
import sys
import os

# Add parent directory to path so we can import slm package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import csv
import json
from datetime import datetime
from typing import List, Dict, Any

from slm.process_intents import (
    parse_command,
    validate_result,
    system_decision,
)

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


def run_test(input_text: str) -> Dict[str, Any]:
    """Run a single test and return all results."""
    result = parse_command(input_text, debug=False)
    validation_ok, validation_errors = validate_result(result)
    decision = system_decision(result, validation_ok)
    
    return {
        "input": input_text,
        "intent": result.get("intent"),
        "process_id": result.get("process_id"),
        "ambiguities": json.dumps(result.get("ambiguities", [])),
        "missing_fields": json.dumps(result.get("missing_fields", [])),
        "model_confidence": result.get("model_confidence"),
        "decision": decision,
        "validation_ok": validation_ok,
        "validation_errors": json.dumps(validation_errors),
        "raw_output": result.get("_raw_model_output", ""),
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
    
    print(f"\nResults saved to: {filename}")
    print(f"Total test cases: {len(results)}")


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
        print(f"  {intent:20} {count:3} ({pct:5.1f}%)")
    
    print("\nDecisions:")
    for decision, count in sorted(decisions.items()):
        pct = (count/total)*100
        print(f"  {decision:20} {count:3} ({pct:5.1f}%)")
    
    print(f"\nValidation failures: {validation_failures}")
    print(f"Cases with ambiguities: {with_ambiguities}")
    print(f"Cases with missing fields: {with_missing}")
    
    # Average confidence
    confidences = [r["model_confidence"] for r in results if r["model_confidence"] is not None]
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        print(f"\nAverage model confidence: {avg_conf:.3f}")
        
        # Confidence by intent
        print("\nConfidence by intent:")
        for intent in sorted(intents.keys()):
            intent_confs = [r["model_confidence"] for r in results 
                          if r["intent"] == intent and r["model_confidence"] is not None]
            if intent_confs:
                avg = sum(intent_confs) / len(intent_confs)
                print(f"  {intent:20} {avg:.3f}")


def print_preview(results: List[Dict[str, Any]], num: int = 10):
    """Print first N results as a preview."""
    print("\n" + "="*60)
    print(f"PREVIEW (first {num} results)")
    print("="*60)
    
    for i, r in enumerate(results[:num], 1):
        print(f"\n{i}. Input: {r['input']}")
        print(f"   Intent: {r['intent']}, PID: {r['process_id']}, Decision: {r['decision']}")
        if r['ambiguities'] != "[]":
            print(f"   Ambiguities: {r['ambiguities']}")
        if r['missing_fields'] != "[]":
            print(f"   Missing: {r['missing_fields']}")


def main():
    print("="*60)
    print("Test Recorder - Running test cases...")
    print("="*60)
    print(f"\nTotal test cases to run: {len(TEST_CASES)}")
    print("This will take a moment...\n")
    
    results = []
    
    for i, test_input in enumerate(TEST_CASES, 1):
        if i % 10 == 0:
            print(f"Progress: {i}/{len(TEST_CASES)}")
        
        try:
            result = run_test(test_input)
            results.append(result)
        except Exception as e:
            print(f"Error on test {i} ('{test_input}'): {e}")
            results.append({
                "input": test_input,
                "intent": "error",
                "process_id": None,
                "ambiguities": "[]",
                "missing_fields": "[]",
                "model_confidence": 0,
                "decision": "error",
                "validation_ok": False,
                "validation_errors": json.dumps([str(e)]),
                "raw_output": "",
            })
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_results_{timestamp}.csv"
    
    # Save to CSV
    save_to_csv(results, filename)
    
    # Print summary
    print_summary(results)
    
    # Print preview
    print_preview(results, num=10)
    
    print("\n" + "="*60)
    print(f"✓ Complete! Open {filename} in Excel/Sheets for analysis")
    print("="*60)


if __name__ == '__main__':
    main()
