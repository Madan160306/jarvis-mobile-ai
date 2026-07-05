import urllib.parse
from engine.device.adb_helper import ADBHelper

PACKAGE_MAP = {
    "whatsapp":    ["com.whatsapp"],
    "instagram":   ["com.instagram.android"],
    "youtube":     ["com.google.android.youtube"],
    "youtube music": ["com.google.android.apps.youtube.music"],
    "yt music":    ["com.google.android.apps.youtube.music"],
    "chrome":      ["com.android.chrome"],
    "gmail":       ["com.google.android.gm"],
    "spotify":     ["com.spotify.music"],
    "maps":        ["com.google.android.apps.maps"],
    "camera":      ["com.sec.android.app.camera", "com.android.camera2", "com.android.camera"],
    "gallery":     ["com.sec.android.gallery3d", "com.google.android.apps.photos", "com.android.gallery3d"],
    "settings":    ["com.android.settings"],
    "phone":       ["com.samsung.android.dialer", "com.android.dialer", "com.android.phone"],
    "contacts":    ["com.samsung.android.app.contacts", "com.android.contacts"],
    "messages":    ["com.google.android.apps.messaging", "com.samsung.android.messaging", "com.android.mms"],
    "calculator":  ["com.sec.android.app.popupcalculator", "com.android.calculator2", "com.google.android.calculator"],
    "clock":       ["com.sec.android.app.clockpackage", "com.android.deskclock", "com.google.android.deskclock"],
    "facebook":    ["com.facebook.katana"],
    "twitter":     ["com.twitter.android"],
    "x":           ["com.twitter.android"],
    "snapchat":    ["com.snapchat.android"],
    "telegram":    ["org.telegram.messenger"],
    "netflix":     ["com.netflix.mediaclient"],
    "amazon":      ["in.amazon.mShop.android.shopping", "com.amazon.mShop.android.shopping"],
    "flipkart":    ["com.flipkart.android"],
    "phonepe":     ["com.phonepe.app"],
    "gpay":        ["com.google.android.apps.nbu.paisa.user"],
    "paytm":       ["net.one97.paytm"],
    "swiggy":      ["in.swiggy.android"],
    "zomato":      ["com.application.zomato"],
    "hotstar":     ["in.startv.hotstar"],
}

def open_app(app_name: str) -> bool:
    app_lower = app_name.lower().strip()
    packages = PACKAGE_MAP.get(app_lower)
    
    if not packages:
        import difflib
        matches = difflib.get_close_matches(app_lower, PACKAGE_MAP.keys(), n=1, cutoff=0.6)
        if matches:
            packages = PACKAGE_MAP[matches[0]]
            
    if packages:
        for pkg in packages:
            if pkg == "com.android.settings":
                ADBHelper.run_command(["shell", "am", "force-stop", "com.android.settings"])
                res = ADBHelper.run_command(["shell", "am", "start", "-a", "android.settings.SETTINGS"])
                if "error" not in res.lower():
                    return True
            else:
                res = ADBHelper.run_command(["shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])
                if "events injected" in res.lower() and "error running adb" not in res.lower():
                    return True
                
    # 2. DYNAMIC PACKAGE SEARCH for newly downloaded apps!
    # Query all installed packages directly from the phone
    res = ADBHelper.run_command(["shell", "pm", "list", "packages"])
    if "error running adb" in res.lower():
        return False
        
    packages = []
    for line in res.splitlines():
        if line.startswith("package:"):
            packages.append(line.replace("package:", "").strip())
            
    # Look for the app name in the package string (e.g., "discord" in "com.discord")
    app_no_spaces = app_lower.replace(" ", "")
    possible_packages = [pkg for pkg in packages if app_no_spaces in pkg.lower()]
    
    if possible_packages:
        # Sort by shortest package name to prioritize main apps over plugins/add-ons
        possible_packages.sort(key=len)
        for best_match in possible_packages:
            res = ADBHelper.run_command(["shell", "monkey", "-p", best_match, "-c", "android.intent.category.LAUNCHER", "1"])
            if "events injected" in res.lower() and "error running adb" not in res.lower():
                return True
        
    return False

def open_play_store(app_name: str):
    encoded = urllib.parse.quote(app_name)
    ADBHelper.run_command([
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", f"market://search?q={encoded}"
    ])
