from engine.device.android_controller import AndroidController

def test():
    print("=== 2026 MOBILE AUTOMATION TESTS ===")
    
    tests = [
        ("WhatsApp", lambda: AndroidController.send_whatsapp("Sandeep", "Hello from JK")),
        ("YouTube", lambda: AndroidController.play_youtube("Attention Charlie Puth")),
        ("Spotify", lambda: AndroidController.play_spotify("Blinding Lights")),
        ("Instagram", lambda: AndroidController.search_instagram("cricket")),
        ("Emails", lambda: AndroidController.read_emails()),
        ("Screenshot", lambda: AndroidController.take_screenshot()),
        ("Flashlight", lambda: AndroidController.toggle_torch("on")),
        ("Brightness", lambda: AndroidController.set_brightness(70))
    ]
    
    for name, func in tests:
        print(f"\n[TESTING] {name}...")
        try:
            res = func()
            print(f"[SUCCESS] {res}")
        except Exception as e:
            print(f"[FAILED] Exception: {e}")

if __name__ == "__main__":
    test()
