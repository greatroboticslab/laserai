import shutil
import tkinter as tk
from tkinter import ttk

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from process_raw import ProcessRawFrame
from moku_waveform import MokuWaveformFrame
from display import DisplayFrame
from record_data import RecordDataFrame
from pid_control import PIDControlFrame          # ← NEW

import os
import sys
from pathlib import Path

def _get_base_dir() -> Path:
    # Running from a PyInstaller .exe: files unpacked to _MEIPASS
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # Normal run: use this file's directory
    return Path(__file__).resolve().parent

BASE_DIR      = _get_base_dir()
MOKU_DATA_DIR = BASE_DIR / "moku_data"
os.environ["MOKU_DATA_PATH"] = str(MOKU_DATA_DIR)


""" For Developer purposes -- This creates an executionable program
pyinstaller --onefile ^
  --add-data "moku_data;moku_data" ^
  app.py
"""


def main():

    app = tb.Window(themename="flatly")
    app.title("Laser Lab Control")
    app.geometry("1200x1000")
    try:
        app.place_window_center()
    except Exception:
        pass

    app.resizable(True, True)

    style = tb.Style()
    style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))

    # ── Header bar ───────────────────────────────────────────────────
    header = tb.Frame(app, padding=(16, 12), bootstyle="dark")
    header.pack(side=tk.TOP, fill=tk.X)

    tb.Label(
        header,
        text="Laser / Moku Control",
        style="Title.TLabel",
        bootstyle="inverse"
    ).pack(side=tk.LEFT)

    # ── Notebook ──────────────────────────────────────────────────────
    nb = tb.Notebook(app, bootstyle="primary")
    nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    has_mokucli = shutil.which("mokucli") is not None

    # ── Tab 1: Moku:Go Waveform Generator ─────────────────────────────
    moku_tab = MokuWaveformFrame(nb, has_mokucli=has_mokucli)
    moku_tab_label = (
        "Moku:Go Waveform"
        if has_mokucli
        else "Moku:Go Waveform (setup required)"
    )
    nb.add(moku_tab, text=moku_tab_label)

    # ── Tab 2: uMD GUI Display ─────────────────────────────────────────
    display_tab = DisplayFrame(nb)
    nb.add(display_tab, text="uMD GUI")

    # ── Tab 3: Record Data ─────────────────────────────────────────────
    record_tab = RecordDataFrame(nb, moku_tab=moku_tab, display_tab=display_tab)
    nb.add(record_tab, text="Record Data")

    # ── Tab 4: PID Closed-Loop Control  (NEW) ─────────────────────────
    pid_tab = PIDControlFrame(nb, moku_tab=moku_tab)
    nb.add(pid_tab, text="PID Closed-Loop")

    # ── Tab 5: Process Raw ─────────────────────────────────────────────
    process_tab = ProcessRawFrame(nb)
    nb.add(process_tab, text="Process Raw")

    # Start on Moku tab
    nb.select(moku_tab)

    app.mainloop()


if __name__ == "__main__":
    main()
