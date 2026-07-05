import base64
import os
import subprocess
from engine.ai.hybrid_llm import HybridLLM

def capture_screen_base64() -> str:
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, "screen.png")
    
    # Run adb commands to capture and pull
    subprocess.run(['adb', 'shell', 'screencap', '-p', '/sdcard/screen.png'], capture_output=True)
    subprocess.run(['adb', 'pull', '/sdcard/screen.png', temp_file], capture_output=True)
    
    if not os.path.exists(temp_file):
        raise FileNotFoundError("Could not capture screenshot via ADB.")
        
    with open(temp_file, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('utf-8')
        
    # Cleanup
    try:
        os.remove(temp_file)
        subprocess.run(['adb', 'shell', 'rm', '/sdcard/screen.png'], capture_output=True)
    except:
        pass
        
    return encoded

def analyze_screen_with_vision(user_question: str) -> str:
    print("[Vision] Capturing Android screen...")
    try:
        screenshot_b64 = capture_screen_base64()
    except Exception as e:
        return f"Sorry, I couldn't capture the screen: {e}"
        
    print("[Vision] Screen captured. Analyzing with Groq Vision (llama-4-scout-17b-16e-instruct)...")
    try:
        # We use the existing HybridLLM vision method which supports Groq Vision!
        response = HybridLLM.vision_completion(
            prompt=f"You are JK, an AI assistant. The user is asking about their phone screen. {user_question}",
            base64_image=screenshot_b64,
            max_tokens=300
        )
        return response
    except Exception as e:
        print(f"[ERROR] Vision analysis failed: {e}")
        return f"I see your screen, but I couldn't analyze it due to an error: {e}"
