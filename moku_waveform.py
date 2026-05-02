"""
moku_waveform.py  —  Moku:Go Waveform Generator with optional PID smoothing
=============================================================================

Architecture (MiM-first)
------------------------
On Connect, the tab ALWAYS deploys Multi-Instrument Mode:
  Slot 1 — WaveformGenerator
  Slot 2 — PIDController

When PID is OFF:
  WG Slot 1 output  → physical Output 1

When PID is ON:
  WG Slot 1 output  → PID Slot 2 Input A
  PID Slot 2 output → physical Output 1

This file is also the single source of truth for waveform configuration used
by both the manual "Apply Waveform" path and the Record Data tab.
"""

import os
import sys
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

import ttkbootstrap as tb
from ttkbootstrap.constants import *


# ── Optional Moku imports ─────────────────────────────────────────────
try:
    from moku.instruments import (
        WaveformGenerator as _MokuWG,
        PIDController as _MokuPID,
        MultiInstrument as _MokuMiM,
    )
    from moku import MokuException
    HAS_MOKU = True
except Exception:
    _MokuWG = None
    _MokuPID = None
    _MokuMiM = None
    HAS_MOKU = False

    class MokuException(Exception):
        pass


# ── Safe limits ───────────────────────────────────────────────────────
MOKUGO_AMPLITUDE_MIN = 4e-3
MOKUGO_AMPLITUDE_MAX = 10.0
MOKUGO_FREQ_MIN = 1e-3

# Per-wave limits on Moku:Go (practical limits for this app)
MOKUGO_FREQ_MAX_SINE = 20e6
MOKUGO_FREQ_MAX_SQUARE = 5e6
MOKUGO_FREQ_MAX_RAMP = 5e6
MOKUGO_FREQ_MAX_PULSE = 5e6

MOKUGO_OFFSET_MIN = -5.0
MOKUGO_OFFSET_MAX = 5.0
MOKU_PHASE_MIN = 0.0
MOKU_PHASE_MAX = 360.0

DUTY_MIN = 0.0
DUTY_MAX = 100.0

SYMMETRY_MIN = 0.0
SYMMETRY_MAX = 100.0

PULSE_EDGE_TIME_MIN = 16e-9  # Moku:Go
DEFAULT_PULSE_WIDTH = 1e-4   # 100 us
DEFAULT_EDGE_TIME = 16e-9


