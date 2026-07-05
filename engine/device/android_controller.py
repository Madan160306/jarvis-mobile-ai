import time
import subprocess
import base64
import io
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
from engine.device.adb_helper import ADBHelper

class AndroidController:
    """Low-level primitive controller for Autonomous VLM navigation."""
    
    @staticmethod
    def tap_coordinates(x: int, y: int) -> str:
        """Taps the exact (x, y) coordinates."""
        res = ADBHelper.run_command(["shell", "input", "tap", str(x), str(y)])
        if "Error" in res:
            return res
        return f"Tapped at ({x}, {y})."

    @staticmethod
    def swipe_screen(params: dict) -> str:
        """Swipes the screen in the given direction to scroll."""
        direction = params.get("direction", "down").lower()
        # Default screen bounds mapping
        # x, y, end_x, end_y
        swipes = {
            "down": ["540", "400", "540", "1800"],  # swipe down (scrolls up)
            "up": ["540", "1800", "540", "400"],    # swipe up (scrolls down)
            "left": ["800", "1000", "200", "1000"],
            "right": ["200", "1000", "800", "1000"]
        }
        coords = swipes.get(direction, swipes["down"])
        res = ADBHelper.run_command(["shell", "input", "swipe"] + coords + ["300"])
        if "Error" in res:
            return res
        return f"Swiped {direction}."

    @staticmethod
    def type_text(params: dict) -> str:
        """Types text into currently focused input box."""
        text = params.get("text", "")
        if not text:
            return "No text provided."
        # Escape spaces for ADB
        escaped_text = text.replace(" ", "%s")
        res = ADBHelper.run_command(["shell", "input", "text", escaped_text])
        if "Error" in res:
            return res
        return f"Typed '{text}'."

    @staticmethod
    def press_button(params: dict) -> str:
        """Presses a physical hardware button."""
        button = params.get("button", "home").lower()
        keycodes = {
            "home": "KEYCODE_HOME",
            "back": "KEYCODE_BACK",
            "recent": "KEYCODE_APP_SWITCH",
            "enter": "KEYCODE_ENTER",
            "power": "KEYCODE_POWER"
        }
        keycode = keycodes.get(button, "KEYCODE_HOME")
        res = ADBHelper.run_command(["shell", "input", "keyevent", keycode])
        if "Error" in res:
            return res
        return f"Pressed {button} button."
    @staticmethod
    def swipe_coordinates(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> str:
        """Executes a raw coordinate-based swipe on the screen."""
        res = ADBHelper.run_command(["shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)])
        if "Error" in res:
            return res
        return f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})."

    @staticmethod
    def take_screenshot_base64() -> str:
        """Takes a fast screenshot, compresses it to 512x512, and returns a Base64 string."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
            png_path = tmp_png.name
            
        try:
            # Take screenshot directly to local machine using adb exec-out (much faster than saving to sdcard and pulling)
            res = subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True)
            if res.returncode != 0 or not res.stdout:
                return ""
                
            if HAS_PIL:
                img = Image.open(io.BytesIO(res.stdout))
                img = img.convert("RGB")
                img.thumbnail((512, 512))
                
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                return b64
            else:
                # Fallback: Just return the raw full-resolution PNG as base64
                return base64.b64encode(res.stdout).decode("utf-8")
        except Exception as e:
            print(f"Screenshot Error: {e}")
            return ""
        finally:
            if os.path.exists(png_path):
                try: os.remove(png_path)
                except: pass

    @staticmethod
    def tap_text(target_text: str) -> str:
        """Taps the exact text, or self-heals using Semantic Similarity if UI changed."""
        import xml.etree.ElementTree as ET
        import tempfile
        import os
        import re

        def extract_bounds(bounds_str):
            matches = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
            if len(matches) == 2:
                x1, y1 = int(matches[0][0]), int(matches[0][1])
                x2, y2 = int(matches[1][0]), int(matches[1][1])
                return (x1 + x2) // 2, (y1 + y2) // 2
            return 0, 0

        # Dump UI XML
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            xml_path = tmp.name
        
        try:
            subprocess.run(['adb', 'shell', 'uiautomator', 'dump'], capture_output=True, timeout=5)
            subprocess.run(['adb', 'pull', '/sdcard/window_dump.xml', xml_path], capture_output=True, timeout=5)
            
            tree = ET.parse(xml_path)
            root = tree.getroot()
            elements = []
            
            for node in root.iter('node'):
                text = node.attrib.get('text', '')
                desc = node.attrib.get('content-desc', '')
                bounds = node.attrib.get('bounds', '')
                
                label = text if text else desc
                if label and bounds:
                    x, y = extract_bounds(bounds)
                    elements.append({"label": label, "x": x, "y": y})
            
            # Phase 1: Exact Match (Fast Path)
            target_lower = target_text.lower().strip()
            for el in elements:
                if el["label"].lower().strip() == target_lower:
                    res = AndroidController.tap_coordinates(el["x"], el["y"])
                    return f"Tapped exact match '{el['label']}'. {res}"
            
            # Phase 2: Semantic Healing (AI Path)
            print(f"[AndroidController] '{target_text}' not found. Initiating Self-Healing UI Loop...")
            try:
                from sentence_transformers import SentenceTransformer, util
                # Load the local model (offline, fast cache)
                encoder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu', local_files_only=True)
                
                target_vec = encoder.encode(target_text)
                best_match = None
                highest_score = -1.0
                
                for el in elements:
                    # Discard extremely short/symbol labels to prevent junk matching
                    if len(el["label"]) < 2: continue
                    
                    el_vec = encoder.encode(el["label"])
                    score = util.cos_sim(target_vec, el_vec).item()
                    if score > highest_score:
                        highest_score = score
                        best_match = el
            except ImportError:
                return f"Failed to tap '{target_text}'. Semantic Healing disabled (sentence_transformers not installed)."
                    
            if best_match and highest_score > 0.40:
                print(f"[AndroidController] Healed! Found '{best_match['label']}' (Score: {highest_score:.2f})")
                res = AndroidController.tap_coordinates(best_match["x"], best_match["y"])
                return f"Self-Healed: Tapped '{best_match['label']}' (Similarity: {highest_score:.2f}). {res}"
            else:
                return f"Failed to tap '{target_text}'. No semantic match found above threshold."
                
        except Exception as e:
            return f"Failed to process UI: {e}"
        finally:
            if os.path.exists(xml_path):
                try: os.remove(xml_path)
                except: pass

    @staticmethod
    def get_foreground_package() -> str:
        """Returns the package name of the currently active Android app."""
        try:
            res = subprocess.run(['adb', 'shell', 'dumpsys', 'activity', 'activities'], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=2)
            for line in res.stdout.split('\n'):
                if 'topResumedActivity' in line or 'mResumedActivity' in line:
                    # Example line: topResumedActivity=ActivityRecord{... com.android.chrome/...}
                    parts = line.split(' ')
                    for p in parts:
                        if '/' in p and '.' in p:
                            pkg = p.split('/')[0]
                            return pkg.strip()
        except Exception:
            pass
        return ""
