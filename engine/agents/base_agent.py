from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    """
    Abstract Base Class for all JK Agents.
    Every agent in the Multi-Agent System must inherit from this.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    @abstractmethod
    def receive_task(self, task: Dict[str, Any]) -> str:
        """
        Receives a task from the Commander Agent.
        Must return a string response indicating the result.
        """
        pass
