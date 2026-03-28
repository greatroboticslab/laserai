"""
moku_waveform.py  —  Moku:Go Waveform Generator with optional PID smoothing
=============================================================================

Architecture (MiM-first)
------------------------
On Connect, the tab ALWAYS deploys Multi-Instrument Mode:
  Slot 1 — WaveformGenerator  (generates sine / square / noise)
  Slot 2 — PIDController      (dormant until user enables PID)

When PID is OFF:
  WG Slot 1 output  → physical Output 1  (direct, like standalone)

When PID is ON (open-loop smoothing):
  WG Slot 1 output  → PID Slot 2 Input A  (signal to smooth)
  PID Slot 2 output → physical Output 1   (smoothed drive)

Switching PID on/off only changes the Output 1 routing.  The WG
never stops, never re-deploys — waveform settings are preserved.

If the ``moku`` package is not installed, the tab shows a setup
screen (same as original behaviour).
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


# ── Safe limits (from Moku:Go WaveformGenerator docs) ────────────────
MOKUGO_AMPLITUDE_MIN = 4e-3     # Vpp
MOKUGO_AMPLITUDE_MAX = 10.0     # Vpp
MOKUGO_FREQ_MIN      = 1e-3    # Hz
MOKUGO_FREQ_MAX      = 20e6    # Hz
MOKUGO_OFFSET_MIN    = -5.0    # V
MOKUGO_OFFSET_MAX    = 5.0     # V
MOKU_PHASE_MIN       = 0.0     # degrees
MOKU_PHASE_MAX       = 360.0   # degrees
DUTY_MIN             = 0.0     # %
DUTY_MAX             = 100.0   # %


class MokuWaveformFrame(ttk.Frame):
    """
    Notebook tab for Moku:Go waveform control + optional PID smoothing.

    Connects via Multi-Instrument Mode so PID can be toggled without
    tearing down the waveform generator.
    """

    def __init__(self, parent, has_mokucli: bool | None = None):
        super().__init__(parent, padding=16)

        # ── Internal state ────────────────────────────────────────────
        self._mim = None          # MultiInstrument handle
        self._wg  = None          # WaveformGenerator in Slot 1
        self._pid = None          # PIDController in Slot 2
        self._pid_active = False  # Is PID currently driving Output 1?

        # Legacy compat: record_data.py checks self._instrument
        self._instrument = None   # points to self._wg when connected

        if has_mokucli is None:
            has_mokucli = self._check_mokucli()
        self._has_mokucli = has_mokucli

        # ── Tk variables — waveform ───────────────────────────────────
        self.ip_var        = tk.StringVar(value="192.168.73.1")
        self.status_var    = tk.StringVar(value="Not connected")
        self.channel_var   = tk.IntVar(value=1)
        self.wave_type_var = tk.StringVar(value="Sine")
        self.amplitude_var = tk.DoubleVar(value=1.0)
        self.frequency_var = tk.DoubleVar(value=1000.0)
        self.offset_var    = tk.DoubleVar(value=0.0)
        self.phase_var     = tk.DoubleVar(value=0.0)
        self.duty_var      = tk.DoubleVar(value=50.0)

        # ── Tk variables — PID ────────────────────────────────────────
        self.pid_enabled_var  = tk.BooleanVar(value=False)
        self.prop_gain_var    = tk.DoubleVar(value=10.0)    # dB — modest P
        self.int_gain_var     = tk.DoubleVar(value=0.0)     # dB — off initially
        self.diff_gain_var    = tk.DoubleVar(value=0.0)     # dB — off (amplifies noise)
        self.int_corner_var   = tk.DoubleVar(value=100.0)   # Hz
        self.diff_corner_var  = tk.DoubleVar(value=100.0)   # Hz
        self.output_limit_var = tk.DoubleVar(value=5.0)     # V
        self.pid_status_var   = tk.StringVar(value="PID off")

        # ── Build UI ──────────────────────────────────────────────────
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
    # Public interface (used by record_data.py)
    # ==================================================================
    def is_connected(self) -> bool:
        return self._wg is not None

    def apply_sine(self, vpp: float, freq_hz: float, channel: int = 1):
        """Programmatic helper for Record Data tab."""
        if self._wg is None:
            raise RuntimeError("Moku not connected")
        self._wg.generate_waveform(
            channel=int(channel),
            type="Sine",
            amplitude=float(vpp),
            frequency=float(freq_hz),
            offset=0.0,
            phase=0.0,
        )
        self.status_var.set(f"Sine on ch{channel}: {vpp} Vpp, {freq_hz:g} Hz")

    # ==================================================================
    # Setup / missing-deps UI  (unchanged from original)
    # ==================================================================
    def _build_setup_ui(self):
        for child in self.winfo_children():
            child.destroy()

        ttk.Label(
            self, text="Moku:Go Waveform (Setup Required)",
            font=("Segoe UI", 13, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        setup_frame = ttk.LabelFrame(
            self, text="Moku CLI / API not ready",
            padding=12, bootstyle=SECONDARY
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

        ttk.Label(setup_frame, text=(
            "This tab is disabled because the Moku Python stack is not fully installed.\n\n"
            f"Missing components:\n{missing_txt}\n"
        ), justify="left").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        instructions = (
            "Quick setup (run these in a terminal):\n"
            "  1. Install / update the Python package:\n"
            "       pip install --upgrade moku\n"
            "  2. Install Moku CLI:\n"
            "       - Download from: https://liquidinstruments.com/utilities/\n"
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

        util_link = tk.Label(link_frame, text="Open Moku Utilities page",
                             fg="blue", cursor="hand2")
        util_link.pack(side="left", padx=(0, 12))
        util_link.bind("<Button-1>",
                       lambda e: webbrowser.open("https://liquidinstruments.com/utilities/", new=1))

        docs_link = tk.Label(link_frame, text="Open Python getting-started docs",
                             fg="blue", cursor="hand2")
        docs_link.pack(side="left")
        docs_link.bind("<Button-1>",
                       lambda e: webbrowser.open(
                           "https://apis.liquidinstruments.com/api/getting-started/starting-python.html",
                           new=1))

        btn_row = ttk.Frame(setup_frame)
        btn_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

        ttk.Button(btn_row, text="Verify Moku setup", bootstyle=PRIMARY,
                   command=self._on_verify_clicked).pack(side="left")

        ttk.Label(setup_frame, text=(
            "Once the commands above succeed, click 'Verify Moku setup' to enable this tab."
        ), justify="left").grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

        self.rowconfigure(1, weight=1)

    def _on_verify_clicked(self):
        self._has_mokucli = self._check_mokucli()
        if not HAS_MOKU:
            messagebox.showerror("Moku Python package missing",
                                 "The 'moku' Python package is still not importable.\n\n"
                                 "Make sure you ran:\n    pip install --upgrade moku")
            return
        if not self._has_mokucli:
            messagebox.showerror("mokucli not found",
                                 "I still cannot find 'mokucli' on PATH.\n\n"
                                 "Try reopening your terminal after installing Moku CLI.")
            return
        messagebox.showinfo("Moku ready", "Moku CLI and Python package look good.\n\n"
                            "Enabling the waveform controls.")
        self._build_waveform_ui()

    # ==================================================================
    # Full waveform UI  (with PID section added)
    # ==================================================================
    def _build_waveform_ui(self):
        for child in self.winfo_children():
            child.destroy()

        # ── Title ─────────────────────────────────────────────────────
        ttk.Label(self, text="Moku:Go Waveform Generator",
                  font=("Segoe UI", 13, "bold")
                  ).grid(row=0, column=0, columnspan=4, sticky="w")

        # ── Connection frame ──────────────────────────────────────────
        conn_frame = ttk.LabelFrame(self, text="Connection", padding=8)
        conn_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 5))
        conn_frame.columnconfigure(1, weight=1)

        ttk.Label(conn_frame, text="Moku:Go IP:").grid(
            row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(conn_frame, textvariable=self.ip_var, width=20).grid(
            row=0, column=1, sticky="ew")
        ttk.Button(conn_frame, text="Connect", bootstyle=SUCCESS,
                   command=self._connect).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(conn_frame, text="Disconnect", bootstyle=DANGER,
                   command=self._disconnect).grid(row=0, column=3, padx=(4, 0))
        ttk.Label(conn_frame, textvariable=self.status_var).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))

        ttk.Button(conn_frame, text="Wi-Fi help", bootstyle=INFO,
                   command=self._open_wifi_settings).grid(
            row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(conn_frame, text=(
            "Tip: connect this computer to the MokuGo Wi-Fi "
            "(ex: 'MokuGo-003703')\n"
            "or to the same lab network where the Moku:Go is connected."
        ), justify="left").grid(row=3, column=0, columnspan=4, sticky="w", pady=(2, 0))

        # ── Waveform settings ─────────────────────────────────────────
        wf_frame = ttk.LabelFrame(self, text="Waveform Settings", padding=8)
        wf_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(10, 5))
        for c in range(4):
            wf_frame.columnconfigure(c, weight=1)

        ttk.Label(wf_frame, text="Channel:").grid(row=0, column=0, sticky="e", pady=2)
        ttk.Combobox(wf_frame, textvariable=self.channel_var,
                     values=[1, 2], state="readonly", width=5
                     ).grid(row=0, column=1, sticky="w", pady=2)

        ttk.Label(wf_frame, text="Type:").grid(row=0, column=2, sticky="e", pady=2)
        type_cb = ttk.Combobox(wf_frame, textvariable=self.wave_type_var,
                               values=["Sine", "Square", "Noise"],
                               state="readonly", width=10)
        type_cb.grid(row=0, column=3, sticky="w", pady=2)
        type_cb.bind("<<ComboboxSelected>>", self._on_type_changed)

        ttk.Label(wf_frame, text="Amplitude (Vpp):").grid(row=1, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.amplitude_var, width=10).grid(
            row=1, column=1, sticky="w", pady=2)
        ttk.Label(wf_frame, text=f"[{MOKUGO_AMPLITUDE_MIN:.4f} – {MOKUGO_AMPLITUDE_MAX:.1f}]"
                  ).grid(row=1, column=2, columnspan=2, sticky="w", pady=2)

        ttk.Label(wf_frame, text="Frequency (Hz):").grid(row=2, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.frequency_var, width=10).grid(
            row=2, column=1, sticky="w", pady=2)
        ttk.Label(wf_frame, text=f"[{MOKUGO_FREQ_MIN:g} – {MOKUGO_FREQ_MAX:g}]"
                  ).grid(row=2, column=2, columnspan=2, sticky="w", pady=2)

        ttk.Label(wf_frame, text="Offset (V):").grid(row=3, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.offset_var, width=10).grid(
            row=3, column=1, sticky="w", pady=2)
        ttk.Label(wf_frame, text=f"[{MOKUGO_OFFSET_MIN:.1f} – {MOKUGO_OFFSET_MAX:.1f}]"
                  ).grid(row=3, column=2, columnspan=2, sticky="w", pady=2)

        ttk.Label(wf_frame, text="Phase (deg):").grid(row=4, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.phase_var, width=10).grid(
            row=4, column=1, sticky="w", pady=2)
        ttk.Label(wf_frame, text=f"[{MOKU_PHASE_MIN:.0f} – {MOKU_PHASE_MAX:.0f}]"
                  ).grid(row=4, column=2, columnspan=2, sticky="w", pady=2)

        ttk.Label(wf_frame, text="Duty (%):").grid(row=5, column=0, sticky="e", pady=2)
        self.duty_entry = ttk.Entry(wf_frame, textvariable=self.duty_var, width=10)
        self.duty_entry.grid(row=5, column=1, sticky="w", pady=2)
        ttk.Label(wf_frame, text=f"[{DUTY_MIN:.0f} – {DUTY_MAX:.0f}] (Square only)"
                  ).grid(row=5, column=2, columnspan=2, sticky="w", pady=2)

        # ── Action buttons ────────────────────────────────────────────
        btn_frame = ttk.Frame(self, padding=(0, 10, 0, 0))
        btn_frame.grid(row=3, column=0, columnspan=4, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ttk.Button(btn_frame, text="Apply Waveform", bootstyle=PRIMARY,
                   command=self._apply_waveform).grid(
            row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Button(btn_frame, text="Stop Output", bootstyle=SECONDARY,
                   command=self._stop_output).grid(
            row=0, column=1, sticky="w", padx=(5, 0))

        # ── PID Smoothing section ─────────────────────────────────────
        pid_frame = ttk.LabelFrame(self, text="PID Smoothing (Closed-Loop)", padding=8)
        pid_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(10, 5))
        pid_frame.columnconfigure(1, weight=1)

        # Enable toggle
        self._pid_check = ttk.Checkbutton(
            pid_frame, text="Enable PID Smoothing",
            variable=self.pid_enabled_var,
            command=self._on_pid_toggled,
            bootstyle="round-toggle"
        )
        self._pid_check.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        ttk.Label(pid_frame, text=(
            "When enabled, Moku PID Controller (Slot 2) corrects the output\n"
            "in hardware at MHz speed. Waveform settings are preserved."
        ), font=("Segoe UI", 8), foreground="grey", justify="left"
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        # Gain fields
        pid_fields = [
            ("Prop gain (dB):",    self.prop_gain_var,    "Proportional"),
            ("Int gain (dB):",     self.int_gain_var,     "Integrator"),
            ("Diff gain (dB):",    self.diff_gain_var,    "Differentiator"),
            ("Int corner (Hz):",   self.int_corner_var,   "Integrator saturation"),
            ("Diff corner (Hz):",  self.diff_corner_var,  "Differentiator saturation"),
            ("Output limit (V):",  self.output_limit_var, "Protects piezo"),
        ]

        self._pid_entries = []
        for r, (label, var, tip) in enumerate(pid_fields, start=2):
            ttk.Label(pid_frame, text=label).grid(
                row=r, column=0, sticky="e", padx=(0, 4), pady=2)
            entry = ttk.Entry(pid_frame, textvariable=var, width=10)
            entry.grid(row=r, column=1, sticky="w", pady=2)
            entry.config(state="disabled")
            self._pid_entries.append(entry)
            ttk.Label(pid_frame, text=tip, font=("Segoe UI", 7),
                      foreground="grey").grid(
                row=r, column=2, sticky="w", padx=(4, 0))

        # Apply Gains button
        gain_row = 2 + len(pid_fields)
        self._apply_gains_btn = ttk.Button(
            pid_frame, text="Apply Gains", bootstyle=SECONDARY,
            command=self._apply_pid_gains, state="disabled")
        self._apply_gains_btn.grid(
            row=gain_row, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # PID status
        ttk.Label(pid_frame, textvariable=self.pid_status_var,
                  font=("Segoe UI", 8), foreground="teal").grid(
            row=gain_row, column=2, sticky="w", padx=(8, 0), pady=(8, 0))

        # Make waveform settings area expand
        self.rowconfigure(2, weight=1)

        # Init duty field state
        self._on_type_changed()

    # ==================================================================
    # Connection logic  (MiM-first)
    # ==================================================================
    def _connect(self):
        if not HAS_MOKU:
            messagebox.showerror("Moku Python package missing",
                                 "Cannot import the Moku instruments.\n\n"
                                 "Make sure 'moku' is installed in this environment.")
            return

        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Missing IP", "Please enter the Moku:Go IP address.")
            return

        self._disconnect(silent=True)

        try:
            self.status_var.set("Connecting (MiM)...")
            self.update_idletasks()

            # Deploy Multi-Instrument Mode
            self._mim = _MokuMiM(ip, force_connect=True, platform_id=2)

            # Slot 1: WaveformGenerator
            self._wg = self._mim.set_instrument(1, _MokuWG)

            # Slot 2: PIDController (dormant — output disabled)
            self._pid = self._mim.set_instrument(2, _MokuPID)

            # Initial routing: WG drives Output 1 directly (PID off)
            self._set_routing_wg_direct()

            # Legacy compat
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
        """WG Slot 1 drives Output 1 directly."""
        if self._mim is None:
            return
        self._mim.set_connections(connections=[
            {"source": "Slot1OutA", "destination": "Output1"},
        ])

    def _set_routing_pid_active(self):
        """WG feeds PID Input A for smoothing, PID drives Output 1."""
        if self._mim is None:
            return
        self._mim.set_connections(connections=[
            # WG → PID Input A (signal to smooth)
            {"source": "Slot1OutA", "destination": "Slot2InA"},
            # PID → Output 1 (smoothed output)
            {"source": "Slot2OutA", "destination": "Output1"},
        ])

    # ==================================================================
    # PID toggle
    # ==================================================================
    def _on_pid_toggled(self):
        """Called when user checks/unchecks the PID toggle."""
        if self._wg is None:
            self.pid_enabled_var.set(False)
            messagebox.showwarning("Not connected",
                                   "Connect to Moku:Go first.")
            return

        want_pid = self.pid_enabled_var.get()

        if want_pid:
            self._enable_pid()
        else:
            self._disable_pid()

        # Update entry field states
        state = "normal" if want_pid else "disabled"
        for entry in self._pid_entries:
            entry.config(state=state)
        self._apply_gains_btn.config(
            state="normal" if want_pid else "disabled")

    def _enable_pid(self):
        """Switch routing so PID processes WG signal before Output 1."""
        try:
            # Control matrix: Path1 = 1×InA + 0×InB (pass WG signal through)
            self._pid.set_control_matrix(channel=1, input_gain1=1, input_gain2=0)

            # Apply gains
            self._push_pid_gains()

            # Set output limit
            try:
                limit_v = float(self.output_limit_var.get())
                self._pid.set_output_limit(channel=1, limit=limit_v)
            except Exception:
                pass

            # Enable PID input and output (per Moku API docs)
            self._pid.enable_input(1, True)
            self._pid.enable_output(1, signal=True, output=True)

            # Switch routing: WG → PID → Output 1
            self._set_routing_pid_active()

            self._pid_active = True
            self.pid_status_var.set(
                "PID active — smoothing output at MHz")
            self.status_var.set(
                f"{self.status_var.get().split('—')[0].strip()} — PID ON")

        except Exception as e:
            self.pid_enabled_var.set(False)
            self._pid_active = False
            self.pid_status_var.set(f"PID enable failed: {e}")
            messagebox.showerror("PID enable failed", str(e))

    def _disable_pid(self):
        """Switch routing back so WG drives Output 1 directly."""
        try:
            # Disable PID output
            try:
                self._pid.enable_output(1, signal=False, output=False)
            except Exception:
                pass

            # Switch routing: WG drives Output 1 again
            self._set_routing_wg_direct()

            self._pid_active = False
            self.pid_status_var.set("PID off — WG driving Output 1 directly")
            self.status_var.set(
                f"{self.status_var.get().replace(' — PID ON', '')}")

        except Exception as e:
            self.pid_status_var.set(f"PID disable error: {e}")

    def _apply_pid_gains(self):
        """Push current Kp/Ki/Kd values to the PID hardware."""
        if self._pid is None or not self._pid_active:
            return
        try:
            self._push_pid_gains()
            self.pid_status_var.set("Gains applied")
        except Exception as e:
            self.pid_status_var.set(f"Gain error: {e}")
            messagebox.showerror("Apply gains failed", str(e))

    def _push_pid_gains(self):
        """Internal: send gain values to PID Slot 2."""
        prop = float(self.prop_gain_var.get())
        intg = float(self.int_gain_var.get())
        diff = float(self.diff_gain_var.get())

        # Build kwargs — only include nonzero gains to avoid
        # issues with corner frequencies when gains are disabled
        kwargs = dict(channel=1, overall_gain=0, prop_gain=prop)

        # Only add int/diff if the user set nonzero values
        if intg != 0.0:
            kwargs["int_gain"] = intg
            kwargs["int_corner"] = float(self.int_corner_var.get())
        if diff != 0.0:
            kwargs["diff_gain"] = diff
            kwargs["diff_corner"] = float(self.diff_corner_var.get())

        self._pid.set_by_gain(**kwargs)

    # ==================================================================
    # Waveform application  (same as original — routes to self._wg)
    # ==================================================================
    def _apply_waveform(self):
        if self._wg is None:
            messagebox.showwarning("Not connected",
                                   "Connect to your Moku:Go first.")
            return

        try:
            channel = int(self.channel_var.get())
        except ValueError:
            messagebox.showerror("Invalid channel", "Channel must be 1 or 2.")
            return

        wave_type = self.wave_type_var.get()

        try:
            amplitude = float(self.amplitude_var.get())
            frequency = float(self.frequency_var.get())
            offset    = float(self.offset_var.get())
            phase     = float(self.phase_var.get())
            duty      = float(self.duty_var.get())
        except ValueError:
            messagebox.showerror("Invalid input",
                                 "One or more numeric fields contain invalid values.")
            return

        # Range checks
        if not (MOKUGO_AMPLITUDE_MIN <= amplitude <= MOKUGO_AMPLITUDE_MAX):
            messagebox.showerror("Amplitude out of range",
                                 f"Amplitude {amplitude} Vpp is out of range.\n\n"
                                 f"Allowed: {MOKUGO_AMPLITUDE_MIN:.4f} – "
                                 f"{MOKUGO_AMPLITUDE_MAX:.1f} Vpp.")
            return
        if not (MOKUGO_FREQ_MIN <= frequency <= MOKUGO_FREQ_MAX):
            messagebox.showerror("Frequency out of range",
                                 f"Frequency {frequency} Hz is out of range.\n\n"
                                 f"Allowed: {MOKUGO_FREQ_MIN:g} – {MOKUGO_FREQ_MAX:g} Hz.")
            return
        if not (MOKUGO_OFFSET_MIN <= offset <= MOKUGO_OFFSET_MAX):
            messagebox.showerror("Offset out of range",
                                 f"Offset {offset} V is out of range.\n\n"
                                 f"Allowed: {MOKUGO_OFFSET_MIN:.1f} – "
                                 f"{MOKUGO_OFFSET_MAX:.1f} V.")
            return
        if not (MOKU_PHASE_MIN <= phase <= MOKU_PHASE_MAX):
            messagebox.showerror("Phase out of range",
                                 f"Phase {phase} deg is out of range.\n\n"
                                 f"Allowed: {MOKU_PHASE_MIN:.0f} – {MOKU_PHASE_MAX:.0f} deg.")
            return
        if wave_type == "Square":
            if not (DUTY_MIN <= duty <= DUTY_MAX):
                messagebox.showerror("Duty out of range",
                                     f"Duty {duty}% is out of range.\n\n"
                                     f"Allowed: {DUTY_MIN:.0f} – {DUTY_MAX:.0f}%.")
                return

        # Send to Moku WG (Slot 1)
        try:
            kwargs = dict(
                channel=channel,
                type=wave_type,
                amplitude=amplitude,
                frequency=frequency,
                offset=offset,
                phase=phase,
            )
            if wave_type == "Square":
                kwargs["duty"] = duty

            self._wg.generate_waveform(**kwargs)

            pid_note = " (PID smoothing)" if self._pid_active else ""
            self.status_var.set(
                f"{wave_type} on ch{channel}: {amplitude} Vpp, "
                f"{frequency:g} Hz, offset {offset} V{pid_note}")

        except MokuException as e:
            messagebox.showerror("Moku error", str(e))
        except Exception as e:
            messagebox.showerror("Error applying waveform", str(e))

    def _stop_output(self):
        if self._wg is None:
            messagebox.showwarning("Not connected",
                                   "Connect to your Moku:Go first.")
            return
        try:
            channel = int(self.channel_var.get())
        except ValueError:
            messagebox.showerror("Invalid channel", "Channel must be 1 or 2.")
            return
        try:
            self._wg.generate_waveform(channel=channel, type="Off")
            self.status_var.set(f"Channel {channel} output OFF")
        except Exception as e:
            messagebox.showerror("Error stopping output", str(e))

    # ==================================================================
    # Misc helpers
    # ==================================================================
    def _on_type_changed(self, event=None):
        wave_type = self.wave_type_var.get()
        if wave_type == "Square":
            self.duty_entry.config(state="normal")
        else:
            self.duty_entry.config(state="disabled")

    def _open_wifi_settings(self):
        try:
            if sys.platform == "win32":
                os.startfile("ms-settings:network-wifi")
            elif sys.platform.startswith("darwin"):
                subprocess.run(
                    ["open", "x-apple.systempreferences:com.apple.preference.network"],
                    check=False)
                messagebox.showinfo("Wi-Fi settings",
                                    "Network preferences have been opened.\n"
                                    "Connect to the MokuGo Wi-Fi.")
            else:
                messagebox.showinfo("Wi-Fi instructions",
                                    "Connect this computer to the MokuGo Wi-Fi network "
                                    "(for example 'MokuGo-003703'),\n"
                                    "or to the same lab network where the Moku:Go is connected.")
        except Exception as e:
            messagebox.showerror("Cannot open Wi-Fi settings",
                                 f"Please connect manually to the MokuGo Wi-Fi.\n\n"
                                 f"Details: {e}")

    def destroy(self):
        self._disconnect(silent=True)
        super().destroy()