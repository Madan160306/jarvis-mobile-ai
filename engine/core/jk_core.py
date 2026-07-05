from engine.voice.hybrid_asr import HybridVoiceEngine
from engine.security.security import validate
from engine.voice.tts_engine import speak
from engine.voice.voice_auth import VoiceAuthenticator
import sys
import os

def run():
    import subprocess
    if os.path.exists('/data/data/com.termux'):
        MOBILE_MODE = True
        try:
            subprocess.Popen(['termux-wake-lock'])
            print("[JARVIS] Termux Wake lock acquired")
        except:
            pass
    else:
        MOBILE_MODE = False

    from engine.core.agent import Agent
    agent = Agent()
    from engine.voice.audio_pipeline import AudioPipeline
    pipeline = AudioPipeline()

    from engine.background.proactive_agent import ProactiveAgent
    proactive = ProactiveAgent()
    proactive.start()

    auth_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "owner_voice.npy")
    auth = VoiceAuthenticator(auth_path)
    if os.path.exists(auth_path):
        speak("Verifying user identity. Please speak your passphrase.")
        if not auth.authenticate():
            speak("Voice authentication failed. Access denied.")
            sys.exit(1)
        speak("Identity confirmed.")
    else:
        speak("No voice profile found. Let's enroll you now. Please speak for 3 seconds.")
        auth.enroll_owner()
        speak("Enrollment complete. Welcome, boss.")

    speak("JK online. All systems operational.", lang="en")

    # Restore any reminders that survived a previous session
    from engine.productivity.reminder_manager import ReminderManager
    ReminderManager.restore_pending()

    import time
    import random
    import re

    try:
        for text, lang in pipeline.listen_continuously():
            if not text.strip():
                continue
                
            print(f"You ({lang}):", text)

            if "daddy's gonna miss u" in text.lower():
                speak("Kill phrase detected. Shutting down JK.")
                break
                
            # Agentic Loop
            response = agent.process(text, lang)
            if response:
                from engine.voice.hybrid_asr import InterruptibleSpeaker
                was_interrupted = InterruptibleSpeaker.speak_interruptible(response)
                if was_interrupted:
                    print("[JK] Speaking interrupted by user.")
                    continue

    except KeyboardInterrupt:
        print("\nJK shutting down.")
        speak("Goodbye.")
        sys.exit(0)
    except Exception as e:
        print(f"[Error] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
