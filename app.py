# app.py
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from process_raw import ProcessRawFrame
from placeholder import PlaceholderFrame


def main():
    app = tb.Window(themename="flatly")
    app.title("Great Robotics Lab App")
    app.geometry("1800x580")

    header = ttk.Frame(app, padding=(12, 8))
    header.pack(side=tk.TOP, fill=tk.X)
    ttk.Label(header, text="Lazer App", font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT)

    nb = ttk.Notebook(app)
    nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    placeholder_tab = PlaceholderFrame(nb)
    process_tab = ProcessRawFrame(nb)

    nb.add(placeholder_tab, text="Placeholder (Default)")
    nb.add(process_tab, text="Process Raw")

    nb.select(placeholder_tab)
    app.mainloop()


if __name__ == "__main__":
    main()
