"""
YTMusicController: YouTube Music control for both mobile (ADB) and PC (browser).
- Mobile: Launches YT Music with a search URL via ADB intent.
- PC: Opens YouTube Music search in the default browser.
- Media key control (play/pause, next, prev) on mobile via ADB keycodes.
"""
import urllib.parse
import webbrowser

from engine.device.adb_helper import ADBHelper

YT_MUSIC_PACKAGE = "com.google.android.apps.youtube.music"


class YTMusicController:

    @classmethod
    def play(cls, query: str, device: str = "mobile") -> str:
        """Search and play on YouTube Music. Defaults to mobile."""
        if device == "pc":
            return cls._play_pc(query)
        return cls._play_mobile(query)

    @classmethod
    def _play_mobile(cls, query: str) -> str:
        # Visual automation flow requested by user
        from engine.device.android_controller import AndroidController
        from engine.device import screen_reader
        
        # 1. Open app using the new visual search workflow
        AndroidController.open_app("youtube music")
        screen_reader.wait(3.0)
        
        # 2. Tap search visually
        if not AndroidController._tap_with_retry(content_desc="Search"):
            return "I couldn't visually locate the search icon in YT Music."
            
        screen_reader.wait(1.5)
        screen_reader.type_text(query)
        screen_reader.press_enter()
        screen_reader.wait(4.0)
        
        # 3. Tap the first result visually (approximate)
        from engine.device.adb_helper import ADBHelper
        ADBHelper.run_command(["shell", "input", "tap", "500", "500"])
            
        return f"Searching and playing '{query}' on YouTube Music."

    @classmethod
    def _play_pc(cls, query: str) -> str:
        encoded = urllib.parse.quote(query)
        url = f"https://music.youtube.com/search?q={encoded}"
        webbrowser.open(url)
        return f"Opening YouTube Music on PC for: '{query}'"

    @classmethod
    def toggle_play_pause(cls) -> str:
        """Toggle play/pause on mobile using media keyevent."""
        ADBHelper.run_command(["shell", "input", "keyevent", "85"])
        return "Toggled play/pause on mobile."

    @classmethod
    def next_track(cls) -> str:
        ADBHelper.run_command(["shell", "input", "keyevent", "87"])
        return "Skipped to next track on mobile."

    @classmethod
    def prev_track(cls) -> str:
        ADBHelper.run_command(["shell", "input", "keyevent", "88"])
        return "Went back to previous track on mobile."

    @classmethod
    def stop(cls) -> str:
        ADBHelper.run_command(["shell", "input", "keyevent", "86"])
        return "Stopped media on mobile."
