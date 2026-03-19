#!/usr/bin/env python3
"""
Simple test client for the process command parser API.
Usage: python test_client.py [message]
"""

import sys
import json
import requests

API_URL = "http://localhost:5000"


def test_single_command(message):
    """Test a single command"""
    response = requests.post(
        f"{API_URL}/parse",
        json={"message": message, "include_raw": False}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nInput: {message}")
        print(f"Intent: {result['intent']}")
        print(f"Process ID: {result['process_id']}")
        print(f"Decision: {result['decision']}")
        print(f"Confidence: {result['model_confidence']}")
        
        if result['ambiguities']:
            print(f"Ambiguities: {result['ambiguities']}")
        if result['missing_fields']:
            print(f"Missing: {result['missing_fields']}")
        
        print(f"\nSuggested response:")
        print(f"  {result['suggested_message']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def test_batch():
    """Test batch processing"""
    test_messages = [
        "turn off process 94",
        "disable 94",
        "enable process 12",
        "what is process 77 doing",
        "disable process",
        "don't disable process 94",
    ]
    
    response = requests.post(
        f"{API_URL}/batch",
        json={"messages": test_messages}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("\nBatch Test Results:")
        print("=" * 80)
        
        for result in data['results']:
            status = "✓" if result['decision'] == 'confirm' else "✗"
            print(f"{status} {result['input']:35} -> {result['intent']:20} PID:{result['process_id']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def check_health():
    """Check if server is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def interactive_mode():
    """Interactive testing mode"""
    print("\n" + "="*60)
    print("Interactive Command Parser Test")
    print("="*60)
    print("Type commands to test (or 'quit' to exit)")
    print("Examples:")
    print("  - turn off process 94")
    print("  - enable process 12")
    print("  - what is process 77 doing")
    print("="*60 + "\n")
    
    while True:
        try:
            message = input("Command> ").strip()
            
            if message.lower() in ['quit', 'exit', 'q']:
                break
            
            if not message:
                continue
            
            test_single_command(message)
            print()
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            break


if __name__ == '__main__':
    # Check if server is running
    if not check_health():
        print("Error: Server is not running at", API_URL)
        print("Start it with: python server.py")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # Single command mode
        message = ' '.join(sys.argv[1:])
        
        if message == '--batch':
            test_batch()
        else:
            test_single_command(message)
    else:
        # Interactive mode
        interactive_mode()
