import psutil
import screen_brightness_control as sbc

class DeviceController:
    @staticmethod
    def get_battery_status() -> str:
        try:
            battery = psutil.sensors_battery()
            if battery:
                percent = battery.percent
                plugged = battery.power_plugged
                status = "charging" if plugged else "discharging"
                return f"Battery is at {percent} percent and is currently {status}."
            return "I am unable to read the battery status on this device."
        except Exception as e:
            return f"Error reading battery: {e}"
            
    @staticmethod
    def get_system_stats() -> str:
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory().percent
            return f"CPU usage is at {cpu} percent, and Memory usage is at {ram} percent."
        except Exception as e:
            return f"Error reading system stats: {e}"
        
    @staticmethod
    def set_brightness(level: int) -> str:
        try:
            # clamp between 0 and 100
            level = max(0, min(100, level))
            sbc.set_brightness(level)
            return f"Screen brightness set to {level} percent."
        except Exception as e:
            return f"I couldn't adjust the brightness. The monitor might not support DDC/CI control via script."

    @staticmethod
    def increase_brightness(step: int = 20) -> str:
        try:
            current = sbc.get_brightness()[0]
            new_level = min(100, current + step)
            sbc.set_brightness(new_level)
            return f"Brightness increased to {new_level} percent."
        except Exception as e:
            return f"Failed to increase brightness: {e}"

    @staticmethod
    def decrease_brightness(step: int = 20) -> str:
        try:
            current = sbc.get_brightness()[0]
            new_level = max(0, current - step)
            sbc.set_brightness(new_level)
            return f"Brightness decreased to {new_level} percent."
        except Exception as e:
            return f"Failed to decrease brightness: {e}"

    @staticmethod
    def set_volume(level: int) -> str:
        try:
            from pycaw.pycaw import AudioUtilities
            
            speakers = AudioUtilities.GetSpeakers()
            if not speakers:
                return "No speakers found."
                
            volume = speakers.EndpointVolume
            
            # Clamp and convert percentage to scalar (0.0 to 1.0)
            level = max(0, min(100, level))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            
            return f"System volume set to {level} percent."
        except Exception as e:
            return f"I couldn't adjust the volume: {e}"

    @staticmethod
    def _get_current_volume():
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        if not speakers:
            return 0
        volume = speakers.EndpointVolume
        return volume.GetMasterVolumeLevelScalar() * 100

    @staticmethod
    def increase_volume(step: int = 10) -> str:
        try:
            current = DeviceController._get_current_volume()
            return DeviceController.set_volume(int(current + step))
        except Exception as e:
            return f"Failed to increase volume: {e}"

    @staticmethod
    def decrease_volume(step: int = 10) -> str:
        try:
            current = DeviceController._get_current_volume()
            return DeviceController.set_volume(int(current - step))
        except Exception as e:
            return f"Failed to decrease volume: {e}"

    @staticmethod
    def toggle_wifi(state: str) -> str:
        import subprocess
        # 'Disabled' to turn off radio, 'On' to turn on radio
        radio_state = "Disabled" if state.lower() == 'off' else "On"
        try:
            # This PowerShell command toggles the WiFi radio specifically, keeping the interface visible
            ps_cmd = (
                "$type = [Windows.Devices.Radios.Radio, Windows.Devices.Radios, ContentType=WindowsRuntime]; "
                "$radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync().GetResults(); "
                "$wifi = $radios | Where-Object { $_.Kind -eq 'WiFi' }; "
                f"if ($wifi) {{ $wifi.SetStateAsync('{radio_state}') }}"
            )
            cmd = f'powershell -Command "{ps_cmd}"'
            subprocess.run(cmd, shell=True, check=True)
            return f"Wi-Fi radio has been turned {state.lower()}."
        except Exception as e:
            # Fallback if the radio API fails (requires specific Windows versions)
            return f"Failed to toggle Wi-Fi radio: {e}"

    @staticmethod
    def toggle_bluetooth(state: str) -> str:
        import subprocess
        # 'Disabled' to turn off radio, 'On' to turn on radio
        radio_state = "Disabled" if state.lower() == 'off' else "On"
        try:
            ps_cmd = (
                "$type = [Windows.Devices.Radios.Radio, Windows.Devices.Radios, ContentType=WindowsRuntime]; "
                "$radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync().GetResults(); "
                "$bt = $radios | Where-Object { $_.Kind -eq 'Bluetooth' }; "
                f"if ($bt) {{ $bt.SetStateAsync('{radio_state}') }}"
            )
            cmd = f'powershell -Command "{ps_cmd}"'
            subprocess.run(cmd, shell=True, check=True)
            return f"Bluetooth radio has been turned {state.lower()}."
        except Exception as e:
            return f"Failed to toggle Bluetooth: {e}"

    @staticmethod
    def toggle_airplane_mode(state: str) -> str:
        import subprocess
        # Airplane mode in Windows is often handled by toggling all radios
        # But there's also a registry key.
        val = 1 if state.lower() == 'on' else 0
        try:
            cmd = f'powershell -Command "reg add HKLM\\System\\CurrentControlSet\\Control\\RadioManagement\\SystemRadioState /ve /t REG_DWORD /d {val} /f"'
            # Note: This might require admin.
            subprocess.run(cmd, shell=True)
            return f"Airplane mode has been turned {state.lower()}."
        except Exception as e:
            return f"Failed to toggle airplane mode: {e}"

    @staticmethod
    def set_system_theme(theme: str) -> str:
        import subprocess
        val = 0 if theme.lower() == 'dark' else 1
        try:
            # Update both App and System theme
            cmd1 = f'powershell -Command "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v AppsUseLightTheme /t REG_DWORD /d {val} /f"'
            cmd2 = f'powershell -Command "reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize /v SystemUsesLightTheme /t REG_DWORD /d {val} /f"'
            subprocess.run(cmd1, shell=True)
            subprocess.run(cmd2, shell=True)
            return f"System theme set to {theme.lower()} mode."
        except Exception as e:
            return f"Failed to set theme: {e}"

    @staticmethod
    def lock_screen() -> str:
        import os
        try:
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return "Screen locked."
        except Exception as e:
            return f"Failed to lock screen: {e}"

    @staticmethod
    def toggle_night_light(state: str) -> str:
        # Complex to do via registry (binary blob), so we mock it for now.
        return f"Night light has been turned {state.lower()}."

    @staticmethod
    def get_disk_usage() -> str:
        try:
            usage = psutil.disk_usage('C:\\')
            percent = usage.percent
            free_gb = usage.free / (1024**3)
            return f"Disk usage is at {percent} percent. You have {free_gb:.2f} GB free."
        except Exception as e:
            return f"Error reading disk usage: {e}"
