#!/usr/bin/env python3
"""
Console demo for the process command parser.
Quick way to test the parser interactively or run the test suite.
"""
import sys
import os

# Add parent directory to path so we can import slm package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from slm.process_intents import (
    parse_command,
    validate_result,
    system_decision,
    TEST_CASES,
)


def demo_single_command(message: str):
    """Demo: Parse a single command and show results."""
    print("\n" + "="*80)
    print("INPUT:")
    print(message)
    print("="*80)
    
    result = parse_command(message, debug=False)
    validation_ok, validation_errors = validate_result(result)
    decision = system_decision(result, validation_ok)

    print("\nPARSED RESULT:")
    print(json.dumps({k: v for k, v in result.items() if k != "_raw_model_output"}, indent=2))

    print("\nVALIDATION:")
    print(json.dumps({
        "validation_ok": validation_ok,
        "validation_errors": validation_errors,
        "decision": decision,
    }, indent=2))

    print("\nSYSTEM RESPONSE:")
    if decision == "confirm":
        print(f'✓ I understand you want to {result["intent"].replace("_", " ")} for process {result["process_id"]}.')
    else:
        print("⚠ Need clarification:")
        if result["missing_fields"]:
            print(f"  Missing: {', '.join(result['missing_fields'])}")
        if result["ambiguities"]:
            print(f"  Ambiguous: {', '.join(result['ambiguities'])}")


def run_test_suite():
    """Run the full test suite and show summary."""
    import pandas as pd
    
    print("\n" + "="*80)
    print("RUNNING TEST SUITE")
    print("="*80 + "\n")
    
    rows = []
    for i, case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] Testing: {case['input']}")
        result = parse_command(case["input"], debug=False)
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
        })

    df = pd.DataFrame(rows)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    intent_match = (df["expected_intent"] == df["actual_intent"]).sum()
    pid_match = (df["expected_pid"] == df["actual_pid"]).sum()
    decision_match = (df["expected_decision"] == df["actual_decision"]).sum()
    print(f"Intent matches: {intent_match}/{len(df)} ({100*intent_match/len(df):.1f}%)")
    print(f"Process ID matches: {pid_match}/{len(df)} ({100*pid_match/len(df):.1f}%)")
    print(f"Decision matches: {decision_match}/{len(df)} ({100*decision_match/len(df):.1f}%)")
    
    # Show failures
    failures = df[(df["expected_intent"] != df["actual_intent"]) | 
                  (df["expected_pid"] != df["actual_pid"]) |
                  (df["expected_decision"] != df["actual_decision"])]
    
    if len(failures) > 0:
        print(f"\n⚠ {len(failures)} FAILURES:")
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 180)
        print(failures.to_string(index=False))
    else:
        print("\n✓ All tests passed!")


if __name__ == '__main__':
    import sys
    
    # If command provided, parse it
    if len(sys.argv) > 1:
        message = ' '.join(sys.argv[1:])
        demo_single_command(message)
    else:
        # Run test suite
        run_test_suite()
        
        # Show example command
        print("\n" + "="*80)
        print("DEMO EXAMPLE")
        print("="*80)
        demo_single_command("turn off process 94 please")
