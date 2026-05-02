import shutil
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from process_raw import ProcessRawFrame
from moku_waveform import MokuWaveformFrame
from display import DisplayFrame
from record_data import RecordDataFrame
from pid_autotune import AutotuneTab

import os
import sys
from pathlib import Path

def _get_base_dir() -> Path:
    #running from a PyInstaller .exe, files get unpacked to _MEIPASS
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    #default py run: use this file's directory
    return Path(__file__).resolve().parent

BASE_DIR = _get_base_dir()
MOKU_DATA_DIR = BASE_DIR / "moku_data"
# If you bundle mokucli.exe inside the app, add it to PATH for this process
MOKUCLI_DIR = BASE_DIR / "moku"
os.environ["PATH"] = str(MOKUCLI_DIR) + os.pathsep + os.environ.get("PATH", "")

os.environ["MOKU_DATA_PATH"] = str(MOKU_DATA_DIR)


def main():
    
    app = tb.Window(themename="flatly") 
    app.title("Laser Lab Control")
    app.geometry("1200x1000")
    try:
        #ttkbootstrap helper to center the window
        app.place_window_center()
    except Exception:
        pass

    app.resizable(True, True)

    style = tb.Style()
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))

    # Header bar
    header = tb.Frame(app, padding=(16, 12), bootstyle="dark")
    header.pack(side=tk.TOP, fill=tk.X)

    tb.Label(
        header,
        text="Laser / Moku Control",
        style="Title.TLabel",
        bootstyle="inverse"
    ).pack(side=tk.LEFT)

    # Notebook with modern style
    nb = tb.Notebook(app, bootstyle="primary")
    nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Check for mokucli once at startup so we can label the tab appropriately.
    has_mokucli = shutil.which("mokucli") is not None

    # Moku:Go waveform tab (will internally show setup or full UI)
    moku_tab = MokuWaveformFrame(nb, has_mokucli=has_mokucli)
    moku_tab_label = "Moku:Go Waveform" if has_mokucli else "Moku:Go Waveform (setup required)"
    nb.add(moku_tab, text=moku_tab_label)

    # for diplay
    display_tab = DisplayFrame(nb)       
    nb.add(display_tab, text="uMD GUI")  

    def on_close():
        try:
            display_tab.shutdown()
        except Exception:
            pass
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)

    # record data
    record_tab = RecordDataFrame(nb, moku_tab=moku_tab, display_tab=display_tab)
    nb.add(record_tab, text="Record Data")

    # Existing raw processing tab
    process_tab = ProcessRawFrame(nb)
    nb.add(process_tab, text="Process Raw")

    # PID autotune tab
    autotune_tab = AutotuneTab(nb, moku_tab=moku_tab, display_tab=display_tab)
    nb.add(autotune_tab, text="PID Autotune")

    # Start on Moku tab by default
    nb.select(moku_tab)

    app.mainloop()


if __name__ == "__main__":
    main()