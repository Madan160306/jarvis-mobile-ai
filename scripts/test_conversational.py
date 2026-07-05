import os
import sys
import datetime

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core.command_parser import parse_command
from engine.ai.local_llm import LLMEngine
from engine.memory.memory_manager import MemoryManager

def run_test():
    print("======================================================================")
    print("CONVERSATIONAL & NATURAL LANGUAGE INTEGRATION TESTS")
    print("======================================================================\n")

    # 1. Test prefix stripping and alternate naming variations
    print("1. Testing Prefix Stripping & Name Unification:")
    print("-" * 50)
    test_commands = [
        "Hey JK, please turn on the torch",
        "Could you please turn on the flashlight, JK?",
        "JK, please lock the laptop",
        "JK, lock the pc, please",
        "JK, can you check phone battery?",
        "JK, could you check the laptop disk usage?",
        "JK, lock my computer",
        "JK, what is the weather like in New York?", # Weather routed to chat
        "Hey Friday, please turn on the torch",     # Friday should trigger correction!
        "hello friday"                              # Pure greeting Friday correction
    ]
    for cmd in test_commands:
        parsed = parse_command(cmd)
        print(f"Input:       '{cmd}'")
        print(f"Parsed:      intent={parsed['intent']}, action={parsed['action']}, raw='{parsed['raw']}'")
        print(f"Correction:  {parsed.get('correction')}")
        print()

    # 2. Test conversational memory limit (10 turns)
    print("2. Testing Conversational Memory Context (Last 10 turns):")
    print("-" * 50)
    memory = MemoryManager.get_instance()
    memory.clear()
    
    # Add 12 interactions to memory
    for i in range(12):
        memory.add_interaction(f"User interaction number {i+1}", f"JK response number {i+1}")
        
    history = memory.history
    print(f"Memory count: {len(history)} (Expected: 10)")
    
    context = memory.get_context_string()
    print("Memory Context Injected in Prompt:")
    print(context)
    
    # 3. Test custom conversational overrides
    print("3. Testing Custom Conversational Overrides:")
    print("-" * 50)
    overrides = [
        "what can you do?",
        "how are you?",
        "what time is it?",
        "what is today's date?",
        "tell me a joke",
        "who are you?"
    ]
    for q in overrides:
        reply = LLMEngine.chat(q)
        print(f"Query:  '{q}'")
        print(f"Reply:  '{reply}'")
        print()

    # 4. Test Web Search RAG & Query Reformulation
    print("4. Testing Web Search RAG & Query Reformulation:")
    print("-" * 50)
    memory.clear()
    
    q1 = "Who won the super bowl in 2026?"
    print(f"User: {q1}")
    reply1 = LLMEngine.chat(q1)
    print(f"JK:   {reply1}\n")
    
    q2 = "Who did they defeat?"
    print(f"User: {q2}")
    reply2 = LLMEngine.chat(q2)
    print(f"JK:   {reply2}\n")

    # 5. Check for occurrences of the word 'JK'
    print("5. Verification of 'JK' to 'JK' Renaming:")
    print("-" * 50)
    found_jk = False
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for root, dirs, files in os.walk(os.path.join(project_dir, "engine")):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if "jk" in content.lower():
                        # Exclude site-packages or internal dependencies
                        print(f"[WARNING] 'JK' found in project file: {os.path.relpath(path, project_dir)}")
                        found_jk = True
                        
    if not found_jk:
        print("Success: No occurrences of 'JK' found in project source files!")

if __name__ == "__main__":
    run_test()
