import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core.command_parser import parse_command
from engine.core.executor import execute
from engine.ai.hybrid_llm import HybridLLM
from engine.personality.emotion_detector import EmotionDetector
from engine.network.network_utils import NetworkUtils

def print_separator():
    print("-" * 50)

def test_intent_parsing(scenario: str, text: str):
    print(f"\n[Test] {scenario}")
    print(f"User: {text}")
    parsed = parse_command(text)
    
    print(f"Parsed Intent: {parsed['intent']}")
    print(f"Parsed Action: {parsed['action']}")
    
    # We won't execute full TTS or device commands to avoid spamming the system
    if parsed['intent'] == "chat":
        # Simulate hybrid LLM call
        print("-> Routing to HybridLLM Chat")
        reply = HybridLLM.chat(text)
        print(f"JK: {reply}")
    else:
        print(f"-> Routing to Executor ({parsed['intent']} handler)")
        print(f"Action triggered: {parsed['action']} (No API call)")

def main():
    print("=== HYBRID SYSTEM TEST ===")
    
    print("\n--- EMOTION DETECTION ---")
    emotions = [
        "explain recursion in Python",
        "I failed my exam",
        "tell me a joke",
        "I need to calm down"
    ]
    for text in emotions:
        res = EmotionDetector.detect_emotion(text)
        print(f"'{text}' -> Emotion: {res['emotion']}, Mode: {res['mode']}")

    print_separator()

    # Ensure config allows online
    print(f"Online Status (NetworkUtils): {NetworkUtils.is_online()}")
    print(f"Can use Online API (HybridLLM): {HybridLLM._can_use_online()}")

    test_intent_parsing("Mentor scenario", "hey jk explain recursion in Python")
    test_intent_parsing("Support scenario", "hey jk I failed my exam")
    test_intent_parsing("Comedy scenario", "hey jk tell me a joke")
    test_intent_parsing("Healing scenario", "hey jk I need to calm down")
    test_intent_parsing("Search scenario", "hey jk what is the latest Python version")
    test_intent_parsing("Offline Device scenario 1", "hey jk lock the phone")
    test_intent_parsing("Offline Device scenario 2", "hey jk turn on flashlight")
    
    print_separator()
    print("Testing offline simulation...")
    # Force offline mode
    original_check = NetworkUtils.is_online
    NetworkUtils.is_online = lambda force=False: False
    print(f"Simulated Online Status: {NetworkUtils.is_online()}")
    
    test_intent_parsing("Simulated Offline Conversation", "hello jk how are you today")
    test_intent_parsing("Simulated Offline Mentoring", "hey jk teach me python")
    
    # Restore
    NetworkUtils.is_online = original_check

if __name__ == "__main__":
    main()
