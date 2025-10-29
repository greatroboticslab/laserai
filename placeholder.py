# placeholder.py
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import ttk

class PlaceholderFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)

        ttk.Label(self, text="Placeholder Feature", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky=W)

        blurb = (
            "This is a placeholder for my next tool.\n\n"
            "Use the 'Process Raw' tab to run the data converter."
        )
        ttk.Label(self, text=blurb, justify=LEFT).grid(row=1, column=0, sticky=W, pady=(8, 0))

        # Stretch nicely
        self.columnconfigure(0, weight=1)
