import subprocess

DEEP_LINK_HANDLERS = {
    "whatsapp_send": 
        "adb shell am start -a android.intent.action.VIEW "
        "-d 'whatsapp://send?phone={phone}&text={text}'",
    
    "whatsapp_contact":
        "adb shell am start -a android.intent.action.VIEW "
        "-d 'whatsapp://send?phone={phone}'",
    
    "youtube_search":
        "adb shell am start -a android.intent.action.SEARCH "
        "-n com.google.android.youtube/.app.honeycomb.Shell\\$HomeActivity "
        "--es query '{query}'",
    
    "youtube_play":
        "adb shell am start -a android.intent.action.VIEW "
        "-d 'vnd.youtube:{video_id}'",
    
    "spotify_search":
        "adb shell am start -a android.intent.action.VIEW "
        "-d 'spotify:search:{query}'",
    
    "maps_navigate":
        "adb shell am start -a android.intent.action.VIEW "
        "-d 'google.navigation:q={destination}'",
    
    "phone_call":
        "adb shell am start -a android.intent.action.CALL "
        "-d 'tel:{number}'",
    
    "sms_send":
        "adb shell am start -a android.intent.action.SENDTO "
        "-d 'smsto:{number}' --es sms_body '{text}'",
    
    "gmail_compose":
        "adb shell am start -a android.intent.action.SENDTO "
        "-d 'mailto:{email}' --es subject '{subject}' "
        "--es body '{body}'",
    
    "instagram_profile":
        "adb shell am start -a android.intent.action.VIEW "
        "-d 'instagram://user?username={username}'",
    
    "settings_wifi":
        "adb shell am start -a android.settings.WIFI_SETTINGS",
    
    "settings_bluetooth":
        "adb shell am start "
        "-a android.settings.BLUETOOTH_SETTINGS",
    
    "settings_battery":
        "adb shell am start "
        "-a android.settings.BATTERY_SAVER_SETTINGS",
    
    "settings_display":
        "adb shell am start "
        "-a android.settings.DISPLAY_SETTINGS",
}

def execute_deep_link(action: str, params: dict) -> str:
    import os
    if os.path.exists('/data/data/com.termux'):
        from engine.device.termux_controller import make_call, send_sms, send_whatsapp, torch_on, torch_off, get_battery, read_notifications
        
        try:
            if action == "phone_call":
                make_call(params.get("number", ""))
                return "Making call via Termux API"
            elif action == "sms_send":
                send_sms(params.get("number", ""), params.get("text", ""))
                return "Sending SMS via Termux API"
            elif action == "whatsapp_send" or action == "whatsapp_contact":
                send_whatsapp(params.get("phone", ""), params.get("text", ""))
                return "Opening WhatsApp via Termux API"
            elif action == "torch_on":
                torch_on()
                return "Turned on torch via Termux API"
            elif action == "torch_off":
                torch_off()
                return "Turned off torch via Termux API"
            elif action == "battery":
                return get_battery()
            elif action == "notifications":
                return read_notifications()
            else:
                # For youtube/maps/etc, we can use termux-open-url
                url = None
                if action == "youtube_search":
                    url = f"https://www.youtube.com/results?search_query={params.get('query','')}"
                elif action == "maps_navigate":
                    url = f"google.navigation:q={params.get('destination','')}"
                elif action == "spotify_search":
                    url = f"spotify:search:{params.get('query','')}"
                    
                if url:
                    subprocess.run(['termux-open-url', url])
                    return f"Opened {action} via termux-open-url"
                return f"Deep link {action} not natively supported in Termux Lite mode."
        except Exception as e:
            return f"Termux API execution failed: {e}"

    # Standard ADB execution
    template = DEEP_LINK_HANDLERS.get(action)
    if not template:
        return None  # fall back to Mobilerun
        
    cmd = template.format(**params)
    print(f"[DeepLink] Executing: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True)
    if result.returncode == 0:
        return f"Done via deep link: {action}"
    else:
        print(f"[DeepLink] Failed: {result.stderr.decode()}")
        return None
