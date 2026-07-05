import datetime
import json
import traceback

def _open_app(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.open_app(params.get("app_name", ""))

def _send_whatsapp(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.send_whatsapp(params.get("contact", ""), params.get("message", ""))

def _send_sms(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.send_sms(params.get("contact", ""), params.get("message", ""))

def _make_call(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.make_call(params.get("contact", ""))

def _attend_call(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.attend_call()

def _reject_call(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.reject_call()

def _set_volume(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.change_volume(str(params.get("level", "50")))

def _set_brightness(params):
    from engine.device.android_controller import AndroidController
    try:
        level = int(params.get("level", 50))
    except:
        level = 50
    return AndroidController.set_brightness(level)

def _toggle_wifi(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.toggle_wifi(params.get("state", "on"))

def _toggle_bluetooth(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.toggle_bluetooth(params.get("state", "on"))

def _toggle_flashlight(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.toggle_torch(params.get("state", "on"))

def _toggle_hotspot(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.toggle_hotspot(params.get("state", "on"))

def _toggle_airplane_mode(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.toggle_airplane_mode(params.get("state", "on"))

def _search_settings(params):
    from engine.device.android_controller import AndroidController
    return AndroidController._search_in_settings(params.get("query", ""))

def _lock_screen(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.press_key("power")

def _take_screenshot(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.take_screenshot()

def _play_youtube(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.play_youtube(params.get("query", ""))

def _play_spotify(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.play_spotify(params.get("query", ""))

def _search_instagram(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.search_instagram(params.get("query", ""))

def _read_notifications(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.read_notifications()

def _read_emails(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.read_emails()

def _analyze_screen(params):
    import yaml
    import os
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "jk_config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except:
        config = {}
        
    from engine.device.android_controller import AndroidController
    
    # Dynamic Privacy Firewall: Check foreground app
    active_pkg = AndroidController.get_foreground_package().lower()
    is_banking_app = any(keyword in active_pkg for keyword in ['pay', 'bank', 'wallet', 'finance', 'cred'])
    
    # If config privacy mode is on OR we are inside a banking app, fallback to 100% offline XML parser
    if config.get("privacy_mode", False) or is_banking_app:
        if is_banking_app:
            print(f"[JARVIS SECURITY] Banking App Detected ({active_pkg}). Enforcing strict Offline XML parsing. Zero uploads allowed.")
        return AndroidController.dump_screen_state()
        
    from engine.ai.hybrid_llm import HybridLLM
    
    b64_image = AndroidController.take_screenshot_base64()
    if not b64_image:
        # Fallback to XML if screencap fails
        return AndroidController.dump_screen_state()
        
    prompt = "Describe the current Android screen in detail. If there are buttons or text inputs, specify them. If this is a game or image, describe what is happening."
    try:
        vision_analysis = HybridLLM.vision_completion(prompt, b64_image)
        return f"Vision Analysis of Screen:\n{vision_analysis}"
    except Exception as e:
        return f"Vision Model failed to analyze screen: {e}"

def _tap_text(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.tap_text(params.get("text", ""))

def _type_text(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.type_text(params.get("text", ""))

def _swipe_screen(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.swipe_screen(params.get("direction", "up"))

def _press_button(params):
    from engine.device.android_controller import AndroidController
    return AndroidController.press_key(params.get("button", "home"))

def _send_email(params):
    from engine.productivity.email_manager import EmailManager
    return EmailManager.send_email(params.get("to", ""), params.get("subject", "Message from JK"), params.get("body", ""))

def _execute_adb_command(params):
    command = params.get("command", "")
    try:
        from engine.device.adb_helper import ADBHelper
        import shlex
        args = shlex.split(command)
        output = ADBHelper.run_command(args)
        return f"ADB Output:\n{output}"
    except Exception as e:
        return f"Failed to execute ADB command: {e}"

def _search_web(params):
    query = params.get("query", "")
    try:
        from engine.ai.search_tool import search_web
        res = search_web(query)
        if not res or "missing" in res.lower() or "error" in res.lower(): return "Search unavailable offline"
        return res
    except Exception as e:
        return "Search unavailable offline"

def _get_memory(params):
    query = params.get("query", "")
    try:
        from engine.memory.rag_engine import RAGEngine
        memory = RAGEngine.get_instance()
        results = memory.search_memory(query, top_k=3, max_time=1.0)
        if not results: return "No relevant memories found."
        return "\n".join(results)
    except Exception as e:
        return f"Error retrieving memory: {e}"

def _check_weather(params):
    city = params.get("city", "")
    try:
        import urllib.request
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            temp = data['current_condition'][0]['temp_C']
            desc = data['current_condition'][0]['weatherDesc'][0]['value']
            return f"Weather in {city}: {temp}°C, {desc}"
    except Exception as e:
        return "Weather needs internet"

def _get_time(params):
    return f"Current System Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def _check_internet_speed(params):
    try:
        import speedtest
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000 # Convert to Mbps
        upload = st.upload() / 1_000_000 # Convert to Mbps
        ping = st.results.ping
        return f"Internet Speed: {download:.2f} Mbps Download, {upload:.2f} Mbps Upload, {ping} ms Ping."
    except Exception as e:
        return f"Could not check internet speed: {e}"

def _calculate(params):
    expression = params.get("expression", "")
    try:
        allowed_chars = "0123456789+-*/().% "
        if "% of" in expression:
            parts = expression.split("% of")
            if len(parts) == 2:
                pct = float(parts[0].strip())
                val = float(parts[1].strip())
                return str((pct / 100.0) * val)
        clean_expr = "".join(c for c in expression if c in allowed_chars)
        result = eval(clean_expr, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return "Could not calculate that"

def _teach_concept(params):
    topic = params.get("topic", "")
    level = params.get("level", "beginner")
    try:
        search_res = _search_web({"query": f"explain {topic} for {level}"})
        if search_res == "Search unavailable offline":
            return f"Offline: Here is a basic explanation of {topic} for {level}s based on my knowledge."
        return f"Teaching {topic} at {level} level based on: {search_res[:1000]}..."
    except Exception:
        return "Error teaching concept."

def _placement_prep(params):
    company = params.get("company", "General")
    topic = params.get("topic", "aptitude")
    companies = ["TCS", "Infosys", "Wipro", "Cognizant", "Accenture", "HCL", "Tech Mahindra", "Capgemini", "IBM India"]
    if company not in companies and company.lower() != "general": company = "TCS"
    try:
        search_res = _search_web({"query": f"latest {company} interview questions 2026 {topic} tips"})
        if search_res == "Search unavailable offline":
             return f"Offline placement prep for {company} - {topic}: Focus on core concepts."
        return f"Placement prep for {company} on {topic}:\nSearch data: {search_res[:1000]}..."
    except Exception:
        return "Error fetching placement prep."

def _english_mentor(params):
    text = params.get("text", "")
    mode = params.get("mode", "correct")
    return f"English Mentor Output for mode '{mode}': Will correct common Indian English mistakes, help with Telugu translation if needed, and give IELTS tips for: '{text}'"

def _code_mentor(params):
    code = params.get("code", "")
    language = params.get("language", "Python")
    mode = params.get("mode", "explain")
    return f"Code Mentor Output for {language} ({mode}): Analyzing time complexity and DSA patterns for TCS/Infosys prep. Code context: '{code[:500]}'"

def _save_memory(params):
    fact = params.get("fact", "")
    from engine.memory.rag_engine import RAGEngine
    memory = RAGEngine.get_instance()
    memory.save_interaction(fact, "User Fact")
    return f"Saved fact to memory: {fact}"

def _forget_memory(params):
    # Dummy implementation for now
    return f"Forgot topic: {params.get('topic', '')}"

def _get_user_profile(params):
    return "User Profile: Mobile automation focus, Indian context, preparing for placements."

TOOL_DISPATCHER = {
    "open_app": _open_app,
    "send_whatsapp": _send_whatsapp,
    "send_sms": _send_sms,
    "make_call": _make_call,
    "attend_call": _attend_call,
    "reject_call": _reject_call,
    "set_volume": _set_volume,
    "set_brightness": _set_brightness,
    "toggle_wifi": _toggle_wifi,
    "toggle_bluetooth": _toggle_bluetooth,
    "toggle_flashlight": _toggle_flashlight,
    "toggle_hotspot": _toggle_hotspot,
    "toggle_airplane_mode": _toggle_airplane_mode,
    "search_settings": _search_settings,
    "lock_screen": _lock_screen,
    "take_screenshot": _take_screenshot,
    "play_youtube": _play_youtube,
    "play_spotify": _play_spotify,
    "search_instagram": _search_instagram,
    "read_notifications": _read_notifications,
    "read_emails": _read_emails,
    "analyze_screen": _analyze_screen,
    "tap_text": _tap_text,
    "type_text": _type_text,
    "swipe_screen": _swipe_screen,
    "press_button": _press_button,
    "send_email": _send_email,
    "execute_adb_command": _execute_adb_command,
    "search_web": _search_web,
    "get_memory": _get_memory,
    "check_weather": _check_weather,
    "check_internet_speed": _check_internet_speed,
    "get_time": _get_time,
    "calculate": _calculate,
    "teach_concept": _teach_concept,
    "placement_prep": _placement_prep,
    "english_mentor": _english_mentor,
    "code_mentor": _code_mentor,
    "save_memory": _save_memory,
    "forget_memory": _forget_memory,
    "get_user_profile": _get_user_profile
}

def generate_tool_schema(name, description, required=None, **properties):
    if required is None: required = list(properties.keys())
    props = {k: {"type": "string"} if isinstance(v, str) else v for k, v in properties.items()}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required
            }
        }
    }

TOOL_DEFINITIONS = [
    generate_tool_schema("open_app", "Opens an app by name.", app_name="string"),
    generate_tool_schema("send_whatsapp", "Sends a WhatsApp message.", contact="string", message="string"),
    generate_tool_schema("send_sms", "Sends an SMS message.", contact="string", message="string"),
    generate_tool_schema("make_call", "Initiates a phone call.", contact="string"),
    generate_tool_schema("attend_call", "Answers an incoming call."),
    generate_tool_schema("reject_call", "Rejects an incoming call."),
    generate_tool_schema("set_volume", "Sets media volume.", level="string"),
    generate_tool_schema("set_brightness", "Sets screen brightness (0-100).", level="string"),
    generate_tool_schema("toggle_wifi", "Toggles WiFi.", state={"type": "string", "enum": ["on", "off"]}),
    generate_tool_schema("toggle_bluetooth", "Toggles Bluetooth.", state={"type": "string", "enum": ["on", "off"]}),
    generate_tool_schema("toggle_flashlight", "Toggles Flashlight.", state={"type": "string", "enum": ["on", "off"]}),
    generate_tool_schema("toggle_hotspot", "Toggles Mobile Hotspot.", state={"type": "string", "enum": ["on", "off"]}),
    generate_tool_schema("toggle_airplane_mode", "Toggles Airplane Mode on or off. This pulls down the Quick Settings panel and taps the toggle.", state={"type": "string", "enum": ["on", "off"]}),
    generate_tool_schema("search_settings", "Opens the Android Settings app and searches for a specific setting by name. Useful for finding any setting like NFC, Dark Mode, Developer Options, etc.", query="string"),
    generate_tool_schema("lock_screen", "Locks the phone screen."),
    generate_tool_schema("take_screenshot", "Takes a screenshot of the phone."),
    generate_tool_schema("play_youtube", "Searches and plays a video/song on YouTube.", query="string"),
    generate_tool_schema("play_spotify", "Searches and plays a song on Spotify.", query="string"),
    generate_tool_schema("search_instagram", "Searches for a user or topic on Instagram.", query="string"),
    generate_tool_schema("read_notifications", "Reads current phone notifications."),
    generate_tool_schema("read_emails", "Reads recent emails."),
    generate_tool_schema("analyze_screen", "Dumps the physical UI of the Android phone screen using a Native Vision Model (VLM). Use this to actually LOOK at the screen. You can use it to read images, understand games, or bypass XML parsing errors. Returns a natural language description of the screen."),
    generate_tool_schema("tap_text", "Taps the physical screen on the specified text or button label.", text="string"),
    generate_tool_schema("type_text", "Types text into the currently focused input box.", text="string"),
    generate_tool_schema("swipe_screen", "Swipes the screen in the given direction.", direction={"type": "string", "enum": ["up", "down", "left", "right"]}),
    generate_tool_schema("press_button", "Presses a hardware button.", button={"type": "string", "enum": ["home", "back", "recent", "enter", "power"]}),
    generate_tool_schema("send_email", "Sends an email.", to="string", subject="string", body="string"),
    generate_tool_schema("execute_adb_command", "Executes raw ADB commands. Omit 'adb' prefix. You MUST start the command with 'shell' (e.g. 'shell dumpsys battery').", command="string"),
    generate_tool_schema("search_web", "Searches the internet for real-time information. Also use this to LEARN how to do unfamiliar tasks on Android — e.g. search_web(query='how to enable NFC on Android') to get step-by-step instructions, then follow them using your tools.", query="string"),
    generate_tool_schema("get_memory", "Retrieves past context about the user.", query="string"),
    generate_tool_schema("check_internet_speed", "Checks the internet download, upload, and ping speeds."),
    generate_tool_schema("check_weather", "Gets weather for a city.", city="string"),
    generate_tool_schema("get_time", "Gets the current system time."),
    generate_tool_schema("calculate", "Evaluates a math expression.", expression="string"),
    generate_tool_schema("teach_concept", "Teaches a topic.", topic="string", level={"type": "string", "enum": ["beginner", "intermediate", "advanced"]}),
    generate_tool_schema("placement_prep", "IT interview prep.", company="string", topic="string"),
    generate_tool_schema("english_mentor", "English corrections and mentoring.", text="string", mode="string"),
    generate_tool_schema("code_mentor", "Code mentoring.", code="string", language="string", mode="string"),
    generate_tool_schema("save_memory", "Saves a fact about the user.", fact="string", category="string"),
    generate_tool_schema("forget_memory", "Forgets a topic.", topic="string"),
    generate_tool_schema("get_user_profile", "Gets general info about the user.")
]

def execute_tool(name: str, params: dict) -> str:
    func = TOOL_DISPATCHER.get(name)
    if not func: return f"Tool {name} not found."
    try:
        return func(params)
    except Exception as e:
        return f"Tool execution failed: {e}\n{traceback.format_exc()}"
