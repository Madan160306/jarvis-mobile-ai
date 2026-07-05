import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.ai.tools import execute_tool

def run_tests():
    print("=== Testing JK Tools ===")

    tests = [
        ("calculate", {"expression": "15% of 8500"}),
        ("check_weather", {"city": "Kurnool"}),
        ("english_mentor", {"text": "I have went to market", "mode": "correct"}),
        ("code_mentor", {"code": "explain binary search", "language": "Python", "mode": "explain"}),
        ("placement_prep", {"company": "TCS", "topic": "aptitude questions"}),
        ("get_time", {}),
        ("search_web", {"query": "latest Python interview questions 2026"})
    ]

    for tool_name, params in tests:
        print(f"\n--- Testing Tool: {tool_name} ---")
        print(f"Params: {params}")
        try:
            result = execute_tool(tool_name, params)
            print(f"Result:\n{result}")
        except Exception as e:
            print(f"Error testing {tool_name}: {e}")

if __name__ == "__main__":
    run_tests()
