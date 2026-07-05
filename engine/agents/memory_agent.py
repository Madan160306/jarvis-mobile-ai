from typing import Dict, Any
from engine.agents.base_agent import BaseAgent
from engine.memory.rag_engine import RAGEngine

class MemoryAgent(BaseAgent):
    """
    Agent responsible for long-term memory, context retrieval, and habit tracking.
    """
    
    def __init__(self):
        super().__init__(
            name="Memory Agent", 
            description="Handles semantic search and long-term memory management."
        )
        self.memory_engine = None

    def _get_engine(self):
        if self.memory_engine is None:
            self.memory_engine = RAGEngine.get_instance()
        return self.memory_engine

    def receive_task(self, task: Dict[str, Any]) -> str:
        action = task.get("action")
        value = task.get("value", "")
        
        try:
            engine = self._get_engine()
            
            if action == "add":
                engine.add_facts_async("explicit_memory", [value])
                return "I've saved that to my long-term memory."
                
            elif action == "query":
                results = engine.search_memory(value, top_k=5, max_time=1.0)
                if results:
                    return "Here is what I found in memory:\n" + "\n".join(f"- {m}" for m in results)
                return "I couldn't find any relevant memories about that."
                
            elif action == "forget":
                return engine.forget_memory(value)
                
            return f"Memory Agent doesn't know how to handle action: {action}"
            
        except Exception as e:
            return f"Memory Agent encountered an error: {e}"
