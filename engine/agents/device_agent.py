from typing import Dict, Any
from engine.agents.base_agent import BaseAgent
from engine.device.android_controller import AndroidController
from engine.ai.hybrid_llm import HybridLLM

class DeviceAgent(BaseAgent):
    """
    Agent responsible for controlling connected mobile and PC devices.
    Acts as JK's hands.
    """
    
    def __init__(self):
        super().__init__(
            name="Device Control Agent", 
            description="Controls apps, settings, and hardware on mobile and PC."
        )

    def receive_task(self, task: Dict[str, Any]) -> str:
        action = task.get("action")
        target = task.get("target")
        value = task.get("value")
        raw = task.get("raw", "")
        lang = task.get("lang", "en")

        # Basic exact mappings for speed
        if action == "wifi": return AndroidController.toggle_wifi(value or "on")
        elif action == "bluetooth": return AndroidController.toggle_bluetooth(value or "on")
        elif action == "torch": return AndroidController.toggle_torch(value or "on")
        elif action == "hotspot": return AndroidController.toggle_hotspot(value or "on")
        elif action == "dnd": return AndroidController.toggle_dnd(value or "on")
        elif action == "open_app": return AndroidController.open_app(target or "")
        elif action == "whatsapp": return AndroidController.send_whatsapp(target or "", value or "")
        elif action == "send_sms": return AndroidController.send_sms(target or "", value or "")
        elif action == "make_call": return AndroidController.make_call(target or "")
        elif action == "play_youtube": return AndroidController.play_youtube(target or value or "")
        elif action == "play_spotify": return AndroidController.play_spotify(target or value or "")
        elif action == "search_instagram": return AndroidController.search_instagram(target or value or "")
        elif action == "read_emails": return AndroidController.read_emails()
        elif action == "read_notifs": return AndroidController.read_notifications()
        elif action == "check_battery": return AndroidController.get_battery()
        elif action == "battery_saver": return AndroidController.toggle_battery_saver(value or "on")
        elif action == "check_disk": return AndroidController.get_disk_usage()
        elif action == "set_brightness": return AndroidController.set_brightness(int(value) if value else 50)
        elif action == "volume": return AndroidController.change_volume(value or "up")
        elif action == "screenshot": return AndroidController.take_screenshot()
        elif action == "press_key": return AndroidController.press_key(value or "home")
        elif action == "lock": return AndroidController.press_key("power")
            
        # Semantic Action Routing for fuzzy or unmapped requests
        print(f"[{self.name}] Routing complex device request to Semantic Tool-Calling LLM...")
        prompt = f"The user issued a device control command: '{raw}'. Use your mobile automation tools to execute it (e.g., mobile_open_app, mobile_toggle_setting, mobile_play_media). If it's a custom command that doesn't fit predefined tools (like battery protection or brightness), use execute_adb or execute_powershell. Respond with a short confirmation message."
        return HybridLLM.chat(prompt, target_lang=lang)
