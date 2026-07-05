import os
import json
import threading

class MacroEngine:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MacroEngine, cls).__new__(cls)
                cls._instance._init_engine()
            return cls._instance
            
    def _init_engine(self):
        self.macros_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "macros.json")
        self.current_recording_task = None
        self.current_actions = []
        self.macros = self._load_macros()
        
    def _load_macros(self):
        if os.path.exists(self.macros_file):
            try:
                with open(self.macros_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
        
    def _save_macros_to_disk(self):
        os.makedirs(os.path.dirname(self.macros_file), exist_ok=True)
        with open(self.macros_file, "w") as f:
            json.dump(self.macros, f, indent=4)
            
    def start_recording(self, task_name: str):
        """Start recording UI actions for a specific task."""
        self.current_recording_task = task_name.strip().lower()
        self.current_actions = []
        print(f"[MacroEngine] Started recording muscle memory for: '{self.current_recording_task}'")
        
    def record_step(self, step_description: str):
        """Record a semantic UI action (e.g., 'Clicked on Text: Wifi') into the current macro buffer."""
        if self.current_recording_task:
            self.current_actions.append(step_description)
            
    def save_macro(self, success: bool):
        """Save the recorded buffer to disk if the task was successful."""
        if self.current_recording_task and success:
            if len(self.current_actions) > 0:
                self.macros[self.current_recording_task] = self.current_actions
                self._save_macros_to_disk()
                print(f"[MacroEngine] Successfully memorized {len(self.current_actions)} steps for '{self.current_recording_task}'")
        self.current_recording_task = None
        self.current_actions = []
        
    def get_macro(self, task_name: str):
        """Retrieve a saved macro for a task."""
        task_name = task_name.strip().lower()
        return self.macros.get(task_name)
