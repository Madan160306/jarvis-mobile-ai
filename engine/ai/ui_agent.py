import json
from engine.device.xml_parser import XMLParser
from engine.device.adb_helper import ADBHelper

class UIAgent:
    """Takes local XML dumps and parses them to extract a clean JSON list of interactable elements.
    Operates 100% offline via SMART XML FILTERING."""
    
    _last_elements = {}

    @staticmethod
    def analyze_screen() -> str:
        """Dumps UI XML, filters interactable elements, and returns clean JSON."""
        context = XMLParser.get_screen_context()
        
        # Cache for tap_element lookup
        UIAgent._last_elements.clear()
        for el in context.get("screen_elements", []):
            UIAgent._last_elements[el["id"]] = el
            
        return json.dumps(context, indent=2)

    @staticmethod
    def tap_element(element_id: int) -> str:
        """Taps an element by its ID."""
        if not UIAgent._last_elements:
            return "Error: Call analyze_screen() first to load elements."
            
        el = UIAgent._last_elements.get(element_id)
        if not el:
            return f"Error: Element ID {element_id} not found."
            
        x, y = el["x"], el["y"]
        res = ADBHelper.run_command(["shell", "input", "tap", str(x), str(y)])
        if "Error" in res:
            return res
        return f"Tapped element {element_id} '{el['text']}' at ({x}, {y})."
        
    @staticmethod
    def find_and_tap(description: str) -> str:
        """Fuzzy matches an element description and taps it."""
        elements = XMLParser.get_interactive_elements()
        if not elements:
            return "Error: No elements found on screen."
            
        best_match = None
        best_score = -1
        
        desc_lower = description.lower()
        for el in elements:
            text = el["text"].lower()
            if desc_lower in text or text in desc_lower:
                score = len(set(desc_lower.split()) & set(text.split()))
                if score > best_score:
                    best_score = score
                    best_match = el
                    
        if best_match:
            x, y = best_match["x"], best_match["y"]
            ADBHelper.run_command(["shell", "input", "tap", str(x), str(y)])
            return f"Found and tapped '{best_match['text']}' at ({x}, {y})."
            
        return f"Error: Could not find element matching '{description}'."
