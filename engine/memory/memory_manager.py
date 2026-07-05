import os
import json
import datetime
from typing import List, Dict

class MemoryManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MemoryManager()
        return cls._instance

    def __init__(self, memory_file="memory.json", max_history=20):
        self.memory_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), memory_file)
        self.max_history = max_history
        self.history: List[Dict] = []
        self.facts: List[str] = []
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
                    self.facts = data.get("facts", [])
            except Exception:
                self.history = []
                self.facts = []
        else:
            self.history = []
            self.facts = []

    def _save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({"history": self.history, "facts": self.facts}, f, indent=4)
        except Exception as e:
            print(f"[ERROR] Could not save memory: {e}")

    def add_interaction(self, user_text: str, jk_text: str):
        if not user_text.strip() or not jk_text.strip():
            return
            
        timestamp = datetime.datetime.now().isoformat()
        self.history.append({
            "timestamp": timestamp,
            "user": user_text, 
            "jk": jk_text
        })
        
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
        self._extract_facts(user_text)
        self._save_memory()

    def _extract_facts(self, text: str):
        # A simple offline fact extractor.
        text_lower = text.lower()
        if "my name is" in text_lower:
            name = text_lower.split("my name is")[-1].strip()
            self.add_fact(f"User's name is {name}")
        elif "i am learning" in text_lower:
            topic = text_lower.split("i am learning")[-1].strip()
            self.add_fact(f"User is learning {topic}")
        elif "preparing for" in text_lower:
            topic = text_lower.split("preparing for")[-1].strip()
            self.add_fact(f"User is preparing for {topic}")
        elif "i have an exam" in text_lower or "my exam" in text_lower:
            self.add_fact("User has an exam coming up")

    def add_fact(self, fact: str):
        if fact not in self.facts:
            self.facts.append(fact)
            self._save_memory()

    def get_context_string(self) -> str:
        context = ""
        if self.facts:
            context += "Facts about the User:\n"
            for fact in self.facts:
                context += f"- {fact}\n"
            context += "\n"
            
        if self.history:
            context += "Recent Conversation History:\n"
            for interaction in self.history:
                # Optionally parse timestamp if needed, but simple display is fine
                context += f"User: {interaction['user']}\nJK: {interaction.get('jk')}\n"
            context += "\n"
        return context

    def clear(self):
        self.history = []
        self._save_memory()
