from typing import Dict, Any
from engine.agents.base_agent import BaseAgent
from engine.agents.memory_agent import MemoryAgent
from engine.agents.device_agent import DeviceAgent

class CommanderAgent(BaseAgent):
    """
    The Main Brain. 
    Receives input, determines the intent, and delegates to the appropriate sub-agent.
    """
    
    def __init__(self):
        super().__init__(
            name="Commander Agent", 
            description="Central orchestrator for the JK Multi-Agent System."
        )
        # Initialize sub-agents lazily to avoid heavy loading
        self.memory_agent = None
        self.device_agent = None

    def route_task(self, task: Dict[str, Any]) -> str:
        """
        Routes the task dictionary to the correct specialized agent.
        """
        intent = task.get("intent", "unknown")
        print(f"[{self.name}] Routing task with intent: {intent}")

        if intent.startswith("memory"):
            if not self.memory_agent:
                self.memory_agent = MemoryAgent()
            
            # Map legacy memory intents (memory_add, memory_query) to actions
            if intent == "memory_add": task["action"] = "add"
            elif intent == "memory_query": task["action"] = "query"
            elif intent == "memory_forget": task["action"] = "forget"
                
            return self.memory_agent.receive_task(task)

        elif intent == "mobile" or intent == "device":
            if not self.device_agent:
                self.device_agent = DeviceAgent()
            return self.device_agent.receive_task(task)

        else:
            # Fallback for Phase 1: if it doesn't match an active agent, 
            # fall back to the legacy HybridLLM for generic chat.
            from engine.ai.hybrid_llm import HybridLLM
            raw = task.get("raw") or "Hello"
            lang = task.get("lang", "en")
            return HybridLLM.chat(raw, target_lang=lang)

    def receive_task(self, task: Dict[str, Any]) -> str:
        return self.route_task(task)
