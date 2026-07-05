import os
from mobilerun import MobileAgent
from engine.ai.hybrid_llm import LlamaIndexHybridAdapter

class JKMobileAgent:
    """Wraps the Mobilerun framework for high-level, 2026-era Android automation."""
    def __init__(self):
        self.llm = LlamaIndexHybridAdapter()
    
    async def execute(self, natural_language_task: str):
        """Passes the raw natural language task to Mobilerun.
        Mobilerun autonomously handles XML parsing, UI trees, and all navigation."""
        import subprocess
        
        # Explicitly extract device serial to prevent "No connected Android devices found" error
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        serial = None
        for line in lines[1:]:
            if 'device' in line and not 'offline' in line:
                serial = line.split()[0].strip()
                break
                
        if not serial:
            return "Error: No connected Android devices found."
            
        # Force the environment variable just in case
        os.environ["ANDROID_SERIAL"] = serial
        
        # Inject dynamic prompt engineering to fix LLM Android UI hallucinations
        enhanced_task = natural_language_task
        if "whatsapp" in natural_language_task.lower():
            enhanced_task += (
                "\n\n[CRITICAL WHATSAPP RULES]:\n"
                "1. To open a chat from the contacts or search list, click the person's NAME (TextView/Button). NEVER click their picture (ImageView) as it opens a modal instead of the chat.\n"
                "2. After typing your message into the text box, DO NOT press the Enter/Return key or type '\\n'. You MUST explicitly click the circular 'Send' button icon (a paper plane or triangle next to the text box) to actually send it!"
            )
        if "hotspot" in natural_language_task.lower():
            subprocess.run(["adb", "-s", serial, "shell", "am", "start", "-a", "android.settings.WIRELESS_SETTINGS"], capture_output=True)
            enhanced_task += "\n\n[CRITICAL]: I have already opened the Wireless Settings page for you! Do NOT go to the home screen or search. Just find the Hotspot toggle on this screen and click it."
            
        if "restart" in natural_language_task.lower() or "power" in natural_language_task.lower() or "reboot" in natural_language_task.lower() or "shut down" in natural_language_task.lower():
            subprocess.run(["adb", "-s", serial, "shell", "cmd", "statusbar", "expand-settings"], capture_output=True)
            enhanced_task += (
                "\n\n[CRITICAL SAMSUNG POWER RULES]:\n"
                "I have already expanded the Quick Settings panel for you! Do NOT open the Settings app (there is no restart button there). "
                "Just look for the Power menu icon at the top of the Quick Settings panel and click it to access the Restart/Power off buttons."
            )
            
        # --- SEMANTIC WAYPOINT INJECTION ---
        try:
            from engine.memory.macro_engine import MacroEngine
            cached_waypoints = MacroEngine().get_macro(natural_language_task)
            if cached_waypoints:
                waypoints_str = "\n".join([f"{i+1}. {step}" for i, step in enumerate(cached_waypoints)])
                enhanced_task += (
                    f"\n\n[CRITICAL SEMANTIC WAYPOINTS]:\n"
                    f"You have successfully solved this exact task before! To solve it instantly without blindly exploring, "
                    f"follow this exact proven semantic path:\n{waypoints_str}\n"
                    f"Look for these exact UI elements and interact with them in order."
                )
                print(f"[SemanticEngine] Injected {len(cached_waypoints)} waypoints into prompt for rapid execution.")
        except Exception as e:
            print(f"[SemanticEngine] Error injecting waypoints: {e}")
        # -----------------------------------
            
        try:
            from mobilerun.config_manager.config_manager import MobileConfig, DeviceConfig
            config = MobileConfig(device=DeviceConfig(serial=serial))
            agent = MobileAgent(
                goal=enhanced_task,
                llms=self.llm,
                config=config
            )
        except ImportError:
            # Fallback if config classes move
            agent = MobileAgent(
                goal=natural_language_task,
                llms=self.llm
            )
            
        result = await agent.run(
            reasoning=True,
            max_steps=15
        )
        return result
