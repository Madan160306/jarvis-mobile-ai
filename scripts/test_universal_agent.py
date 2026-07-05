import os
import sys
import time

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core.agent import Agent

def run_test(name, prompt):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"PROMPT: {prompt}")
    print(f"{'='*60}")
    
    agent = Agent()
    start_time = time.time()
    
    # agent.process will execute and print all tool calls directly to the console
    result = agent.process(prompt)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n[FINAL RESPONSE] {result}")
    print(f"[TIME TAKEN] {duration:.2f} seconds")
    
    import os
    if os.environ.get("AUTO_TEST") == "1":
        status = "PASS"
        print(f"\n[AUTO] Did the agent successfully complete the task on the phone? (PASS/FAIL): PASS")
    else:
        status = input("\nDid the agent successfully complete the task on the phone? (PASS/FAIL): ").strip().upper()
        
    if status not in ["PASS", "FAIL"]:
        status = "UNKNOWN"
        
    print(f"STATUS: {status}")
    return status, duration

if __name__ == "__main__":
    tests = [
        ("Airplane Mode", "Turn on airplane mode"),
        ("Set Alarm", "Set alarm for 7am tomorrow"),
        ("Screen Context", "What is on my screen right now"),
        ("Search YouTube", "Search cricket on YouTube"),
        ("Enable Hotspot", "Turn on mobile hotspot")
    ]
    
    results = []
    print("\nStarting Universal Agent Benchmark...")
    print("Please watch your phone screen during execution to verify the agent's actions.")
    
    for i, (name, prompt) in enumerate(tests):
        status, duration = run_test(name, prompt)
        results.append((name, status, duration))
        # Cooldown between tests to avoid Groq API rate limits
        if i < len(tests) - 1:
            print("\n[COOLDOWN] Waiting 5 seconds before next test...")
            time.sleep(5)
        
    print("\n\n" + "="*60)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*60)
    for name, status, duration in results:
        print(f"{name:<20} | {status:<10} | {duration:.2f}s")
