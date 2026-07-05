import os
import re
import json
import xml.etree.ElementTree as ET
from engine.device.adb_helper import ADBHelper

class XMLParser:
    @staticmethod
    def get_screen_context() -> dict:
        """Returns the current app package, screen title (if any), and filtered UI elements."""
        # Get current focus
        focus_res = ADBHelper.run_command(["shell", "dumpsys", "window", "|", "grep", "mCurrentFocus"])
        current_app = "Unknown"
        if "mCurrentFocus" in focus_res:
            try:
                match = re.search(r'u0 (.*?)/', focus_res)
                if match:
                    current_app = match.group(1)
            except:
                pass

        elements = XMLParser.get_interactive_elements()
        return {
            "current_app": current_app,
            "screen_elements": elements
        }

    @staticmethod
    def get_interactive_elements(max_elements=20) -> list:
        """Dumps XML, parses it locally, and filters strictly to max_elements."""
        xml_path = "/sdcard/window_dump.xml"
        local_path = os.path.join(os.path.dirname(__file__), "window_dump.xml")
        
        ADBHelper.run_command(["shell", "uiautomator", "dump", xml_path])
        ADBHelper.run_command(["pull", xml_path, local_path])
        
        if not os.path.exists(local_path):
            return XMLParser._get_grid_fallback()
            
        try:
            tree = ET.parse(local_path)
            root = tree.getroot()
            
            raw_elements = []
            
            for node in root.iter('node'):
                bounds_str = node.attrib.get('bounds', '')
                text = node.attrib.get('text', '').strip()
                content_desc = node.attrib.get('content-desc', '').strip()
                cls_name = node.attrib.get('class', '')
                
                clickable = node.attrib.get('clickable', 'false') == 'true'
                focusable = node.attrib.get('focusable', 'false') == 'true'
                is_interactive_class = any(t in cls_name for t in ['Button', 'EditText', 'Switch', 'CheckBox', 'TabWidget'])
                
                if not (clickable or focusable or is_interactive_class):
                    continue
                    
                match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                if not match:
                    continue
                    
                x1, y1, x2, y2 = map(int, match.groups())
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                label = text if text else content_desc
                if not label and not is_interactive_class:
                    continue # Ignore layout containers without labels
                
                if not label:
                    label = cls_name.split('.')[-1]
                
                el_type = "button"
                if "Switch" in cls_name or "CheckBox" in cls_name:
                    el_type = "toggle_on" if node.attrib.get('checked', 'false') == 'true' else "toggle_off"
                elif "EditText" in cls_name:
                    el_type = "input"
                    
                # Calculate priority score for sorting
                priority = 0
                if text or content_desc: priority += 10
                if "Button" in cls_name: priority += 5
                if "Switch" in cls_name: priority += 5
                if "EditText" in cls_name: priority += 5
                # Prefer upper half of screen slightly
                if center_y < 1200: priority += 2
                
                raw_elements.append({
                    "text": label,
                    "type": el_type,
                    "x": center_x,
                    "y": center_y,
                    "priority": priority
                })
            
            # If extremely few elements found, fallback to grid
            if len(raw_elements) < 2:
                return XMLParser._get_grid_fallback()
                
            # Sort by priority descending and take top N
            raw_elements.sort(key=lambda x: x["priority"], reverse=True)
            top_elements = raw_elements[:max_elements]
            
            # Format output
            formatted = []
            for idx, el in enumerate(top_elements, 1):
                formatted.append({
                    "id": idx,
                    "text": el["text"],
                    "type": el["type"],
                    "x": el["x"],
                    "y": el["y"]
                })
                
            return formatted
            
        except Exception:
            return XMLParser._get_grid_fallback()
        finally:
            if os.path.exists(local_path):
                try: os.remove(local_path)
                except: pass

    @staticmethod
    def _get_grid_fallback():
        """Fallback for Flutter/Games with no XML structure. 3x6 grid."""
        grid = []
        id_counter = 1
        # Assuming 1080x2400 standard resolution
        cell_w = 1080 // 3
        cell_h = 2400 // 6
        
        for row in range(6):
            for col in range(3):
                grid.append({
                    "id": id_counter,
                    "text": f"Grid Zone Row {row+1} Col {col+1}",
                    "type": "zone",
                    "x": (col * cell_w) + (cell_w // 2),
                    "y": (row * cell_h) + (cell_h // 2)
                })
                id_counter += 1
        return grid
