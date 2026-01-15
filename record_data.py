# record_data.py
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from process_raw import get_downloads_dir, select_folder_native, open_folder_native


class RecordDataFrame(ttk.Frame):
    def __init__(self, parent, moku_tab, display_tab):
        super().__init__(parent, padding=16)
        self.moku_tab = moku_tab
        self.display_tab = display_tab

        # UI vars
        self.base_folder = tk.StringVar(value=get_downloads_dir())
        self.folder_name = tk.StringVar(value="umd_logs")
        self.test_duration = tk.DoubleVar(value=15.0)

        self.freq_start = tk.IntVar(value=1)
        self.freq_end = tk.IntVar(value=10)

        self.vpp = tk.DoubleVar(value=5.0)
        self.sample_freq = tk.IntVar(value=1000)

        self.status = tk.StringVar(value="Status: idle")

        # Worker control
        self._stop_flag = threading.Event()
        self._worker = None

        # Progress modal state
        self._progress_win = None
        self._progress_bar = None
        self._progress_label = None
        self._progress_sub = None
        self._progress_eta = None
        self._progress_btn_stop = None

        # Progress bookkeeping (shared between threads, updated carefully)
        self._run_started_at = None
        self._total_seconds = None
        self._current_file = ""
        self._current_freq = None
        self._freq_index = 0
        self._freq_total = 0
        self._freq_started_at = None

        self._build_ui()
        self._start_condition_monitor()

    # ---------- UI ----------
    def _build_ui(self):
        ttk.Label(self, text="Record Data", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")

        # Save folder
        ttk.Label(self, text="Save to folder:").grid(row=1, column=0, sticky="e", pady=(10, 0))
        ttk.Entry(self, textvariable=self.base_folder, width=60).grid(row=1, column=1, sticky="ew", pady=(10, 0))
        ttk.Button(self, text="Change...", command=self._pick_folder).grid(row=1, column=2, padx=(8, 0), pady=(10, 0))

        ttk.Label(self, text="Subfolder name:").grid(row=2, column=0, sticky="e", pady=(6, 0))
        ttk.Entry(self, textvariable=self.folder_name, width=25).grid(row=2, column=1, sticky="w", pady=(6, 0))

        # Test params
        ttk.Label(self, text="Seconds per frequency:").grid(row=3, column=0, sticky="e", pady=(10, 0))
        ttk.Entry(self, textvariable=self.test_duration, width=10).grid(row=3, column=1, sticky="w", pady=(10, 0))

        ttk.Label(self, text="Frequency range (Hz):").grid(row=4, column=0, sticky="e", pady=(6, 0))
        r = ttk.Frame(self)
        r.grid(row=4, column=1, sticky="w", pady=(6, 0))
        ttk.Entry(r, textvariable=self.freq_start, width=6).pack(side="left")
        ttk.Label(r, text=" to ").pack(side="left")
        ttk.Entry(r, textvariable=self.freq_end, width=6).pack(side="left")

        ttk.Label(self, text="Vpp (default 5):").grid(row=5, column=0, sticky="e", pady=(6, 0))
        ttk.Entry(self, textvariable=self.vpp, width=10).grid(row=5, column=1, sticky="w", pady=(6, 0))

        ttk.Label(self, text="Sample Frequency (Hz):").grid(row=6, column=0, sticky="e", pady=(6, 0))
        ttk.Entry(self, textvariable=self.sample_freq, width=10).grid(row=6, column=1, sticky="w", pady=(6, 0))

        # Only Start button on the tab
        btns = ttk.Frame(self)
        btns.grid(row=7, column=0, columnspan=3, sticky="w", pady=(14, 0))
        self.start_btn = ttk.Button(btns, text="Start Recording", command=self.start_recording)
        self.start_btn.pack(side="left")

        ttk.Label(self, textvariable=self.status).grid(row=8, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.columnconfigure(1, weight=1)

    def _pick_folder(self):
        p = select_folder_native("Select output folder")
        if p:
            self.base_folder.set(p)

    # ---------- Conditions ----------
    def _conditions_ok(self) -> bool:
        # 1) Moku connected
        if not getattr(self.moku_tab, "is_connected", lambda: False)():
            return False
        # 2) MQTT connected/listening (approx via "received at least one payload")
        if not getattr(self.display_tab, "is_mqtt_connected", lambda: False)():
            return False
        # 3) uMD GUI opened AND data is streaming into uMD tab
        if not getattr(self.display_tab, "is_umd_running", lambda: False)():
            return False
        if not getattr(self.display_tab, "is_streaming", lambda: False)():
            return False
        return True

    def _start_condition_monitor(self):
        ok = self._conditions_ok()
        self.start_btn.config(state=("normal" if ok else "disabled"))
        if ok:
            self.status.set("Status: ready (all conditions met)")
        else:
            self.status.set("Status: waiting (connect Moku, open uMD GUI, ensure MQTT data is streaming)")
        self.after(300, self._start_condition_monitor)

    # ---------- Recording lifecycle ----------
    def start_recording(self):
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Already running", "Recording is already in progress.")
            return
        if not self._conditions_ok():
            messagebox.showerror("Not ready", "Conditions not met yet.")
            return

        # Validate inputs quickly
        try:
            f0 = int(self.freq_start.get())
            f1 = int(self.freq_end.get())
            dur = float(self.test_duration.get())
            if f1 < f0:
                raise ValueError("Frequency end must be >= start.")
            if dur <= 0:
                raise ValueError("Seconds per frequency must be > 0.")
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        # Setup progress bookkeeping
        self._stop_flag.clear()
        self._run_started_at = time.time()
        self._freq_total = (f1 - f0 + 1)
        self._freq_index = 0
        self._current_freq = None
        self._current_file = ""
        self._freq_started_at = None

        self._total_seconds = self._freq_total * float(self.test_duration.get())

        # Open progress modal
        self._open_progress_modal()

        # Start worker
        self._worker = threading.Thread(target=self._run_sequence, daemon=True)
        self._worker.start()

        # Start UI progress pump
        self._pump_progress_ui()

    def _open_progress_modal(self):
        # Create modal
        w = tk.Toplevel(self)
        w.title("Recording…")
        w.resizable(False, False)

        # Make it modal
        w.transient(self.winfo_toplevel())
        w.grab_set()

        # Layout
        frm = ttk.Frame(w, padding=16)
        frm.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frm, text="Recording in progress", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")

        self._progress_label = ttk.Label(frm, text="Preparing…")
        self._progress_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        self._progress_sub = ttk.Label(frm, text="")
        self._progress_sub.grid(row=2, column=0, sticky="w", pady=(2, 0))

        self._progress_bar = ttk.Progressbar(frm, length=380, mode="determinate", maximum=100)
        self._progress_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        self._progress_eta = ttk.Label(frm, text="Elapsed: 0s   Remaining: --")
        self._progress_eta.grid(row=4, column=0, sticky="w", pady=(8, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, sticky="e", pady=(12, 0))
        self._progress_btn_stop = ttk.Button(btns, text="Stop", command=self._stop_from_modal)
        self._progress_btn_stop.pack(side="right")

        self._progress_win = w

        # If user tries to close window, treat as stop
        w.protocol("WM_DELETE_WINDOW", self._stop_from_modal)

    def _stop_from_modal(self):
        self._stop_flag.set()
        if self._progress_label:
            self._progress_label.config(text="Stopping…")
        if self._progress_btn_stop:
            self._progress_btn_stop.config(state="disabled")

    def _close_progress_modal(self):
        if self._progress_win is not None:
            try:
                self._progress_win.grab_release()
            except Exception:
                pass
            try:
                self._progress_win.destroy()
            except Exception:
                pass
        self._progress_win = None
        self._progress_bar = None
        self._progress_label = None
        self._progress_sub = None
        self._progress_eta = None
        self._progress_btn_stop = None

    def _pump_progress_ui(self):
        # Stop pumping if modal is gone
        if self._progress_win is None:
            return

        # Update progress visuals
        now = time.time()
        elapsed = max(0.0, now - (self._run_started_at or now))
        total = max(0.001, float(self._total_seconds or 0.001))
        pct = min(100.0, (elapsed / total) * 100.0)

        # Remaining (simple ETA)
        remaining = max(0.0, total - elapsed)

        if self._progress_bar is not None:
            self._progress_bar["value"] = pct

        # Current label
        if self._progress_label is not None:
            if self._current_freq is None:
                self._progress_label.config(text="Preparing…")
            else:
                self._progress_label.config(
                    text=f"Recording {self._current_freq} Hz  ({self._freq_index}/{self._freq_total})"
                )

        # Sub info
        if self._progress_sub is not None:
            if self._current_file:
                self._progress_sub.config(text=f"File: {os.path.basename(self._current_file)}")
            else:
                self._progress_sub.config(text="")

        # ETA label
        if self._progress_eta is not None:
            self._progress_eta.config(
                text=f"Elapsed: {int(elapsed)}s   Remaining: {int(remaining)}s"
            )

        # If worker finished, close modal and finalize
        if self._worker and (not self._worker.is_alive()):
            self._close_progress_modal()
            return

        # Keep updating
        self.after(200, self._pump_progress_ui)

    # ---------- Worker ----------
    def _run_sequence(self):
        out_dir = None
        try:
            base = self.base_folder.get().strip()
            name = self.folder_name.get().strip() or "umd_logs"
            out_dir = os.path.join(base, name)
            os.makedirs(out_dir, exist_ok=True)

            fs = int(self.sample_freq.get())
            vpp = float(self.vpp.get())
            dur = float(self.test_duration.get())
            f0 = int(self.freq_start.get())
            f1 = int(self.freq_end.get())

            for idx, f in enumerate(range(f0, f1 + 1), start=1):
                if self._stop_flag.is_set():
                    break

                # Record bookkeeping
                self._current_freq = f
                self._freq_index = idx
                self._freq_started_at = time.time()

                # Set Moku waveform for this test frequency
                self.moku_tab.apply_sine(vpp=vpp, freq_hz=float(f))

                # File path
                filename = os.path.join(out_dir, f"log_{f}Hz.txt")
                self._current_file = filename

                # Header exactly like requested
                header = f"Sample Frequency = {fs} Hz Voltage = {vpp:g} Vpp Test Frequency = {f} Hz\n\n"

                self._set_status_mainthread(f"Recording {f} Hz -> {os.path.basename(filename)}")

                t_end = time.time() + dur
                with open(filename, "w", encoding="utf-8") as fp:
                    fp.write(header)

                    serial = 1
                    while time.time() < t_end and not self._stop_flag.is_set():
                        d = getattr(self.display_tab, "last_d_counts", None)

                        
                        if d is not None:
                            fp.write(f"D:{d} N:{serial}\n")
                            serial += 1

                        time.sleep(0.001)  # light poll (~1kHz

            # Finished or stopped
            if self._stop_flag.is_set():
                self._set_status_mainthread("Stopped by user.")
            else:
                self._set_status_mainthread("Done. Opening output folder…")
                if out_dir:
                    open_folder_native(out_dir)

        except Exception as e:
            self._set_status_mainthread(f"Error: {e}")

        finally:
            # If modal still open, UI pump will close it when worker ends.
            pass

    def _set_status_mainthread(self, text: str):
        self.after(0, lambda: self.status.set(f"Status: {text}"))
