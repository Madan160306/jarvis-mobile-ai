import os
import sys
import uuid
import sqlite3

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core.agent import Agent
from engine.ai.hybrid_llm import HybridLLM

def test_checkpointing():
    print("============================================================")
    print("TESTING STATE CHECKPOINTING AND DURABILITY")
    print("============================================================")
    
    config = HybridLLM._load_config()
    db_path = config.get("checkpoint_db", "logs/jk_checkpoints.db")
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Cleared older checkpoints database at: {db_path}")
        except Exception as e:
            print(f"Could not clear older checkpoints: {e}")
            
    agent = Agent()
    thread_id = f"test-thread-{uuid.uuid4()}"
    print(f"Initiating agent task with unique Thread ID: {thread_id}")
    
    # Run the process for a basic command
    # This will compile the graph, run the reason node, and save state to SQLite.
    response = agent.process("turn on mobile hotspot", thread_id=thread_id)
    print(f"Agent reply: {response}")
    
    # Verify that checkpoints were written to the SQLite database
    if not os.path.exists(db_path):
        print(f"[-] FAIL: Checkpoints database was not created at {db_path}")
        return False
        
    print(f"[+] SUCCESS: Checkpoints database created at {db_path}")
    
    # Inspect SQLite database tables and checkpoints
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # In LangGraph v0.2+, checkpoints are stored in checkpoint tables
        # Let's list tables to verify
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Database tables found: {tables}")
        
        if not any("checkpoint" in t for t in tables):
            print("[-] FAIL: No checkpoint tables found in database.")
            return False
            
        print("[+] SUCCESS: LangGraph checkpoint tables found.")
        
        # Check if checkpoints exist for our thread_id
        cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?;", (thread_id,))
        count = cursor.fetchone()[0]
        print(f"Total saved checkpoints for thread {thread_id}: {count}")
        
        if count == 0:
            print("[-] FAIL: No checkpoints found in database for our thread_id.")
            return False
            
        print(f"[+] SUCCESS: {count} checkpoints successfully verified in database!")
        conn.close()
        return True
    except Exception as e:
        print(f"[-] Error querying checkpoint database: {e}")
        return False

if __name__ == "__main__":
    success = test_checkpointing()
    sys.exit(0 if success else 1)
