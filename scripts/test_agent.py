import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core.agent import Agent

def test():
    agent = Agent()
    
    test_cases = [
        "turn on touc",
        "watsap hello to mom",
        "yutub lofi music",
        "how much battery is left",
        "TCS prep questions",
        "I am feeling low",
        "15 percent of 8500",
        "weather outside in Kurnool",
        "correct my english: i am go to market",
        "explain quicksort"
    ]
    
    print("="*50)
    print("Testing Agentic Loop with 10 Fuzzy Queries")
    print("="*50)
    
    for case in test_cases:
        print(f"\n[QUERY] -> {case}")
        response = agent.process(case)
        print(f"[REPLY] <- {response}")
        print("-" * 50)

if __name__ == "__main__":
    test()
