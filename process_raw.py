# process_raw.py
import os
import re
import csv
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import ttkbootstrap as tb
from ttkbootstrap.constants import *

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# -----------------------------
# Platform helpers
# -----------------------------
def is_wsl() -> bool:
    try:
        rel = platform.release().lower()
        ver = platform.version().lower()
        return ("microsoft" in rel) or ("microsoft" in ver) or os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop")
    except Exception:
        return False


def win_to_wsl_path(win_path: str) -> str:
    
    m = re.match(r"^([A-Za-z]):\\(.*)$", win_path)
    if not m:
        return win_path
    drive = m.group(1).lower()
    rest = m.group(2).replace("\\", "/")
    return f"/mnt/{drive}/{rest}"


def wsl_to_win_path(wsl_path: str) -> str:
    
    m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", wsl_path)
    if not m:
        return wsl_path
    drive = m.group(1).upper()
    rest = m.group(2).replace("/", "\\")
    return f"{drive}:\\{rest}"


def select_folder_native(prompt: str) -> str:
    """
    Use a truly native folder picker:
      - WSL: Windows Forms dialog via powershell.exe, then convert to WSL path.
      - Windows/macOS/Linux: use platform-appropriate picker.
    """
    system = platform.system()
    if is_wsl():
        try:
            ps_cmd = [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                # Windows FolderBrowserDialog
                "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
                f"$fbd = New-Object System.Windows.Forms.FolderBrowserDialog;"
                f"$fbd.Description = '{prompt.replace('\"','\\\"')}';"
                "$fbd.ShowNewFolderButton = $true;"
                "if ($fbd.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {"
                "  Write-Output $fbd.SelectedPath"
                "} else { exit 1 }"
            ]
            result = subprocess.run(ps_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                win_path = result.stdout.strip()
                return win_to_wsl_path(win_path)
        except Exception:
            pass
        # Fallback to Tk dialog inside WSL if PowerShell fails
        return filedialog.askdirectory(title=prompt) or ""

    if system == "Windows":
        return filedialog.askdirectory(title=prompt) or ""
    elif system == "Darwin":
        return filedialog.askdirectory(title=prompt) or ""
    else:
        return filedialog.askdirectory(title=prompt) or ""


def open_folder_native(path: str):
    """Open a folder in the default OS file explorer."""
    try:
        if is_wsl():
            win = wsl_to_win_path(path)
            subprocess.Popen(["explorer.exe", win])
        else:
            system = platform.system()
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def get_downloads_dir() -> str:
    """
    Return the user's default Downloads folder for the current OS.
    - WSL: ask Windows for the real user profile via PowerShell, then convert to WSL path.
    - Windows: %USERPROFILE%\\Downloads
    - macOS: ~/Downloads
    - Linux: XDG_DOWNLOAD_DIR if defined in ~/.config/user-dirs.dirs, else ~/Downloads
    """
    if is_wsl():
        try:
            # Ask Windows for the true user profile (respects domain/profiles)
            ps = ["powershell.exe", "-NoProfile", "-Command", "[Environment]::GetFolderPath('UserProfile')"]
            r = subprocess.run(ps, capture_output=True, text=True)
            if r.returncode == 0:
                userprof = r.stdout.strip()
                return win_to_wsl_path(os.path.join(userprof, "Downloads"))
        except Exception:
            pass
        return os.path.expanduser("~/Downloads")

    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Downloads")
    elif system == "Darwin":
        return os.path.expanduser("~/Downloads")
    else:
        # Linux: honor XDG if present
        try:
            cfg = os.path.expanduser("~/.config/user-dirs.dirs")
            if os.path.isfile(cfg):
                with open(cfg, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("XDG_DOWNLOAD_DIR"):
                            # XDG_DOWNLOAD_DIR="$HOME/Downloads"
                            val = line.split("=", 1)[1].strip().strip('"')
                            val = val.replace("$HOME", os.path.expanduser("~"))
                            return val
        except Exception:
            pass
        return os.path.expanduser("~/Downloads")


# -----------------------------
# Core processing logic -hello
# -----------------------------
def raw_to_nm(D, wavelength=632.991372, phase=0.0, correction=0.0):
    return (D - phase) * (wavelength / 2.0) - correction


def is_valid_file(file_name: str) -> bool:
    return file_name.lower().endswith(".txt") and "readme" not in file_name.lower()


def process_text_files(input_folder, output_folder, mode="2", sample_freq=1000.0, zoom_points=600, status_cb=None):
    os.makedirs(output_folder, exist_ok=True)
    pattern = re.compile(r"D:(-?\d+(?:\.\d+)?)\s+N:(\d+)")
    sample_period_ms = 1000.0 / float(sample_freq)
    mode_str = "absolute" if mode == "1" else "relative"

    todo = []
    for root, _, files in os.walk(input_folder):
        for filename in files:
            if is_valid_file(filename):
                todo.append(os.path.join(root, filename))

    total = len(todo)
    if total == 0:
        raise RuntimeError("No .txt input files found under the selected folder.")

    for idx, filepath in enumerate(todo, start=1):
        rel_path = os.path.relpath(filepath, input_folder)
        rel_folder = os.path.dirname(rel_path)
        out_dir = os.path.join(output_folder, rel_folder)
        os.makedirs(out_dir, exist_ok=True)

        filename = os.path.basename(filepath)
        output_csv = os.path.join(out_dir, filename.replace(".txt", f"_{mode_str}.csv"))
        output_plot_all = os.path.join(out_dir, filename.replace(".txt", f"_{mode_str}_all.png"))
        output_plot_zoom = os.path.join(out_dir, filename.replace(".txt", f"_{mode_str}_zoom.png"))

        with open(filepath, "r") as f:
            lines = f.readlines()

        time_data, disp_data = [], []
        with open(output_csv, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Time_ms", f"{'Absolute' if mode == '1' else 'Delta'}_Displacement_nm"])

        # initialize baselines
            N_start, D_start = None, None
            for line in lines:
                m = pattern.search(line)
                if not m:
                    continue
                D_val = float(m.group(1))
                N_val = int(m.group(2))

                if N_start is None:
                    N_start = N_val
                if D_start is None:
                    D_start = D_val

                nm_value = raw_to_nm(D_val if mode == "1" else (D_val - D_start))
                time_ms = (N_val - N_start) * sample_period_ms

                writer.writerow([f"{time_ms:.3f}", f"{nm_value:.3f}"])
                time_data.append(time_ms)
                disp_data.append(nm_value)

        # Full plot
        plt.figure(figsize=(10, 5))
        plt.plot(time_data, disp_data, linewidth=0.7)
        plt.xlabel("Time (ms)")
        plt.ylabel("Displacement (nm)")
        plt.title(f"{filename} ({mode_str}) - All Data")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(output_plot_all, dpi=150)
        plt.close()

        # Zoom plot
        zoom_n = min(int(zoom_points), len(time_data))
        plt.figure(figsize=(10, 5))
        plt.plot(time_data[:zoom_n], disp_data[:zoom_n], marker="o")
        plt.xlabel("Time (ms)")
        plt.ylabel("Displacement (nm)")
        plt.title(f"{filename} ({mode_str}) - First {zoom_n} Points")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(output_plot_zoom, dpi=150)
        plt.close()

        if status_cb:
            status_cb(idx, total, f"Processed: {rel_path}")


# --------------------------------
# GUI Frame
# --------------------------------
class ProcessRawFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.input_folder = tk.StringVar()
        self.mode = tk.StringVar(value="2")   # 1=absolute, 2=relative
        self.sample_freq = tk.DoubleVar(value=1000.0)
        self.zoom_points = tk.IntVar(value=2400)

        self.run_btn = None
        self.pb = None
        self.status = None

        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Process Raw Data", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=6, sticky="w")

        ttk.Label(self, text="Input folder:").grid(row=1, column=0, sticky="e", pady=(10, 0))
        ttk.Entry(self, textvariable=self.input_folder, width=70).grid(row=1, column=1, columnspan=4, sticky="ew", pady=(10, 0))
        ttk.Button(self, text="Browse...", command=self._pick_input).grid(row=1, column=5, sticky="w", pady=(10, 0))

        row = 2
        ttk.Label(self, text="Mode:").grid(row=row, column=0, sticky="e", pady=(8, 0))
        ttk.Radiobutton(self, text="Absolute", value="1", variable=self.mode).grid(row=row, column=1, sticky="w", pady=(8, 0))
        ttk.Radiobutton(self, text="Relative (baseline)", value="2", variable=self.mode).grid(row=row, column=2, sticky="w", pady=(8, 0))

        ttk.Label(self, text="Sample freq (Hz):").grid(row=row, column=3, sticky="e", pady=(8, 0))
        ttk.Entry(self, textvariable=self.sample_freq, width=10).grid(row=row, column=4, sticky="w", pady=(8, 0))

        row += 1
        ttk.Label(self, text="Zoom points:").grid(row=row, column=0, sticky="e", pady=(6, 0))
        ttk.Entry(self, textvariable=self.zoom_points, width=10).grid(row=row, column=1, sticky="w", pady=(6, 0))

        row += 1
        self.run_btn = ttk.Button(self, text="Run", bootstyle=SUCCESS, command=self._run)
        self.run_btn.grid(row=row, column=0, sticky="w", pady=(12, 0))

        self.pb = ttk.Progressbar(self, mode="determinate")
        self.pb.grid(row=row, column=1, columnspan=4, sticky="ew", padx=(8, 0), pady=(12, 0))
        self.status = ttk.Label(self, text="Idle")
        self.status.grid(row=row, column=5, sticky="e", pady=(12, 0))

        for c in range(6):
            self.columnconfigure(c, weight=1)

    def _pick_input(self):
        path = select_folder_native("Select input folder with .txt files")
        if not path:
            return
        self.input_folder.set(path)

    def _run(self):
        in_dir = self.input_folder.get().strip()
        if not in_dir:
            messagebox.showwarning("Input Required", "Please select the input folder.")
            return

        # Always write into the OS Downloads folder
        downloads = get_downloads_dir()
        base = os.path.basename(os.path.normpath(in_dir))
        out_dir = os.path.join(downloads, f"output_{base}")

        self.run_btn.config(state="disabled")
        self.status.config(text="Starting...")
        self.pb.config(value=0)

        def worker():
            try:
                progress_inited = False

                def status_cb(done, total, text):
                    nonlocal progress_inited
                    if not progress_inited:
                        self.pb.config(maximum=total)
                        progress_inited = True
                    self.pb.config(value=done)
                    self.status.config(text=f"{text}  ({done}/{total})")

                process_text_files(
                    input_folder=in_dir,
                    output_folder=out_dir,
                    mode=self.mode.get(),
                    sample_freq=float(self.sample_freq.get()),
                    zoom_points=int(self.zoom_points.get()),
                    status_cb=status_cb
                )
                self.status.config(text=f"Done → {out_dir}")
                open_folder_native(out_dir)
                messagebox.showinfo("Processing Complete", f"Output saved to:\n{out_dir}")
            except Exception as e:
                self.status.config(text="Error")
                messagebox.showerror("Error", str(e))
            finally:
                self.run_btn.config(state="normal")

        threading.Thread(target=worker, daemon=True).start()
