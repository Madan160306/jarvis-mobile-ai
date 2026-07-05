import os
import sys
import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.ai.ui_agent import UIAgent

def count_tokens(text: str) -> int:
    """Rough approximation of Llama/GPT token count (1 token ~= 4 chars)."""
    return len(text) // 4

def run_tests():
    print("=== UI Agent Smart XML Filtering Benchmark ===\n")
    
    # 1. Test analyze_screen latency and token bloat
    print("Testing analyze_screen()...")
    start_time = time.time()
    screen_json = UIAgent.analyze_screen()
    end_time = time.time()
    
    latency = end_time - start_time
    tokens = count_tokens(screen_json)
    
    data = json.loads(screen_json)
    elements_count = len(data.get("screen_elements", []))
    
    print(f"Latency: {latency:.2f} seconds")
    print(f"Token count: ~{tokens} tokens")
    print(f"Elements extracted: {elements_count}")
    print(f"Target < 500 tokens? {'PASS' if tokens < 500 else 'FAIL'}")
    print(f"Target < 1.0s? {'PASS' if latency < 1.0 else 'FAIL'}")
    
    print("\nSample Output:")
    print(json.dumps(data, indent=2))
    
    # 2. Test tap_element latency
    print("\nTesting tap_element(1)...")
    if elements_count > 0:
        start_time = time.time()
        res = UIAgent.tap_element(1)
        end_time = time.time()
        
        tap_latency = end_time - start_time
        print(f"Result: {res}")
        print(f"Latency: {tap_latency:.2f} seconds")
        print(f"Target < 0.5s? {'PASS' if tap_latency < 0.5 else 'FAIL'}")
    else:
        print("No elements to tap.")
        
    print("\nAll tests completed.")

if __name__ == "__main__":
    run_tests()
