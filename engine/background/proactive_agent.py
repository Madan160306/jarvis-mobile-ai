import subprocess
import threading
import time
import datetime
import hashlib
class ProactiveAgent:
    def __init__(self):
        self.rules = [
            {
                "name": "low_battery",
                "check": self._check_battery,
                "threshold": 15,
                "message": "Hey Madan, battery is at {level} percent. Want me to turn on battery saver?",
                "cooldown": 3600  # alert once per hour max
            },
            {
                "name": "morning_briefing", 
                "check": self._is_morning,
                "time": "08:00",
                "message": "Good morning Madan! Ready to start the day?",
                "once_per_day": True,
                "has_run_today": False
            },
            {
                "name": "notification_watcher",
                "check": self._check_notifications,
                "cooldown": 5
            },
            {
                "name": "nightly_consolidation",
                "check": self._is_nightly_consolidation_time,
                "once_per_day": True,
                "has_run_today": False
            }
        ]
        self.last_run = {}
        self.seen_notifications = set()
    
    def _check_battery(self) -> int:
        try:
            result = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            for line in result.stdout.split('\n'):
                if 'level' in line:
                    return int(line.split(':')[1].strip())
        except Exception:
            pass
        return 100
        
    def _is_morning(self) -> bool:
        now = datetime.datetime.now()
        # Trigger between 8:00 and 8:05 AM
        if now.hour == 8 and now.minute < 5:
            return True
        return False

    def _is_nightly_consolidation_time(self) -> bool:
        now = datetime.datetime.now()
        # Trigger between 2:00 and 2:05 AM
        if now.hour == 2 and now.minute < 5:
            return True
        return False

    def _check_notifications(self):
        try:
            result = subprocess.run(['adb', 'shell', 'dumpsys', 'notification', '--noredact'], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=3)
            current_pkg = None
            title = None
            text = None
            lines = result.stdout.split('\n')
            
            for line in lines:
                if 'NotificationRecord{' in line:
                    try:
                        current_pkg = line.split(' pkg=')[1].split(' ')[0]
                        title = None
                        text = None
                    except:
                        pass
                if current_pkg in ['com.whatsapp', 'com.google.android.apps.messaging', 'org.telegram.messenger']:
                    if 'android.title=String (' in line:
                        title = line.split('android.title=String (')[1].split(')')[0]
                    elif 'android.text=String (' in line:
                        text = line.split('android.text=String (')[1].split(')')[0]
                        
                    if title and text:
                        notif_hash = hashlib.md5(f"{current_pkg}{title}{text}".encode()).hexdigest()
                        if notif_hash not in self.seen_notifications:
                            self.seen_notifications.add(notif_hash)
                            if "checking" in text.lower() or "running" in text.lower():
                                continue
                            return {"sender": title, "message": text}
        except:
            pass
        return None

    def _evaluate_rule(self, rule: dict):
        now = time.time()
        name = rule["name"]
        
        # Check cooldown
        if "cooldown" in rule:
            if now - self.last_run.get(name, 0) < rule["cooldown"]:
                return
                
        # Check once_per_day
        if rule.get("once_per_day"):
            current_date = datetime.datetime.now().date()
            if self.last_run.get(name) == current_date:
                return

        # Execute check
        if name == "low_battery":
            level = rule["check"]()
            if level <= rule["threshold"]:
                from engine.voice.tts_engine import TTSEngine
                TTSEngine.speak(rule["message"].format(level=level))
                self.last_run[name] = now
                
        elif name == "morning_briefing":
            if rule["check"]():
                from engine.voice.tts_engine import TTSEngine
                TTSEngine.speak(rule["message"])
                self.last_run[name] = datetime.datetime.now().date()
                
        elif name == "notification_watcher":
            msg_data = rule["check"]()
            if msg_data:
                from engine.ai.hybrid_llm import HybridLLM
                from engine.voice.tts_engine import TTSEngine
                prompt = f"A new message arrived from {msg_data['sender']}: {msg_data['message']}. Is this urgent or highly relevant? Reply 'YES' or 'NO', followed by a 1-sentence proactive alert starting with 'Madan, ' if YES."
                try:
                    res = HybridLLM.chat_completion([{"role": "user", "content": prompt}], max_tokens=100)
                    reply = res.choices[0].message.content.strip()
                    if reply.upper().startswith("YES"):
                        alert = reply[3:].strip()
                        if alert.startswith("-") or alert.startswith(":"):
                            alert = alert[1:].strip()
                        print(f"[ProactiveAgent] URGENT NOTIFICATION DETECTED: {alert}")
                        TTSEngine.speak(alert)
                    else:
                        print(f"[ProactiveAgent] Ignored non-urgent notification from {msg_data['sender']}")
                except Exception as e:
                    print(f"[ProactiveAgent] LLM failed to evaluate notification: {e}")
                    
        elif name == "nightly_consolidation":
            if rule["check"]():
                try:
                    from engine.memory.rag_engine import RAGEngine
                    print("[ProactiveAgent] Triggering Nightly Memory Consolidation...")
                    RAGEngine.get_instance()._run_consolidation()
                    self.last_run[name] = datetime.datetime.now().date()
                except Exception as e:
                    print(f"[ProactiveAgent] Nightly Consolidation failed: {e}")

    def start(self):
        print("[ProactiveAgent] Starting background thread...")
        thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )
        thread.start()
    
    def _run_loop(self):
        while True:
            for rule in self.rules:
                try:
                    self._evaluate_rule(rule)
                except Exception as e:
                    print(f"[ProactiveAgent] Error in rule {rule['name']}: {e}")
            time.sleep(15)  # check every 15 seconds
