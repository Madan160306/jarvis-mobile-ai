import os
import sys
import io

# Force UTF-8 on Windows stdout/stderr to prevent UnicodeEncodeError
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', write_through=True)
    except Exception:
        pass
if sys.stderr and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', write_through=True)
    except Exception:
        pass

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server.fastmcp import FastMCP
from engine.ai.ui_agent import UIAgent
from engine.device.android_controller import AndroidController

mcp = FastMCP("JK-Mobile-Agent")

@mcp.tool()
def analyze_screen() -> str:
    """Analyzes the current Android screen and returns a JSON list of interactable UI elements with IDs."""
    return UIAgent.analyze_screen()

@mcp.tool()
def tap_element(element_id: int) -> str:
    """Taps a specific UI element based on its numeric ID returned by analyze_screen()."""
    return UIAgent.tap_element(element_id)

@mcp.tool()
def swipe_screen(direction: str) -> str:
    """Swipes the screen in the given direction to scroll. Direction must be 'up', 'down', 'left', or 'right'."""
    return AndroidController.swipe_screen({"direction": direction})

@mcp.tool()
def type_text(text: str) -> str:
    """Types text into the currently focused input box on the phone."""
    return AndroidController.type_text({"text": text})

@mcp.tool()
def press_button(button: str) -> str:
    """Presses a hardware button. Button must be 'home', 'back', 'recent', 'enter', or 'power'."""
    return AndroidController.press_button({"button": button})

@mcp.tool()
def execute_adb_command(command: str) -> str:
    """Executes a raw ADB command. Command must start with 'shell' (e.g. 'shell dumpsys battery')."""
    from engine.device.adb_helper import ADBHelper
    res = ADBHelper.run_command(command.split(" "))
    return str(res)

@mcp.tool()
def swipe_coordinates(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    """Executes a precise coordinate-based swipe. Use this to pull down the status bar (e.g. 540, 0, 540, 1500) or scroll the screen."""
    return AndroidController.swipe_coordinates(start_x, start_y, end_x, end_y)

if __name__ == "__main__":
    # Standard fastmcp run will expose it via stdio
    mcp.run()
