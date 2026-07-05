"""
Phase 4 Test Suite — Parser validation only (no hardware).
Tests all Phase 4 commands plus the new mobile quick settings.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.core.command_parser import parse_command

TESTS = [
    # Productivity
    ("remind me to call Mom at 5 PM",               "productivity", "remind"),
    ("remind me to take medicine in 30 minutes",    "productivity", "remind"),
    ("what's my schedule",                           "productivity", "schedule"),
    ("what's the weather",                           "productivity", "weather"),
    ("weather in Mumbai",                            "productivity", "weather_city"),
    ("will it rain",                                 "productivity", "rain"),
    ("get forecast",                                 "productivity", "forecast"),
    ("read my emails",                               "productivity", "read_email"),
    # Media
    ("play jazz on youtube music",                   "media",        "ytmusic_play"),
    ("play lofi hip hop on yt music",                "media",        "ytmusic_play"),
    ("pause music",                                  "media",        "ytmusic_pause"),
    ("next song",                                    "media",        "ytmusic_next"),
    ("previous track",                               "media",        "ytmusic_prev"),
    ("sync volume to 70",                            "media",        "sync_volume_level"),
    ("sync volume",                                  "media",        "sync_volume"),
    # Mobile quick settings
    ("turn on airplane mode",                        "mobile",       "airplane_mode"),
    ("turn off airplane mode",                       "mobile",       "airplane_mode"),
    ("turn on bluetooth",                            "mobile",       "bluetooth"),
    ("turn off bluetooth",                           "mobile",       "bluetooth"),
    ("turn on torch",                                "mobile",       "torch"),
    ("turn off flashlight",                          "mobile",       "torch"),
    ("enable hotspot",                               "mobile",       "hotspot"),
    ("disable hotspot",                              "mobile",       "hotspot"),
    ("enable dnd",                                   "mobile",       "dnd"),
    ("turn off do not disturb",                      "mobile",       "dnd"),
    ("portrait",                                     "mobile",       "rotation"),
    ("landscape",                                    "mobile",       "rotation"),
    ("auto rotation",                                "mobile",       "rotation"),
    ("eye comfort on",                               "mobile",       "eye_comfort"),
    ("blue light off",                               "mobile",       "eye_comfort"),
    ("turn on nfc",                                  "mobile",       "nfc"),
    ("turn on wifi",                                 "mobile",       "wifi"),
    ("screen timeout 30",                            "mobile",       "screen_timeout"),
    ("take a screenshot",                            "mobile",       "screenshot"),
    ("mobile battery",                               "mobile",       "check_battery"),
    # Mobile misc
    ("lock the phone",                               "mobile",       "lock"),
    ("lock the pc",                                  "device",       "lock"),
    ("mobile open YouTube Music",                    "mobile",       "open_app"),
    ("open WhatsApp on my phone",                    "mobile",       "open_app"),
    ("attend the call",                              "mobile",       "attend_call"),
    ("reject the mobile call",                       "mobile",       "reject_call"),
    ('send whatsapp "Hello Boss" to 9876543210',     "mobile",       "whatsapp"),
    ("mobile volume up",                             "mobile",       "volume"),
    ("mobile brightness 75",                         "mobile",       "set_brightness"),
    # PC explicit
    ("increase the brightness",                      "device",       "increase_brightness"),
    ("make it louder",                               "device",       "increase_volume"),
    ("enable dark mode",                             "device",       "set_theme"),
    ("check disk usage",                             "device",       "check_disk"),
]

PASS = FAIL = 0

print("=" * 65)
print("  JK Phase 4 + Mobile Quick Settings — Parser Test Suite")
print("=" * 65)

for text, exp_intent, exp_action in TESTS:
    cmd = parse_command(text)
    ok  = cmd["intent"] == exp_intent and cmd["action"] == exp_action

    if ok:
        status = "[PASS]"
        PASS += 1
    else:
        status = "[FAIL]"
        FAIL += 1

    print(f"{status} | {text!r}")
    if not ok:
        print(f"        Expected: intent={exp_intent!r}, action={exp_action!r}")
        print(f"        Got:      intent={cmd['intent']!r}, action={cmd['action']!r}")

print("=" * 65)
print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
print("=" * 65)
