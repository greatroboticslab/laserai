import os, subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
exe_path = os.path.join(base_dir, "gui", "uMD_GUI.exe")

subprocess.Popen([exe_path])