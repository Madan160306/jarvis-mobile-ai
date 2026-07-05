import os
import json
import base64
from engine.device.adb_helper import ADBHelper
from engine.ai.hybrid_llm import HybridLLM

class AIScreenReader:

    @staticmethod
    def capture_base64_screenshot() -> str:
        """Takes a screenshot via ADB and returns it as a base64 encoded string."""
        ADBHelper.run_command(["shell", "screencap", "/sdcard/ai_screen.png"])
        local_path = "temp_ai_screen.png"
        ADBHelper.run_command(["pull", "/sdcard/ai_screen.png", local_path])
        
        if not os.path.exists(local_path):
            return None
            
        with open(local_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        try:
            os.remove(local_path)
        except:
            pass
            
        return encoded_string

    @staticmethod
    def verify_screen(condition_description: str) -> bool:
        """
        Sends the current screen to Groq Vision and asks to verify a condition.
        Returns True if the condition is met, False otherwise.
        """
        base64_image = AIScreenReader.capture_base64_screenshot()
        if not base64_image:
            return False
            
        try:
            prompt = f"""You are a mobile UI automation assistant. Look at the provided screenshot of a mobile phone screen.
Evaluate this condition: '{condition_description}'
Reply ONLY with a raw JSON object containing a boolean field 'verified'. For example: {{"verified": true}} or {{"verified": false}}."""

            result_str = HybridLLM.vision_completion(
                prompt=prompt,
                base64_image=base64_image,
                response_format={"type": "json_object"},
                max_tokens=256
            )
            result_json = json.loads(result_str)
            
            is_verified = bool(result_json.get("verified", False))
            print(f"[AIScreenReader] Verification for '{condition_description}': {is_verified}")
            return is_verified
            
        except Exception as e:
            print(f"[AIScreenReader] Vision Verification API Error: {e}")
            return False

    @staticmethod
    def find_element_with_vision(target_description: str) -> tuple:
        """
        Sends the current screen to Groq Vision and asks for the coordinates of the target element.
        Returns a tuple of (x, y) if found, else None.
        """
        base64_image = AIScreenReader.capture_base64_screenshot()
        if not base64_image:
            print("[AIScreenReader] Failed to capture screenshot.")
            return None

        try:
            prompt = f"""You are a mobile UI automation assistant. Look at the provided screenshot of a mobile phone screen.
Find the exact location of the UI element described as: "{target_description}".
Estimate the exact center pixel coordinates (x, y) of this element. 
Assume a standard mobile resolution (e.g., 1080x2400) if you are unsure, but scale appropriately to the image provided.
Output ONLY a raw JSON object with the format: {{"x": 500, "y": 800}}. Do not include any other text or markdown formatting."""

            result_str = HybridLLM.vision_completion(
                prompt=prompt,
                base64_image=base64_image,
                response_format={"type": "json_object"},
                max_tokens=256
            )
            result_json = json.loads(result_str)
            
            x = int(result_json.get("x", -1))
            y = int(result_json.get("y", -1))
            
            if x >= 0 and y >= 0:
                print(f"[AIScreenReader] Found '{target_description}' at ({x}, {y})")
                return (x, y)
                
            return None
            
        except Exception as e:
            print(f"[AIScreenReader] Vision API Error: {e}")
            return None
