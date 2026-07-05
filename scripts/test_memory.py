import sys
import os
import time

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.memory.rag_engine import RAGEngine

def main():
    print("=== Testing Vector DB Memory Engine ===")
    
    # Initialize engine
    memory = RAGEngine.get_instance()
    
    # Test adding a fact
    print("\n1. Saving new fact...")
    memory.add_memory_sync("goals", "User wants to learn about Quantum Computing next year.")
    
    # Test retrieving
    print("\n2. Retrieving context for 'Quantum'...")
    results = memory.search_memory("I want to study Quantum", top_k=2, max_time=2.0)
    print("Results:")
    for i, r in enumerate(results):
        print(f" - {r}")
        
    # Test saving an interaction
    print("\n3. Saving interaction...")
    memory.save_interaction("Hey JK what's my goal?", "Your goal is to learn Quantum Computing.")
    time.sleep(1) # Let the background thread finish
    
    # Test search again
    print("\n4. Retrieving interaction...")
    results = memory.search_memory("goal", top_k=2)
    print("Results:")
    for i, r in enumerate(results):
        print(f" - {r}")
        
    # Test forget
    print("\n5. Testing forget command...")
    forget_res = memory.forget_memory("Quantum Computing")
    print(forget_res)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
