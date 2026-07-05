import subprocess

def torch_on():
    subprocess.run(['termux-torch', 'on'])

def torch_off():
    subprocess.run(['termux-torch', 'off'])

def send_sms(number, message):
    subprocess.run(['termux-sms-send', '-n', number, message])

def make_call(number):
    subprocess.run(['termux-telephony-call', number])

def get_battery():
    import json
    result = subprocess.run(['termux-battery-status'], capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        return f"Battery at {data.get('percentage', 'unknown')}%"
    except:
        return "Battery status unknown"

def read_notifications():
    result = subprocess.run(['termux-notification-list'], capture_output=True, text=True)
    return result.stdout

def send_whatsapp(contact, message):
    # termux-api deep link approach
    subprocess.run([
        'termux-open-url',
        f'whatsapp://send?phone={contact}&text={message}'
    ])

def speak(text):
    subprocess.run(['termux-tts-speak', text])

def vibrate():
    subprocess.run(['termux-vibrate', '-d', '500'])