class MokuWaveformFrame(ttk.Frame):
    """
    Notebook tab for Moku:Go waveform control + optional PID smoothing.

    This tab is the single source of truth for waveform configuration.
    """

    def __init__(self, parent, has_mokucli=None):
        super().__init__(parent, padding=16)

        # ── Internal state ────────────────────────────────────────────
        self._mim = None
        self._wg = None
        self._pid = None
        self._pid_active = False

        # Legacy compat for existing code paths
        self._instrument = None

        if has_mokucli is None:
            has_mokucli = self._check_mokucli()
        self._has_mokucli = has_mokucli

        # ── Tk variables — waveform ──────────────────────────────────
        self.ip_var = tk.StringVar(value="192.168.73.1")
        self.status_var = tk.StringVar(value="Not connected")
        self.channel_var = tk.IntVar(value=1)
        self.wave_type_var = tk.StringVar(value="Sine")
        self.amplitude_var = tk.DoubleVar(value=1.0)
        self.frequency_var = tk.DoubleVar(value=1000.0)
        self.offset_var = tk.DoubleVar(value=0.0)
        self.phase_var = tk.DoubleVar(value=0.0)

        self.duty_var = tk.DoubleVar(value=50.0)
        self.symmetry_var = tk.DoubleVar(value=50.0)
        self.pulse_width_var = tk.DoubleVar(value=DEFAULT_PULSE_WIDTH)
        self.edge_time_var = tk.DoubleVar(value=DEFAULT_EDGE_TIME)

        # ── Tk variables — PID ───────────────────────────────────────
        self.pid_enabled_var = tk.BooleanVar(value=False)
        self.prop_gain_var = tk.DoubleVar(value=10.0)
        self.int_gain_var = tk.DoubleVar(value=0.0)
        self.diff_gain_var = tk.DoubleVar(value=0.0)
        self.int_corner_var = tk.DoubleVar(value=100.0)
        self.diff_corner_var = tk.DoubleVar(value=100.0)
        self.output_limit_var = tk.DoubleVar(value=5.0)
        self.pid_status_var = tk.StringVar(value="PID off")

        # Widget refs used for show/hide/enable logic
        self._frequency_widgets = []
        self._offset_widgets = []
        self._phase_widgets = []
        self._duty_widgets = []
        self._symmetry_widgets = []
        self._pulse_width_widgets = []
        self._edge_time_widgets = []

        if HAS_MOKU and self._has_mokucli:
            self._build_waveform_ui()
        else:
            self._build_setup_ui()

        self.columnconfigure(0, weight=1)
        for c in range(1, 4):
            self.columnconfigure(c, weight=1)

    # ==================================================================
    # Detection helpers
    # ==================================================================
    @staticmethod
    def _check_mokucli() -> bool:
        return shutil.which("mokucli") is not None

    # ==================================================================
    # Public interface used by Record Data tab
    # ==================================================================
    def is_connected(self) -> bool:
        return self._wg is not None

    def apply_sine(self, vpp: float, freq_hz: float, channel: int = 1):
        """
        Backward-compatible helper kept for compatibility with any older code.
        """
        config = {
            "type": "Sine",
            "channel": int(channel),
            "amplitude": float(vpp),
            "frequency": float(freq_hz),
            "offset": 0.0,
            "phase": 0.0,
            "duty": None,
            "symmetry": None,
            "pulse_width": None,
            "edge_time": None,
            "supports_frequency_sweep": True,
        }
        self._apply_waveform_config(config)

    def get_current_waveform_config(self) -> dict:
        """
        Return the current waveform state from the Moku tab as a plain dict.
        This is safe for other tabs to consume and display.
        """
        wave_type = self.wave_type_var.get().strip()
        channel = int(self.channel_var.get())

        config = {
            "type": wave_type,
            "channel": channel,
            "amplitude": float(self.amplitude_var.get()),
            "frequency": float(self.frequency_var.get()) if wave_type != "Noise" else None,
            "offset": float(self.offset_var.get()) if wave_type != "Noise" else None,
            "phase": float(self.phase_var.get()) if wave_type != "Noise" else None,
            "duty": None,
            "symmetry": None,
            "pulse_width": None,
            "edge_time": None,
            "supports_frequency_sweep": wave_type in {"Sine", "Square", "Ramp", "Pulse"},
        }

        if wave_type == "Square":
            config["duty"] = float(self.duty_var.get())
        elif wave_type == "Ramp":
            config["symmetry"] = float(self.symmetry_var.get())
        elif wave_type == "Pulse":
            config["pulse_width"] = float(self.pulse_width_var.get())
            config["edge_time"] = float(self.edge_time_var.get())

        return config

    def apply_waveform_config_for_recording(self, config: dict, freq_override=None):
        """
        Apply a plain config dict captured from the Moku tab. This is the method
        the Record Data worker thread should call, so it does not need to touch
        Tk variables directly.
        """
        cfg = dict(config)
        if freq_override is not None and cfg.get("supports_frequency_sweep", False):
            cfg["frequency"] = float(freq_override)
        self._apply_waveform_config(cfg)

    def apply_current_waveform_for_recording(self, freq_override=None):
        """
        Convenience wrapper: read current UI state and apply it immediately.
        Prefer apply_waveform_config_for_recording() from worker threads.
        """
        cfg = self.get_current_waveform_config()
        self.apply_waveform_config_for_recording(cfg, freq_override=freq_override)

    # ==================================================================
    # Setup / missing-deps UI
    # ==================================================================
    def _build_setup_ui(self):
        for child in self.winfo_children():
            child.destroy()

        ttk.Label(
            self,
            text="Moku:Go Waveform (Setup Required)",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        setup_frame = ttk.LabelFrame(
            self, text="Moku CLI / API not ready", padding=12, bootstyle=SECONDARY
        )
        setup_frame.grid(row=1, column=0, columnspan=4, sticky="nsew")
        for c in range(4):
            setup_frame.columnconfigure(c, weight=1)

        parts = []
        if not HAS_MOKU:
            parts.append("- The Python package 'moku' (Waveform API)")
        if not self._has_mokucli:
            parts.append("- The Moku command-line tool 'mokucli'")
        missing_txt = "\n".join(parts) if parts else "- (Unable to detect components)"

        ttk.Label(
            setup_frame,
            text=(
                "This tab is disabled because the Moku Python stack is not fully installed.\n\n"
                f"Missing components:\n{missing_txt}\n"
            ),
            justify="left",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        instructions = (
            "Quick setup (run these in a terminal):\n"
            "  1. Install / update the Python package:\n"
            "       pip install --upgrade moku\n"
            "  2. Install Moku CLI\n"
            "  3. Make sure 'mokucli' is on your PATH:\n"
            "       mokucli --help\n"
            "  4. Download instrument data (only once):\n"
            "       mokucli instrument download <MokuOS_version>\n"
        )

        text_frame = ttk.Frame(setup_frame)
        text_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(0, 8))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        txt = tk.Text(text_frame, height=10, wrap="word")
        txt.insert("1.0", instructions)
        txt.configure(state="disabled")
        txt.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=scroll.set)

        link_frame = ttk.Frame(setup_frame)
        link_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 4))

        util_link = tk.Label(link_frame, text="Open Moku Utilities page", fg="blue", cursor="hand2")
        util_link.pack(side="left", padx=(0, 12))
        util_link.bind("<Button-1>", lambda e: webbrowser.open("https://liquidinstruments.com/utilities/", new=1))

        docs_link = tk.Label(link_frame, text="Open Python getting-started docs", fg="blue", cursor="hand2")
        docs_link.pack(side="left")
        docs_link.bind(
            "<Button-1>",
            lambda e: webbrowser.open(
                "https://apis.liquidinstruments.com/api/getting-started/starting-python.html",
                new=1,
            ),
        )

        btn_row = ttk.Frame(setup_frame)
        btn_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

        ttk.Button(btn_row, text="Verify Moku setup", bootstyle=PRIMARY, command=self._on_verify_clicked).pack(side="left")

        ttk.Label(
            setup_frame,
            text="Once the commands above succeed, click 'Verify Moku setup' to enable this tab.",
            justify="left",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

        self.rowconfigure(1, weight=1)

    def _on_verify_clicked(self):
        self._has_mokucli = self._check_mokucli()
        if not HAS_MOKU:
            messagebox.showerror(
                "Moku Python package missing",
                "The 'moku' Python package is still not importable.\n\n"
                "Make sure you ran:\n    pip install --upgrade moku",
            )
            return
        if not self._has_mokucli:
            messagebox.showerror(
                "mokucli not found",
                "I still cannot find 'mokucli' on PATH.\n\n"
                "Try reopening your terminal after installing Moku CLI.",
            )
            return
        messagebox.showinfo("Moku ready", "Moku CLI and Python package look good.\n\nEnabling the waveform controls.")
        self._build_waveform_ui()

    # ==================================================================
    # Full waveform UI
    # ==================================================================
    def _build_waveform_ui(self):
        for child in self.winfo_children():
            child.destroy()

        ttk.Label(
            self,
            text="Moku:Go Waveform Generator",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w")

        # ── Connection frame ──────────────────────────────────────────
        conn_frame = ttk.LabelFrame(self, text="Connection", padding=8)
        conn_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 5))
        conn_frame.columnconfigure(1, weight=1)

        ttk.Label(conn_frame, text="Moku:Go IP:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(conn_frame, textvariable=self.ip_var, width=20).grid(row=0, column=1, sticky="ew")
        ttk.Button(conn_frame, text="Connect", bootstyle=SUCCESS, command=self._connect).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(conn_frame, text="Disconnect", bootstyle=DANGER, command=self._disconnect).grid(row=0, column=3, padx=(4, 0))
        ttk.Label(conn_frame, textvariable=self.status_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))

        ttk.Button(conn_frame, text="Wi-Fi help", bootstyle=INFO, command=self._open_wifi_settings).grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(
            conn_frame,
            text=(
                "Tip: connect this computer to the MokuGo Wi-Fi "
                "(ex: 'MokuGo-003703')\n"
                "or to the same lab network where the Moku:Go is connected."
            ),
            justify="left",
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(2, 0))

        # ── Waveform settings ─────────────────────────────────────────
        wf_frame = ttk.LabelFrame(self, text="Waveform Settings", padding=8)
        wf_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(10, 5))
        for c in range(4):
            wf_frame.columnconfigure(c, weight=1)

        ttk.Label(wf_frame, text="Channel:").grid(row=0, column=0, sticky="e", pady=2)
        ttk.Combobox(wf_frame, textvariable=self.channel_var, values=[1, 2], state="readonly", width=5).grid(
            row=0, column=1, sticky="w", pady=2
        )

        ttk.Label(wf_frame, text="Type:").grid(row=0, column=2, sticky="e", pady=2)
        type_cb = ttk.Combobox(
            wf_frame,
            textvariable=self.wave_type_var,
            values=["Sine", "Square", "Ramp", "Pulse", "Noise"],
            state="readonly",
            width=10,
        )
        type_cb.grid(row=0, column=3, sticky="w", pady=2)
        type_cb.bind("<<ComboboxSelected>>", self._on_type_changed)

        # Amplitude
        ttk.Label(wf_frame, text="Amplitude (Vpp):").grid(row=1, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.amplitude_var, width=10).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(wf_frame, text=f"[{MOKUGO_AMPLITUDE_MIN:.4f} – {MOKUGO_AMPLITUDE_MAX:.1f}]").grid(
            row=1, column=2, columnspan=2, sticky="w", pady=2
        )

        # Frequency
        self._frequency_widgets = self._make_setting_row(
            frame=wf_frame,
            row=2,
            label="Frequency (Hz):",
            variable=self.frequency_var,
            hint="Waveform repetition rate",
        )

        # Offset
        self._offset_widgets = self._make_setting_row(
            frame=wf_frame,
            row=3,
            label="Offset (V):",
            variable=self.offset_var,
            hint=f"[{MOKUGO_OFFSET_MIN:.1f} – {MOKUGO_OFFSET_MAX:.1f}]",
        )

        # Phase
        self._phase_widgets = self._make_setting_row(
            frame=wf_frame,
            row=4,
            label="Phase (deg):",
            variable=self.phase_var,
            hint=f"[{MOKU_PHASE_MIN:.0f} – {MOKU_PHASE_MAX:.0f}]",
        )

        # Square-only
        self._duty_widgets = self._make_setting_row(
            frame=wf_frame,
            row=5,
            label="Duty (%):",
            variable=self.duty_var,
            hint=f"[{DUTY_MIN:.0f} – {DUTY_MAX:.0f}] (Square only)",
        )

        # Ramp-only
        self._symmetry_widgets = self._make_setting_row(
            frame=wf_frame,
            row=6,
            label="Symmetry (% rise):",
            variable=self.symmetry_var,
            hint=f"[{SYMMETRY_MIN:.0f} – {SYMMETRY_MAX:.0f}] (Ramp only)",
        )

        # Pulse-only
        self._pulse_width_widgets = self._make_setting_row(
            frame=wf_frame,
            row=7,
            label="Pulse width (s):",
            variable=self.pulse_width_var,
            hint="Must be > 0 and <= period (Pulse only)",
        )

        self._edge_time_widgets = self._make_setting_row(
            frame=wf_frame,
            row=8,
            label="Edge time (s):",
            variable=self.edge_time_var,
            hint="Moku:Go min 16 ns and <= pulse width",
        )

        # ── Action buttons ────────────────────────────────────────────
        btn_frame = ttk.Frame(self, padding=(0, 10, 0, 0))
        btn_frame.grid(row=3, column=0, columnspan=4, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ttk.Button(btn_frame, text="Apply Waveform", bootstyle=PRIMARY, command=self._apply_waveform).grid(
            row=0, column=0, sticky="e", padx=(0, 5)
        )
        ttk.Button(btn_frame, text="Stop Output", bootstyle=SECONDARY, command=self._stop_output).grid(
            row=0, column=1, sticky="w", padx=(5, 0)
        )

        # ── PID Smoothing section ─────────────────────────────────────
        pid_frame = ttk.LabelFrame(self, text="PID Smoothing (Closed-Loop)", padding=8)
        pid_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(10, 5))
        pid_frame.columnconfigure(1, weight=1)

        self._pid_check = ttk.Checkbutton(
            pid_frame,
            text="Enable PID Smoothing",
            variable=self.pid_enabled_var,
            command=self._on_pid_toggled,
            bootstyle="round-toggle",
        )
        self._pid_check.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        ttk.Label(
            pid_frame,
            text=(
                "When enabled, Moku PID Controller (Slot 2) corrects the output\n"
                "in hardware at MHz speed. Waveform settings are preserved."
            ),
            font=("Segoe UI", 8),
            foreground="grey",
            justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        pid_fields = [
            ("Prop gain (dB):", self.prop_gain_var, "Proportional"),
            ("Int gain (dB):", self.int_gain_var, "Integrator"),
            ("Diff gain (dB):", self.diff_gain_var, "Differentiator"),
            ("Int corner (Hz):", self.int_corner_var, "Integrator saturation"),
            ("Diff corner (Hz):", self.diff_corner_var, "Differentiator saturation"),
            ("Output limit (V):", self.output_limit_var, "Protects piezo"),
        ]

        self._pid_entries = []
        for r, (label, var, tip) in enumerate(pid_fields, start=2):
            ttk.Label(pid_frame, text=label).grid(row=r, column=0, sticky="e", padx=(0, 4), pady=2)
            entry = ttk.Entry(pid_frame, textvariable=var, width=10)
            entry.grid(row=r, column=1, sticky="w", pady=2)
            entry.config(state="disabled")
            self._pid_entries.append(entry)
            ttk.Label(pid_frame, text=tip, font=("Segoe UI", 7), foreground="grey").grid(
                row=r, column=2, sticky="w", padx=(4, 0)
            )

        gain_row = 2 + len(pid_fields)
        self._apply_gains_btn = ttk.Button(
            pid_frame,
            text="Apply Gains",
            bootstyle=SECONDARY,
            command=self._apply_pid_gains,
            state="disabled",
        )
        self._apply_gains_btn.grid(row=gain_row, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(pid_frame, textvariable=self.pid_status_var, font=("Segoe UI", 8), foreground="teal").grid(
            row=gain_row, column=2, sticky="w", padx=(8, 0), pady=(8, 0)
        )

        self.rowconfigure(2, weight=1)
        self._on_type_changed()

    def _make_setting_row(self, frame, row: int, label: str, variable, hint: str):
        lbl = ttk.Label(frame, text=label)
        lbl.grid(row=row, column=0, sticky="e", pady=2)
        entry = ttk.Entry(frame, textvariable=variable, width=10)
        entry.grid(row=row, column=1, sticky="w", pady=2)
        hint_lbl = ttk.Label(frame, text=hint)
        hint_lbl.grid(row=row, column=2, columnspan=2, sticky="w", pady=2)
        return [lbl, entry, hint_lbl]

    # ==================================================================
    # Connection logic (MiM-first)
    # ==================================================================
    def _connect(self):
        if not HAS_MOKU:
            messagebox.showerror(
                "Moku Python package missing",
                "Cannot import the Moku instruments.\n\nMake sure 'moku' is installed in this environment.",
            )
            return

        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Missing IP", "Please enter the Moku:Go IP address.")
            return

        self._disconnect(silent=True)

        try:
            self.status_var.set("Connecting (MiM)...")
            self.update_idletasks()

            self._mim = _MokuMiM(ip, force_connect=True, platform_id=2)
            self._wg = self._mim.set_instrument(1, _MokuWG)
            self._pid = self._mim.set_instrument(2, _MokuPID)

            self._set_routing_wg_direct()

            self._instrument = self._wg

            self._pid_active = False
            self.pid_enabled_var.set(False)
            self.pid_status_var.set("PID off — WG driving Output 1 directly")

            self.status_var.set(f"Connected (MiM) — {ip}")

        except Exception as e:
            self._mim = None
            self._wg = None
            self._pid = None
            self._instrument = None
            self.status_var.set("Not connected")
            messagebox.showerror("Connection failed", str(e))

    def _disconnect(self, silent: bool = False):
        self._pid_active = False
        self.pid_enabled_var.set(False)
        if self._mim is not None:
            try:
                self._mim.relinquish_ownership()
            except Exception:
                pass
        self._mim = None
        self._wg = None
        self._pid = None
        self._instrument = None
        self.status_var.set("Not connected")
        self.pid_status_var.set("PID off")
        if not silent:
            messagebox.showinfo("Disconnected", "Disconnected from Moku:Go.")

    # ==================================================================
    # MiM routing
    # ==================================================================
    def _set_routing_wg_direct(self):
        if self._mim is None:
            return
        self._mim.set_connections(connections=[{"source": "Slot1OutA", "destination": "Output1"}])

    def _set_routing_pid_active(self):
        if self._mim is None:
            return
        self._mim.set_connections(
            connections=[
                {"source": "Slot1OutA", "destination": "Slot2InA"},
                {"source": "Slot2OutA", "destination": "Output1"},
            ]
        )

    # ==================================================================
    # PID toggle
    # ==================================================================
    def _on_pid_toggled(self):
        if self._wg is None:
            self.pid_enabled_var.set(False)
            messagebox.showwarning("Not connected", "Connect to Moku:Go first.")
            return

        want_pid = self.pid_enabled_var.get()

        if want_pid:
            self._enable_pid()
        else:
            self._disable_pid()

        state = "normal" if want_pid else "disabled"
        for entry in self._pid_entries:
            entry.config(state=state)
        self._apply_gains_btn.config(state="normal" if want_pid else "disabled")

    def _enable_pid(self):
        try:
            self._pid.set_control_matrix(channel=1, input_gain1=1, input_gain2=0)
            self._push_pid_gains()

            try:
                limit_v = float(self.output_limit_var.get())
                self._pid.set_output_limit(channel=1, limit=limit_v)
            except Exception:
                pass

            self._pid.enable_input(1, True)
            self._pid.enable_output(1, signal=True, output=True)

            self._set_routing_pid_active()

            self._pid_active = True
            self.pid_status_var.set("PID active — smoothing output at MHz")
            self.status_var.set(f"{self.status_var.get().split('—')[0].strip()} — PID ON")

        except Exception as e:
            self.pid_enabled_var.set(False)
            self._pid_active = False
            self.pid_status_var.set(f"PID enable failed: {e}")
            messagebox.showerror("PID enable failed", str(e))

    def _disable_pid(self):
        try:
            try:
                self._pid.enable_output(1, signal=False, output=False)
            except Exception:
                pass

            self._set_routing_wg_direct()

            self._pid_active = False
            self.pid_status_var.set("PID off — WG driving Output 1 directly")
            self.status_var.set(f"{self.status_var.get().replace(' — PID ON', '')}")

        except Exception as e:
            self.pid_status_var.set(f"PID disable error: {e}")

    def _apply_pid_gains(self):
        if self._pid is None or not self._pid_active:
            return
        try:
            self._push_pid_gains()
            self.pid_status_var.set("Gains applied")
        except Exception as e:
            self.pid_status_var.set(f"Gain error: {e}")
            messagebox.showerror("Apply gains failed", str(e))

    def _push_pid_gains(self):
        prop = float(self.prop_gain_var.get())
        intg = float(self.int_gain_var.get())
        diff = float(self.diff_gain_var.get())

        kwargs = dict(channel=1, overall_gain=0, prop_gain=prop)

        if intg != 0.0:
            kwargs["int_gain"] = intg
            kwargs["int_corner"] = float(self.int_corner_var.get())
        if diff != 0.0:
            kwargs["diff_gain"] = diff
            kwargs["diff_corner"] = float(self.diff_corner_var.get())

        self._pid.set_by_gain(**kwargs)

    # ==================================================================
    # Waveform application
    # ==================================================================
    def _apply_waveform(self):
        if self._wg is None:
            messagebox.showwarning("Not connected", "Connect to your Moku:Go first.")
            return

        try:
            config = self.get_current_waveform_config()
            self._apply_waveform_config(config)
        except MokuException as e:
            messagebox.showerror("Moku error", str(e))
        except Exception as e:
            messagebox.showerror("Error applying waveform", str(e))

    def _apply_waveform_config(self, config: dict):
        if self._wg is None:
            raise RuntimeError("Moku not connected")

        cfg = self._validate_waveform_config(config)
        wave_type = cfg["type"]

        kwargs = {
            "channel": cfg["channel"],
            "type": wave_type,
            "strict": True,
        }

        if wave_type == "Noise":
            kwargs["amplitude"] = cfg["amplitude"]
        else:
            kwargs["amplitude"] = cfg["amplitude"]
            kwargs["frequency"] = cfg["frequency"]
            kwargs["offset"] = cfg["offset"]
            kwargs["phase"] = cfg["phase"]

            if wave_type == "Square":
                kwargs["duty"] = cfg["duty"]
            elif wave_type == "Ramp":
                kwargs["symmetry"] = cfg["symmetry"]
            elif wave_type == "Pulse":
                kwargs["pulse_width"] = cfg["pulse_width"]
                kwargs["edge_time"] = cfg["edge_time"]

        self._wg.generate_waveform(**kwargs)

        summary = self._format_waveform_status(cfg)
        pid_note = " (PID smoothing)" if self._pid_active else ""
        self.status_var.set(f"{summary}{pid_note}")

    def _validate_waveform_config(self, config: dict) -> dict:
        cfg = dict(config)
        wave_type = str(cfg["type"]).strip()
        channel = int(cfg["channel"])

        if channel not in (1, 2):
            raise ValueError("Channel must be 1 or 2.")

        amplitude = float(cfg["amplitude"])
        if not (MOKUGO_AMPLITUDE_MIN <= amplitude <= MOKUGO_AMPLITUDE_MAX):
            raise ValueError(
                f"Amplitude {amplitude} Vpp is out of range. "
                f"Allowed: {MOKUGO_AMPLITUDE_MIN:.4f} – {MOKUGO_AMPLITUDE_MAX:.1f} Vpp."
            )
        cfg["amplitude"] = amplitude

        if wave_type == "Noise":
            return cfg

        frequency = float(cfg["frequency"])
        fmax = self._get_freq_max_for_waveform(wave_type)
        if not (MOKUGO_FREQ_MIN <= frequency <= fmax):
            raise ValueError(
                f"Frequency {frequency} Hz is out of range for {wave_type}. "
                f"Allowed: {MOKUGO_FREQ_MIN:g} – {fmax:g} Hz."
            )
        cfg["frequency"] = frequency

        offset = float(cfg["offset"])
        if not (MOKUGO_OFFSET_MIN <= offset <= MOKUGO_OFFSET_MAX):
            raise ValueError(
                f"Offset {offset} V is out of range. "
                f"Allowed: {MOKUGO_OFFSET_MIN:.1f} – {MOKUGO_OFFSET_MAX:.1f} V."
            )
        cfg["offset"] = offset

        phase = float(cfg["phase"])
        if not (MOKU_PHASE_MIN <= phase <= MOKU_PHASE_MAX):
            raise ValueError(
                f"Phase {phase} deg is out of range. "
                f"Allowed: {MOKU_PHASE_MIN:.0f} – {MOKU_PHASE_MAX:.0f} deg."
            )
        cfg["phase"] = phase

        if wave_type == "Square":
            duty = float(cfg["duty"])
            if not (DUTY_MIN <= duty <= DUTY_MAX):
                raise ValueError(f"Duty {duty}% is out of range. Allowed: {DUTY_MIN:.0f} – {DUTY_MAX:.0f}%.")
            cfg["duty"] = duty

        elif wave_type == "Ramp":
            symmetry = float(cfg["symmetry"])
            if not (SYMMETRY_MIN <= symmetry <= SYMMETRY_MAX):
                raise ValueError(
                    f"Symmetry {symmetry}% is out of range. Allowed: {SYMMETRY_MIN:.0f} – {SYMMETRY_MAX:.0f}%."
                )
            cfg["symmetry"] = symmetry

        elif wave_type == "Pulse":
            pulse_width = float(cfg["pulse_width"])
            if pulse_width <= 0:
                raise ValueError("Pulse width must be > 0.")
            period = 1.0 / frequency
            if pulse_width > period:
                raise ValueError("Pulse width must be <= one waveform period.")
            cfg["pulse_width"] = pulse_width

            edge_time = float(cfg["edge_time"])
            if edge_time < PULSE_EDGE_TIME_MIN:
                raise ValueError(f"Edge time must be >= {PULSE_EDGE_TIME_MIN:g} s on Moku:Go.")
            if edge_time > pulse_width:
                raise ValueError("Edge time must be <= pulse width.")
            cfg["edge_time"] = edge_time

        return cfg

    @staticmethod
    def _get_freq_max_for_waveform(wave_type: str) -> float:
        if wave_type == "Sine":
            return MOKUGO_FREQ_MAX_SINE
        if wave_type == "Square":
            return MOKUGO_FREQ_MAX_SQUARE
        if wave_type == "Ramp":
            return MOKUGO_FREQ_MAX_RAMP
        if wave_type == "Pulse":
            return MOKUGO_FREQ_MAX_PULSE
        return MOKUGO_FREQ_MAX_SINE

    @staticmethod
    def _format_waveform_status(cfg: dict) -> str:
        wave_type = cfg["type"]
        ch = cfg["channel"]
        amp = cfg["amplitude"]

        if wave_type == "Noise":
            return f"Noise on ch{ch}: {amp:g} Vpp"

        base = (
            f"{wave_type} on ch{ch}: {amp:g} Vpp, "
            f"{cfg['frequency']:g} Hz, offset {cfg['offset']:g} V, phase {cfg['phase']:g}°"
        )

        if wave_type == "Square":
            base += f", duty {cfg['duty']:g}%"
        elif wave_type == "Ramp":
            base += f", symmetry {cfg['symmetry']:g}%"
        elif wave_type == "Pulse":
            base += f", pulse_width {cfg['pulse_width']:g} s, edge_time {cfg['edge_time']:g} s"

        return base

    # ==================================================================
    # Misc helpers
    # ==================================================================
    def _on_type_changed(self, event=None):
        wave_type = self.wave_type_var.get().strip()

        self._set_widget_group_state(self._frequency_widgets, enabled=wave_type != "Noise")
        self._set_widget_group_state(self._offset_widgets, enabled=wave_type != "Noise")
        self._set_widget_group_state(self._phase_widgets, enabled=wave_type != "Noise")

        self._set_widget_group_state(self._duty_widgets, enabled=(wave_type == "Square"))
        self._set_widget_group_state(self._symmetry_widgets, enabled=(wave_type == "Ramp"))
        self._set_widget_group_state(self._pulse_width_widgets, enabled=(wave_type == "Pulse"))
        self._set_widget_group_state(self._edge_time_widgets, enabled=(wave_type == "Pulse"))

    @staticmethod
    def _set_widget_group_state(widgets, enabled: bool):
        state = "normal" if enabled else "disabled"
        for widget in widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def _stop_output(self):
        if self._wg is None:
            messagebox.showwarning("Not connected", "Connect to your Moku:Go first.")
            return
        try:
            channel = int(self.channel_var.get())
            self._wg.generate_waveform(channel=channel, type="Off", strict=True)
            self.status_var.set(f"Channel {channel} output OFF")
        except Exception as e:
            messagebox.showerror("Error stopping output", str(e))

    def _open_wifi_settings(self):
        try:
            if sys.platform == "win32":
                os.startfile("ms-settings:network-wifi")
            elif sys.platform.startswith("darwin"):
                subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.network"], check=False)
                messagebox.showinfo("Wi-Fi settings", "Network preferences have been opened.\nConnect to the MokuGo Wi-Fi.")
            else:
                messagebox.showinfo(
                    "Wi-Fi instructions",
                    "Connect this computer to the MokuGo Wi-Fi network "
                    "(for example 'MokuGo-003703'),\n"
                    "or to the same lab network where the Moku:Go is connected.",
                )
        except Exception as e:
            messagebox.showerror(
                "Cannot open Wi-Fi settings",
                f"Please connect manually to the MokuGo Wi-Fi.\n\nDetails: {e}",
            )

    def destroy(self):
        self._disconnect(silent=True)
        super().destroy()