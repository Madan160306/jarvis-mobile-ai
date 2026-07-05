import subprocess
import os
import time

class ADBHelper:
    # Use the path found on the user's system as a primary location
    COMMON_PATHS = [
        r"C:\Users\msand\AppData\Local\Android\Sdk\platform-tools\adb.exe",
        "adb", # If it's in PATH
        r"C:\platform-tools\adb.exe"
    ]
    
    _adb_path = None

    @classmethod
    def get_adb_path(cls):
        if cls._adb_path:
            return cls._adb_path
            
        # Try 'where' command first
        try:
            res = subprocess.run(["where.exe", "adb"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if res.returncode == 0:
                cls._adb_path = res.stdout.splitlines()[0].strip()
                return cls._adb_path
        except:
            pass

        for path in cls.COMMON_PATHS:
            if os.path.exists(path):
                cls._adb_path = path
                return path
        return None

    @classmethod
    def connect_wifi(cls, ip, port=5555):
        return cls.run_command(["connect", f"{ip}:{port}"])

    @classmethod
    def run_command(cls, args, timeout=5):
        adb = cls.get_adb_path()
        if not adb:
            return "Error: ADB not found. Please install platform-tools."
            
        cmd = [adb] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            
            # Auto-Recovery mechanism for "no devices" or offline errors
            error_msg = res.stderr.strip() if res.stderr else (res.stdout.strip() if res.stdout else "")
            if res.returncode != 0 or "no devices/emulators found" in error_msg.lower() or "offline" in error_msg.lower():
                # Only auto-recover if we aren't already trying to kill/start the server to prevent infinite loops
                if "kill-server" not in args and "start-server" not in args:
                    print(f"[ADB] Connection error detected: {error_msg}. Initiating Auto-Recovery...")
                    subprocess.run([adb, "kill-server"], capture_output=True)
                    time.sleep(1)
                    subprocess.run([adb, "start-server"], capture_output=True)
                    time.sleep(2)
                    
                    # Retry original command
                    res_retry = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
                    if res_retry.returncode != 0:
                        retry_err = res_retry.stderr.strip() if res_retry.stderr else res_retry.stdout.strip()
                        return f"Error running ADB after recovery: {retry_err}"
                    return res_retry.stdout.strip()
                    
                return f"Error running ADB: {error_msg}"
                
            return res.stdout.strip()
        except subprocess.TimeoutExpired:
            return "Error: ADB command timed out. Device might be offline."
        except Exception as e:
            return f"Unexpected error: {e}"
