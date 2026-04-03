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

        self.sample_freq = tk.IntVar(value=1000)

        self.status = tk.StringVar(value="Status: idle")
        self.wave_summary = tk.StringVar(value="Waiting for waveform settings from Moku tab...")

        # Worker control
        self._stop_flag = threading.Event()
        self._worker = None

        # Snapshot of waveform config taken at start of recording
        self._run_waveform_config = None

        # Progress modal state
        self._progress_win = None
        self._progress_bar = None
        self._progress_label = None
        self._progress_sub = None
        self._progress_eta = None
        self._progress_btn_stop = None

        # Progress bookkeeping
        self._run_started_at = None
        self._total_seconds = None
        self._current_file = ""
        self._current_freq = None
        self._freq_index = 0
        self._freq_total = 0
        self._freq_started_at = None

        self._build_ui()
        self._start_condition_monitor()
        self._refresh_waveform_summary()

    # ---------- UI ----------
    def _build_ui(self):
        ttk.Label(self, text="Record Data", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")

        # Waveform source-of-truth summary
        self.summary_frame = ttk.LabelFrame(self, text="Current waveform from Moku tab", padding=8)
        self.summary_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        self.summary_label = ttk.Label(
            self.summary_frame,
            textvariable=self.wave_summary,
            justify="left",
        )
        self.summary_label.grid(row=0, column=0, sticky="w")

        # Save folder
        ttk.Label(self, text="Save to folder:").grid(row=2, column=0, sticky="e", pady=(10, 0))
        ttk.Entry(self, textvariable=self.base_folder, width=60).grid(row=2, column=1, sticky="ew", pady=(10, 0))
        ttk.Button(self, text="Change...", command=self._pick_folder).grid(row=2, column=2, padx=(8, 0), pady=(10, 0))

        ttk.Label(self, text="Subfolder name:").grid(row=3, column=0, sticky="e", pady=(6, 0))
        ttk.Entry(self, textvariable=self.folder_name, width=25).grid(row=3, column=1, sticky="w", pady=(6, 0))

        ttk.Label(self, text="Seconds per run:").grid(row=4, column=0, sticky="e", pady=(10, 0))
        ttk.Entry(self, textvariable=self.test_duration, width=10).grid(row=4, column=1, sticky="w", pady=(10, 0))

        # Frequency sweep row (shown only for sweepable waveforms)
        self.freq_row = ttk.Frame(self)
        self.freq_row.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        ttk.Label(self.freq_row, text="Frequency range (Hz):").grid(row=0, column=0, sticky="e")
        sweep_box = ttk.Frame(self.freq_row)
        sweep_box.grid(row=0, column=1, sticky="w")
        self.freq_start_entry = ttk.Entry(sweep_box, textvariable=self.freq_start, width=6)
        self.freq_start_entry.pack(side="left")
        ttk.Label(sweep_box, text=" to ").pack(side="left")
        self.freq_end_entry = ttk.Entry(sweep_box, textvariable=self.freq_end, width=6)
        self.freq_end_entry.pack(side="left")

        ttk.Label(self, text="Sample Frequency (Hz):").grid(row=6, column=0, sticky="e", pady=(6, 0))
        ttk.Entry(self, textvariable=self.sample_freq, width=10).grid(row=6, column=1, sticky="w", pady=(6, 0))

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
        if not getattr(self.moku_tab, "is_connected", lambda: False)():
            return False
        if not getattr(self.display_tab, "is_mqtt_connected", lambda: False)():
            return False
        if not getattr(self.display_tab, "is_umd_running", lambda: False)():
            return False
        if not getattr(self.display_tab, "is_streaming", lambda: False)():
            return False
        return True

    def _start_condition_monitor(self):
        moku_ok = getattr(self.moku_tab, "is_connected", lambda: False)()
        mqtt_ok = getattr(self.display_tab, "is_mqtt_connected", lambda: False)()
        umd_ok = getattr(self.display_tab, "is_umd_running", lambda: False)()
        stream_ok = getattr(self.display_tab, "is_streaming", lambda: False)()

        ok = moku_ok and mqtt_ok and umd_ok and stream_ok

        self.start_btn.config(state=("normal" if ok else "disabled"))

        self.status.set(
            ("Status: ready ✅ " if ok else "Status: waiting ❌ ")
            + f"| Moku={moku_ok} MQTT={mqtt_ok} uMD={umd_ok} Stream={stream_ok}"
        )

        self.after(300, self._start_condition_monitor)

    def _refresh_waveform_summary(self):
        try:
            cfg = self.moku_tab.get_current_waveform_config()
            self.wave_summary.set(self._format_wave_summary(cfg))

            if cfg.get("supports_frequency_sweep", False):
                self.freq_row.grid()
                self.freq_start_entry.configure(state="normal")
                self.freq_end_entry.configure(state="normal")
            else:
                self.freq_row.grid_remove()
        except Exception:
            self.wave_summary.set("Waiting for waveform settings from Moku tab...")
            self.freq_row.grid()

        self.after(300, self._refresh_waveform_summary)

    @staticmethod
    def _format_wave_summary(cfg: dict) -> str:
        lines = [
            f"Waveform: {cfg['type']}",
            f"Channel: {cfg['channel']}",
            f"Amplitude: {cfg['amplitude']:g} Vpp",
        ]

        wave_type = cfg["type"]

        if wave_type != "Noise":
            lines.append(f"Base frequency: {cfg['frequency']:g} Hz")
            lines.append(f"Offset: {cfg['offset']:g} V")
            lines.append(f"Phase: {cfg['phase']:g}°")

        if wave_type == "Square":
            lines.append(f"Duty: {cfg['duty']:g}%")
        elif wave_type == "Ramp":
            lines.append(f"Symmetry: {cfg['symmetry']:g}%")
        elif wave_type == "Pulse":
            lines.append(f"Pulse width: {cfg['pulse_width']:g} s")
            lines.append(f"Edge time: {cfg['edge_time']:g} s")

        if cfg.get("supports_frequency_sweep", False):
            lines.append("Recording mode: frequency sweep")
        else:
            lines.append("Recording mode: single run (no frequency sweep)")

        return "\n".join(lines)

    # ---------- Recording lifecycle ----------
    def start_recording(self):
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Already running", "Recording is already in progress.")
            return
        if not self._conditions_ok():
            messagebox.showerror("Not ready", "Conditions not met yet.")
            return

        try:
            cfg = self.moku_tab.get_current_waveform_config()
        except Exception as e:
            messagebox.showerror("Waveform error", f"Could not read waveform settings from Moku tab:\n{e}")
            return

        try:
            dur = float(self.test_duration.get())
            if dur <= 0:
                raise ValueError("Seconds per run must be > 0.")

            if cfg.get("supports_frequency_sweep", False):
                f0 = int(self.freq_start.get())
                f1 = int(self.freq_end.get())
                if f1 < f0:
                    raise ValueError("Frequency end must be >= start.")
                freq_total = f1 - f0 + 1
            else:
                f0 = None
                f1 = None
                freq_total = 1

        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        self._run_waveform_config = cfg
        self._stop_flag.clear()
        self._run_started_at = time.time()
        self._freq_total = freq_total
        self._freq_index = 0
        self._current_freq = None
        self._current_file = ""
        self._freq_started_at = None
        self._total_seconds = self._freq_total * float(self.test_duration.get())

        self._open_progress_modal()

        self._worker = threading.Thread(target=self._run_sequence, daemon=True)
        self._worker.start()

        self._pump_progress_ui()

    def _open_progress_modal(self):
        w = tk.Toplevel(self)
        w.title("Recording…")
        w.resizable(False, False)

        w.transient(self.winfo_toplevel())
        w.grab_set()

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
        if self._progress_win is None:
            return

        now = time.time()
        elapsed = max(0.0, now - (self._run_started_at or now))
        total = max(0.001, float(self._total_seconds or 0.001))
        pct = min(100.0, (elapsed / total) * 100.0)
        remaining = max(0.0, total - elapsed)

        if self._progress_bar is not None:
            self._progress_bar["value"] = pct

        if self._progress_label is not None:
            if self._current_freq is None:
                wave_type = (self._run_waveform_config or {}).get("type", "Waveform")
                self._progress_label.config(text=f"Recording {wave_type}…")
            else:
                self._progress_label.config(
                    text=f"Recording {self._run_waveform_config['type']} @ {self._current_freq} Hz  ({self._freq_index}/{self._freq_total})"
                )

        if self._progress_sub is not None:
            if self._current_file:
                self._progress_sub.config(text=f"File: {os.path.basename(self._current_file)}")
            else:
                self._progress_sub.config(text="")

        if self._progress_eta is not None:
            self._progress_eta.config(text=f"Elapsed: {int(elapsed)}s   Remaining: {int(remaining)}s")

        if self._worker and (not self._worker.is_alive()):
            self._close_progress_modal()
            return

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
            dur = float(self.test_duration.get())

            cfg = dict(self._run_waveform_config or {})
            wave_type = cfg["type"]

            if cfg.get("supports_frequency_sweep", False):
                f0 = int(self.freq_start.get())
                f1 = int(self.freq_end.get())
                run_steps = list(range(f0, f1 + 1))
            else:
                run_steps = [None]

            for idx, freq in enumerate(run_steps, start=1):
                if self._stop_flag.is_set():
                    break

                self._current_freq = freq
                self._freq_index = idx
                self._freq_started_at = time.time()

                self.moku_tab.apply_waveform_config_for_recording(cfg, freq_override=freq)

                if freq is None:
                    filename = os.path.join(out_dir, f"log_{wave_type.lower()}.txt")
                else:
                    filename = os.path.join(out_dir, f"log_{freq}Hz.txt")
                self._current_file = filename

                header = self._build_header(fs=fs, cfg=cfg, freq=freq)

                if freq is None:
                    self._set_status_mainthread(f"Recording {wave_type} -> {os.path.basename(filename)}")
                else:
                    self._set_status_mainthread(f"Recording {wave_type} @ {freq} Hz -> {os.path.basename(filename)}")

                t_end = time.time() + dur
                with open(filename, "w", encoding="utf-8") as fp:
                    fp.write(header)

                    serial = 1
                    while time.time() < t_end and not self._stop_flag.is_set():
                        d = getattr(self.display_tab, "last_d_counts", None)
                        if d is not None:
                            fp.write(f"D:{d} N:{serial}\n")
                            serial += 1

                        time.sleep(0.001)

            if self._stop_flag.is_set():
                self._set_status_mainthread("Stopped by user.")
            else:
                self._set_status_mainthread("Done. Opening output folder…")
                if out_dir:
                    open_folder_native(out_dir)

        except Exception as e:
            self._set_status_mainthread(f"Error: {e}")

    @staticmethod
    def _build_header(fs: int, cfg: dict, freq: int | None) -> str:
        parts = [
            f"Sample Frequency = {fs} Hz",
            f"Voltage = {cfg['amplitude']:g} Vpp",
            f"Waveform = {cfg['type']}",
            f"Channel = {cfg['channel']}",
        ]

        if cfg["type"] != "Noise":
            use_freq = freq if freq is not None else cfg["frequency"]
            parts.append(f"Test Frequency = {use_freq:g} Hz")
            parts.append(f"Offset = {cfg['offset']:g} V")
            parts.append(f"Phase = {cfg['phase']:g} deg")

        if cfg["type"] == "Square":
            parts.append(f"Duty = {cfg['duty']:g} %")
        elif cfg["type"] == "Ramp":
            parts.append(f"Symmetry = {cfg['symmetry']:g} %")
        elif cfg["type"] == "Pulse":
            parts.append(f"Pulse Width = {cfg['pulse_width']:g} s")
            parts.append(f"Edge Time = {cfg['edge_time']:g} s")

        return " ".join(parts) + "\n\n"

    def _set_status_mainthread(self, text: str):
        self.after(0, lambda: self.status.set(f"Status: {text}"))