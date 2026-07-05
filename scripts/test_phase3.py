import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core.executor import execute
from engine.core.command_parser import parse_command

def test_command(text):
    print(f"\n[TESTING]: {text}")
    cmd = parse_command(text)
    print(f"[PARSED]: {cmd}")
    # We mock execute a bit to avoid actual hardware changes during test if needed,
    # but here we'll just run it and see the output/logs.
    execute(cmd)

if __name__ == "__main__":
    print("--- JK Phase 3 Test Suite ---")
    
    commands = [
        "increase the brightness",
        "make it louder",
        "turn on airplane mode",
        "lock the pc",
        "lock the phone",
        "mobile brightness 50",
        "mobile volume up",
        "attend the call",
        "reject the mobile call",
        "read mobile notifications",
        "send whatsapp \"Hello from JK\" to 9876543210",
        "turn on airplane mode",
        "enable dark mode",
        "check disk usage"
    ]
    
    for cmd in commands:
        try:
            test_command(cmd)
        except Exception as e:
            print(f"[ERROR]: {e}")
            
    print("\n--- Test Suite Complete ---")
