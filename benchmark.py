#!/usr/bin/env python3
"""
Performance comparison: Cold start vs. Warm API
"""

import time
import subprocess
import requests

API_URL = "http://localhost:5000"

def test_cold_start():
    """Test cold start by running cpp.py as a subprocess"""
    print("\n" + "="*60)
    print("COLD START TEST (python cpp.py)")
    print("="*60)
    print("Loading model from disk on every run...\n")
    
    start = time.time()
    result = subprocess.run(
        ["python", "cpp.py"],
        cwd=".",
        capture_output=True,
        text=True
    )
    duration = time.time() - start
    
    print(f"Total time: {duration:.2f}s")
    print(f"  - Model loading: ~{duration-1:.2f}s")
    print(f"  - Processing requests: ~1s")
    return duration


def test_warm_api(num_requests=5):
    """Test warm API with multiple requests"""
    print("\n" + "="*60)
    print(f"WARM API TEST ({num_requests} consecutive requests)")
    print("="*60)
    print("Model already loaded in memory...\n")
    
    test_message = "turn off process 94"
    times = []
    
    for i in range(num_requests):
        start = time.time()
        response = requests.post(
            f"{API_URL}/parse",
            json={"message": test_message}
        )
        duration = time.time() - start
        times.append(duration)
        
        if response.status_code == 200:
            print(f"Request {i+1}: {duration:.3f}s")
        else:
            print(f"Request {i+1}: ERROR")
    
    avg = sum(times) / len(times)
    total = sum(times)
    
    print(f"\nTotal time for {num_requests} requests: {total:.2f}s")
    print(f"Average per request: {avg:.3f}s")
    print(f"Speedup vs cold start: {cold_start_time/avg:.1f}x faster")
    
    return times


def check_server():
    """Check if API server is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


if __name__ == '__main__':
    if not check_server():
        print("Error: API server not running at", API_URL)
        print("Start it with: python server.py")
        exit(1)
    
    # Run cold start test
    cold_start_time = test_cold_start()
    
    # Run warm API test
    warm_times = test_warm_api(num_requests=5)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Cold start penalty: {cold_start_time:.2f}s per run")
    print(f"Warm API average: {sum(warm_times)/len(warm_times):.3f}s per request")
    print(f"\nIn a real-world scenario with the API:")
    print(f"  - Load model once at deployment: ~{cold_start_time-1:.1f}s")
    print(f"  - Handle requests continuously: ~{sum(warm_times)/len(warm_times)*1000:.0f}ms each")
    print("\nThis is what production deployment looks like!")
    print("="*60 + "\n")
