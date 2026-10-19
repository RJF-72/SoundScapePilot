import os
import sys

MEIPASS = getattr(sys, "_MEIPASS", None)
if MEIPASS:
    internal_dir = os.path.join(MEIPASS, "_internal")
    if os.path.isdir(internal_dir) and internal_dir not in sys.path:
        sys.path.insert(0, internal_dir)
    try:
        os.add_dll_directory(internal_dir)
    except Exception:
        pass
