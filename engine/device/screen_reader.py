import os
import re
import time
import cv2
import xml.etree.ElementTree as ET
from engine.device.adb_helper import ADBHelper

def wait(seconds: float):
    time.sleep(seconds)

def get_screen_xml():
    """Dump current UI to XML and return the parsed XML tree root."""
    ADBHelper.run_command(["shell", "uiautomator", "dump", "/sdcard/ui.xml"])
    ADBHelper.run_command(["pull", "/sdcard/ui.xml", "temp_ui.xml"])
    
    if not os.path.exists("temp_ui.xml"):
        return None
        
    with open("temp_ui.xml", "r", encoding="utf-8") as f:
        xml_content = f.read()
        
    try:
        os.remove("temp_ui.xml")
    except:
        pass
        
    try:
        return ET.fromstring(xml_content)
    except Exception as e:
        print(f"[ScreenReader] XML Parse Error: {e}")
        return None

def find_element(root=None, text=None, resource_id=None, content_desc=None, class_name=None):
    """Search XML for matching element and return center coordinates (x, y)."""
    if root is None:
        root = get_screen_xml()
        if root is None:
            return None

    for node in root.iter('node'):
        node_res = node.get('resource-id', '')
        node_desc = node.get('content-desc', '')
        node_text = node.get('text', '')
        node_class = node.get('class', '')
        
        match = True
        if text and text.lower() not in node_text.lower():
            match = False
        if resource_id and resource_id not in node_res:
            match = False
        if content_desc and content_desc.lower() not in node_desc.lower():
            match = False
        if class_name and class_name not in node_class:
            match = False
            
        if match and (text or resource_id or content_desc or class_name):
            bounds = node.get('bounds')
            if bounds:
                m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    return (cx, cy)
    return None

def find_elements(root=None, text=None, resource_id=None, content_desc=None, class_name=None):
    """Search XML for matching elements and return list of center coordinates (x, y) and their properties."""
    if root is None:
        root = get_screen_xml()
        if root is None:
            return []

    results = []
    for node in root.iter('node'):
        node_res = node.get('resource-id', '')
        node_desc = node.get('content-desc', '')
        node_text = node.get('text', '')
        node_class = node.get('class', '')
        
        match = True
        if text and text.lower() not in node_text.lower():
            match = False
        if resource_id and resource_id not in node_res:
            match = False
        if content_desc and content_desc.lower() not in node_desc.lower():
            match = False
        if class_name and class_name not in node_class:
            match = False
            
        if match and (text or resource_id or content_desc or class_name):
            bounds = node.get('bounds')
            if bounds:
                m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    results.append({
                        "x": cx, "y": cy, 
                        "text": node_text, 
                        "desc": node_desc
                    })
    return results

def tap(x: int, y: int):
    ADBHelper.run_command(["shell", "input", "tap", str(x), str(y)])

def tap_element(text=None, resource_id=None, content_desc=None, class_name=None, root=None):
    coords = find_element(root=root, text=text, resource_id=resource_id, content_desc=content_desc, class_name=class_name)
    if coords:
        tap(coords[0], coords[1])
        return True
    return False

def type_text(text: str):
    formatted = text.replace(" ", "%s").replace("'", "")
    ADBHelper.run_command(["shell", "input", "text", formatted])

def swipe_up():
    ADBHelper.run_command(["shell", "input", "swipe", "500", "1500", "500", "500", "300"])

def swipe_down():
    ADBHelper.run_command(["shell", "input", "swipe", "500", "500", "500", "1500", "300"])

def press_back():
    ADBHelper.run_command(["shell", "input", "keyevent", "4"])

def press_home():
    ADBHelper.run_command(["shell", "input", "keyevent", "3"])

def press_enter():
    ADBHelper.run_command(["shell", "input", "keyevent", "66"])

def get_screenshot():
    ADBHelper.run_command(["shell", "screencap", "/sdcard/screen.png"])
    ADBHelper.run_command(["pull", "/sdcard/screen.png", "temp_screen.png"])
    if os.path.exists("temp_screen.png"):
        img = cv2.imread("temp_screen.png")
        try:
            os.remove("temp_screen.png")
        except:
            pass
        return img
    return None

def get_simplified_ui_elements():
    """Returns a simplified, numbered list of clickable/interactive elements for LLM processing."""
    root = get_screen_xml()
    if root is None:
        return []
        
    elements = []
    element_id = 1
    
    for node in root.iter('node'):
        is_clickable = node.get('clickable') == 'true'
        node_text = node.get('text', '').strip()
        node_desc = node.get('content-desc', '').strip()
        
        # Only include nodes that have some identifying text/desc OR are clickable
        if (is_clickable or node_text or node_desc):
            if not node_text and not node_desc and not is_clickable:
                continue
                
            bounds = node.get('bounds')
            if bounds:
                m = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    
                    # Skip tiny or zero-size elements
                    if (x2 - x1) < 5 or (y2 - y1) < 5:
                        continue
                        
                    el_data = {
                        "id": element_id,
                        "text": node_text,
                        "desc": node_desc,
                        "class": node.get('class', '').split('.')[-1],
                        "clickable": is_clickable,
                        "center_x": cx,
                        "center_y": cy
                    }
                    elements.append(el_data)
                    element_id += 1
                    
    return elements
