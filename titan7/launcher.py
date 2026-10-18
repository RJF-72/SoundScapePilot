import os
import sys
import socket
import webbrowser
import winreg
import uvicorn

EXE_NAME = "SoundScapePilot.exe"
URL_MAP = {
    "dashboard": "home",
    "home": "home",
    "radio-autopilot": "radio",
    "booking-agent": "booking",
    "press-wire": "pr",
    "master-autopilot": "autopilot",
    "aegis-security": "security",
    "web-browser": "browser",
    "titan-meet": "meet",
    "ai-marketing": "marketing",
}

def register_protocol():
    try:
        root = winreg.HKEY_CURRENT_USER
        sub = r"Software\Classes\titan7"
        key = winreg.CreateKey(root, sub)
        winreg.SetValue(key, "", winreg.REG_SZ, "URL:SoundScape Pilot Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        winreg.CloseKey(key)

        cmd_key = winreg.CreateKey(root, sub + r"\shell\open\command")
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(sys.argv[0])
        winreg.SetValue(cmd_key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
        winreg.CloseKey(cmd_key)
        return True
    except:
        return False

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    module = "home"
    url_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("titan7://"):
            url_arg = arg
            path = arg.replace("titan7://", "").split("/")[0]
            module = URL_MAP.get(path, "home")
            break

    if not getattr(sys, 'frozen', False):
        register_protocol()

    for p in range(8765, 8775):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('0.0.0.0', p))
            s.close()
            port = p
            break
        except:
            s.close()
            continue

    webbrowser.open(f"http://127.0.0.1:{port}/?module={module}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")
