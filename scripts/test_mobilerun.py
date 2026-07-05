import sys
import os
import time
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.device.mobile_agent import JKMobileAgent

async def run_tests():
    agent = JKMobileAgent()
    
    test_cases = [
        "Send hello to Sandeep on WhatsApp",
        "Play Shape of You on YouTube",
        "Open Instagram and search cricket",
        "Turn on airplane mode",
        "Set alarm for 7am tomorrow",
        "Open Gmail and read latest email",
        "Turn on Dolby Atmos in settings",
        "Enable battery saver mode"
    ]
    
    print("=== Mobilerun Benchmark ===")
    
    for idx, case in enumerate(test_cases, 1):
        print(f"\n[Test {idx}] {case}")
        start_time = time.time()
        
        try:
            # Note: Since the agent requires an actual device and internet, this might fail 
            # or time out depending on the environment. We catch exceptions to allow the suite to finish.
            result = await agent.execute(case)
            status = "PASS" if result else "FAIL"
        except Exception as e:
            result = str(e)
            status = "ERROR"
            
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Status: {status}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(run_tests())
