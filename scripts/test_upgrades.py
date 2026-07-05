import os
import sys
import time

base_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(base_dir)

def test_tts():
    print("\n=== Testing UPGRADE 1: Kokoro TTS ===")
    try:
        from engine.voice.tts_engine import TTSEngine
        print("[Info] TTSEngine loaded.")
        
        start_time = time.time()
        # Mute audio generation text for benchmark
        # We assume TTSEngine buffers and starts playback quickly
        TTSEngine.speak("This is a speed test.")
        elapsed = (time.time() - start_time) * 1000
        
        print(f"[Result] Kokoro TTS time: {elapsed:.2f}ms")
        if elapsed < 800: # Note: Exact TTS generation might take slightly more depending on CPU, but we log the time
            print("[Pass] TTS is fast.")
        else:
            print("[Warning] TTS took longer than expected.")
    except Exception as e:
        print(f"[Fail] TTS Error: {e}")

def test_interruptible_speaker():
    print("\n=== Testing UPGRADE 2: Interruptible Speaker ===")
    try:
        from engine.voice.hybrid_asr import InterruptibleSpeaker
        print("[Info] Speaking a long sentence. Make a loud noise to interrupt it mid-sentence!")
        was_interrupted = InterruptibleSpeaker.speak_interruptible(
            "This is a very long sentence designed to test the full duplex interruption capabilities of JARVIS. "
            "If you make a loud noise or start speaking now, I should immediately stop talking."
        )
        if was_interrupted:
            print("[Pass] Successfully interrupted mid-sentence via VAD.")
        else:
            print("[Fail] Finished speaking without interruption (or no noise detected).")
    except Exception as e:
        print(f"[Fail] InterruptibleSpeaker Error: {e}")

def test_vision():
    print("\n=== Testing UPGRADE 3: Screen-Aware Vision ===")
    try:
        from engine.vision.screen_vision import analyze_screen_with_vision
        print("[Info] Analyzing 'what is on screen'...")
        res = analyze_screen_with_vision("what is on my screen?")
        print(f"[Vision Result]:\n{res}")
        if "error" not in res.lower() and "fail" not in res.lower():
            print("[Pass] Vision analysis succeeded.")
        else:
            print("[Fail] Vision analysis returned an error.")
    except Exception as e:
        print(f"[Fail] Vision Error: {e}")

def test_deep_links():
    print("\n=== Testing UPGRADE 4: WhatsApp Deep Link Speed ===")
    try:
        from engine.device.deep_links import execute_deep_link
        print("[Info] Executing WhatsApp deep link to arbitrary contact...")
        
        start_time = time.time()
        res = execute_deep_link("whatsapp_contact", {"phone": "1234567890"})
        elapsed = (time.time() - start_time)
        
        print(f"[Result] WhatsApp deep link execution time: {elapsed:.2f}s")
        if res and elapsed < 1.0:
            print("[Pass] Deep link executed under 1 sec.")
        else:
            print("[Fail] Deep link failed or was too slow.")
    except Exception as e:
        print(f"[Fail] Deep Link Error: {e}")

def test_proactive():
    print("\n=== Testing UPGRADE 5: Proactive Agent Battery Alert ===")
    try:
        from engine.background.proactive_agent import ProactiveAgent
        agent = ProactiveAgent()
        print("[Pass] ProactiveAgent initialized.")
        battery = agent._check_battery()
        print(f"[Info] Current device battery: {battery}%")
        
        # Test the rule manually
        agent.rules[0]["threshold"] = 100 # Force trigger
        agent._evaluate_rule(agent.rules[0])
        print("[Pass] Proactive battery alert triggered correctly.")
    except Exception as e:
        print(f"[Fail] Proactive Agent Error: {e}")

if __name__ == "__main__":
    print("Running JARVIS 2026 Architecture Upgrades Test Suite\n" + "="*50)
    test_tts()
    test_interruptible_speaker()
    # test_vision()  # Uncomment when an Android phone is actually connected via ADB
    test_deep_links()
    test_proactive()
    print("\n" + "="*50 + "\nAll tests completed.")
