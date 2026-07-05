import os
import sys
import time

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.ai.local_llm import LLMEngine

def test_offline():
    print("======================================================================")
    print("OFFLINE LOCAL 3B LLM INFERENCE VERIFICATION")
    print("======================================================================\n")

    # 1. Test Chat / Personality
    print("1. Testing Conversational Chat Responses:")
    print("-" * 50)
    chat_queries = [
        "Who are you?",
        "Tell me a joke",
        "What can you do?"
    ]
    for q in chat_queries:
        start = time.time()
        reply = LLMEngine.chat(q)
        duration = time.time() - start
        print(f"Query:    '{q}'")
        print(f"Reply:    '{reply}'")
        print(f"Duration: {duration:.2f} seconds")
        print()

    # 2. Test Intent Classification
    print("2. Testing Few-Shot Command/Intent Classification:")
    print("-" * 50)
    commands = [
        "turn on the flashlight",
        "open chrome",
        "check mobile battery",
        "how are you today?"
    ]
    for cmd in commands:
        start = time.time()
        intent = LLMEngine.classify_command(cmd)
        duration = time.time() - start
        print(f"Command:  '{cmd}'")
        print(f"Parsed:   {intent}")
        print(f"Duration: {duration:.2f} seconds")
        print()

    # 3. Test Translation
    print("3. Testing Translation:")
    print("-" * 50)
    translations = [
        ("Hello, how can I help you?", "en", "es"),
        ("What is the time?", "en", "fr")
    ]
    for text, src, dest in translations:
        start = time.time()
        translated = LLMEngine.translate(text, src, dest)
        duration = time.time() - start
        print(f"Original ({src}): '{text}'")
        print(f"Translated ({dest}): '{translated}'")
        print(f"Duration: {duration:.2f} seconds")
        print()

    # 4. Test Text Enhancement
    print("4. Testing Text Enhancement (Email):")
    print("-" * 50)
    rough = "i cant attend class today"
    start = time.time()
    enhanced = LLMEngine.enhance_text(rough, "professional email")
    duration = time.time() - start
    print(f"Rough:    '{rough}'")
    print(f"Enhanced: '{enhanced}'")
    print(f"Duration: {duration:.2f} seconds")
    print()

if __name__ == "__main__":
    test_offline()
