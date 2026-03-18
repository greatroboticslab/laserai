"""
pid_control.py  —  Closed-Loop PID Control tab
===============================================

Architecture (what actually works with Moku hardware)
------------------------------------------------------
Previous versions tried to run WaveformGenerator + Oscilloscope
simultaneously on the same Moku:Go — this fails because the device
only runs ONE instrument at a time.

This version uses PIDController as the SINGLE instrument:
  - It reads Input 1 (piezo sensor) natively at MHz
  - It drives Output 1 (piezo amplifier) natively at MHz
  - Its get_data() returns live monitor samples we can plot
  - Auto-tune works by setting a very high Kp (bang-bang relay
    behaviour) and reading the oscillation from get_data()
  - After tuning, set_by_gain() / set_control_loop_parameters()
    applies the ZN gains and the Moku runs the loop by itself

Workflow  (2 clicks, fully automatic)
--------------------------------------
  1. Wire:   Input 1 <- piezo sensor,  Output 1 -> piezo amp
  2. Enter IP  ->  Connect
  3. Click  AUTO-TUNE  (~15 s)  ->  Kp/Ki/Kd computed automatically
  4. Gains are pushed to hardware immediately  ->  done
     (Moku now running full closed-loop at MHz, no Python in the path)

Simulation mode (no hardware)
-------------------------------
  If moku is not installed or IP is left blank, all steps run against
  a first-order plant simulation so the UI works for demo / offline use.

Auto-tune algorithm  (Astrom-Hagglund relay)
---------------------------------------------
  Phase 1:  set Kp very high, Ki=Kd=0 — the PID acts like a bang-bang
            relay, causing the piezo to oscillate at its ultimate freq.
  Phase 2:  read get_data() to detect zero-crossings.
  Phase 3:  measure Tu (ultimate period) and a (oscillation amplitude).
            Ku = 4*relay_d / (pi * a)
  Ziegler-Nichols:
            Kp = 0.60 * Ku
            Ki = Kp / (Tu/2)
            Kd = Kp * (Tu/8)
  Phase 4:  push final Kp/Ki/Kd to the Moku and enable closed-loop.
"""

import os
import re
import time
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import deque

import numpy as np
import ttkbootstrap as tb
from ttkbootstrap.constants import *

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# ── Optional: SciPy ───────────────────────────────────────────────────────
try:
    from scipy.signal import square as _scipy_square
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ── Optional: Moku ───────────────────────────────────────────────────────
try:
    from moku.instruments import PIDController as _MokuPID
    from moku import MokuException
    HAS_MOKU = True
except Exception:
    _MokuPID = None
    class MokuException(Exception):
        pass
    HAS_MOKU = False

# ── Constants ─────────────────────────────────────────────────────────────
RELAY_CYCLES     = 6        # oscillation cycles to observe during auto-tune
RELAY_KP         = 80.0    # high Kp used as relay (bang-bang approximation)
RELAY_TIMEOUT_S  = 30.0     # max seconds to wait for oscillation
MIN_HALF_SAMPLES = 4        # min samples per half-cycle to count as valid
MONITOR_HZ       = 10       # how often to poll get_data() for the live plot
LIVE_PLOT_SECS   = 5.0      # rolling window width on live plot


# =============================================================================
# Simulation helpers  (used when no hardware is connected)
# =============================================================================

def _generate_staircase(waveform, freq_hz, amplitude, offset,
                         duration_s=3.0, fs=1000.0):
    """Synthetic open-loop staircase for the preview plot."""
    t = np.arange(0, duration_s, 1.0 / fs)
    w = waveform.lower().split("/")[0].strip()
    if w == "sine":
        clean = amplitude * np.sin(2.0 * np.pi * freq_hz * t) + offset
    elif w == "square":
        if HAS_SCIPY:
            clean = amplitude * _scipy_square(2.0 * np.pi * freq_hz * t) + offset
        else:
            clean = amplitude * np.sign(np.sin(2.0 * np.pi * freq_hz * t)) + offset
    else:
        rng   = np.random.default_rng(42)
        clean = offset + rng.normal(0, max(amplitude * 0.25, 0.1), size=len(t))
    return np.round(clean).astype(float), t


def _run_pid_preview(waveform, freq_hz, amp, offset, kp, ki, kd,
                     fs=1000.0):
    """Run offline PID simulation. Returns (time, open_loop, setpoint, closed_loop)."""
    dur   = max(3.0, 5.0 / max(freq_hz, 0.001))
    y_ol, time_ = _generate_staircase(waveform, freq_hz, amp, offset, dur, fs)
    dt    = 1.0 / fs

    w = waveform.lower().split("/")[0].strip()
    if w == "sine":
        sp = amp * np.sin(2.0 * np.pi * freq_hz * time_) + offset
    elif w == "square":
        if HAS_SCIPY:
            sp = amp * _scipy_square(2.0 * np.pi * freq_hz * time_) + offset
        else:
            sp = amp * np.sign(np.sin(2.0 * np.pi * freq_hz * time_)) + offset
    else:
        sp = np.full_like(time_, offset)

    actual = np.zeros_like(time_)
    actual[0] = float(y_ol[0])
    integ  = 0.0
    prev_e = 0.0
    tau    = max(0.005, 1.0 / (2.0 * np.pi * max(freq_hz, 1.0)))

    for i in range(1, len(time_)):
        fb        = np.round(actual[i - 1])
        e         = sp[i] - fb
        integ     = float(np.clip(integ + e * dt, -10.0, 10.0))
        deriv     = (e - prev_e) / dt
        v         = float(np.clip(kp*e + ki*integ + kd*deriv, -10.0, 10.0))
        actual[i] = actual[i-1] + (v - (actual[i-1] - offset)) / tau * dt
        prev_e    = e

    return time_, y_ol, sp, actual


# =============================================================================
# Simulation plant  (used inside auto-tune when no hardware connected)
# =============================================================================

class _SimPlant:
    """First-order piezo plant for simulation mode."""
    def __init__(self, offset_d, freq_hz):
        self.pos    = float(offset_d)
        self.offset = float(offset_d)
        self.tau    = max(0.005, 1.0 / (2.0 * np.pi * max(freq_hz, 1.0)))

    def step(self, v_out, dt):
        dx      = (v_out - (self.pos - self.offset)) / self.tau
        self.pos += dx * dt
        return self.pos


# =============================================================================
# Auto-tuner  (runs in a worker thread)
# =============================================================================

class _AutoTuner:
    """
    Relay auto-tune using Astrom-Hagglund method.

    Hardware mode:
      - Sets PIDController to very high Kp (bang-bang relay behaviour)
      - Reads oscillation via pid.get_data()
      - Computes ZN gains and pushes them

    Simulation mode (pid=None):
      - Same algorithm against the SimPlant model
    """

    def __init__(self, pid, channel, freq_hz, offset_d, adc_scale,
                 relay_kp, progress_cb):
        self._pid        = pid
        self._channel    = channel
        self._freq_hz    = freq_hz
        self._offset_d   = offset_d
        self._adc_scale  = adc_scale
        self._relay_kp   = relay_kp
        self._progress   = progress_cb

        # Simulation fallback
        self._plant      = _SimPlant(offset_d, freq_hz) if pid is None else None
        self._sim_t      = 0.0
        self._dt_sim     = 0.005   # 200 Hz sim rate

    # ── hardware helpers ──────────────────────────────────────────────

    def _hw_set_relay(self):
        """Configure PIDController as a high-gain P-only controller (relay approx)."""
        pid = self._pid
        try:
            # Try set_by_gain first (newer firmware)
            pid.set_by_gain(
                channel=self._channel,
                prop_gain=self._relay_kp,
                int_gain=0.0,
                diff_gain=0.0,
            )
        except Exception:
            try:
                pid.set_control_loop_parameters(
                    channel=self._channel,
                    prop_gain=self._relay_kp,
                    int_gain=0.0,
                    diff_gain=0.0,
                )
            except Exception as e:
                raise RuntimeError(
                    f"Could not configure PIDController relay mode.\n\n"
                    f"Error: {e}\n\n"
                    f"Available methods: {[m for m in dir(pid) if not m.startswith('_')]}"
                )

    def _hw_read(self):
        """
        Read current position from PIDController monitor output.

        On the first successful call we discover which key in get_data()
        contains the sensor array and cache it in self._data_key so
        we never have to guess again.
        """
        try:
            data = self._pid.get_data()

            # ── discover the right key on first call ──────────────────
            if not hasattr(self, "_data_key"):
                self._data_key = None
                if isinstance(data, dict):
                    # Prefer keys that look like 'ch1', 'input1', 'ch_1'
                    preferred = ["ch1", "input1", "ch_1", "monitor1",
                                 "ch2", "input2"]
                    for k in preferred:
                        if k in data:
                            self._data_key = k
                            break
                    # Otherwise take the first key whose value is a sequence
                    if self._data_key is None:
                        for k, v in data.items():
                            if hasattr(v, "__len__") and len(v) > 0:
                                self._data_key = k
                                break
                    # Last resort: first key at all
                    if self._data_key is None and data:
                        self._data_key = list(data.keys())[0]

            # ── extract value ─────────────────────────────────────────
            if isinstance(data, dict):
                raw = data.get(self._data_key,
                               list(data.values())[0] if data else 0.0)
            else:
                raw = data

            if hasattr(raw, "__len__") and len(raw) > 0:
                v = float(np.mean(raw))
            else:
                v = float(raw)

            return v * self._adc_scale

        except Exception:
            return self._offset_d    # fallback: assume at setpoint

    def _hw_push_gains(self, kp, ki, kd):
        """
        Push gains to the Moku PIDController.
        Discovers the correct method name on first call and caches it.
        """
        pid = self._pid

        # ── discover setter method once ───────────────────────────────
        if not hasattr(self, "_gain_setter"):
            self._gain_setter = None
            # Try common method names in preference order
            for name in ["set_by_gain",
                          "set_control_loop_parameters",
                          "set_pid_gains",
                          "set_gains"]:
                if hasattr(pid, name):
                    self._gain_setter = name
                    break
            if self._gain_setter is None:
                available = [m for m in dir(pid) if not m.startswith("_")]
                raise RuntimeError(
                    "Could not find a PID gain setter on this firmware.\n\n"
                    f"All available methods:\n  " +
                    "\n  ".join(available) +
                    "\n\nRun moku_diagnostic.py to identify the correct method.")

        method = getattr(pid, self._gain_setter)

        # ── try calling with standard param names ─────────────────────
        kwargs_options = [
            dict(channel=self._channel,
                 prop_gain=kp, int_gain=ki, diff_gain=kd),
            dict(channel=self._channel,
                 kp=kp, ki=ki, kd=kd),
            dict(channel=self._channel,
                 proportional=kp, integral=ki, derivative=kd),
            # some firmware uses positional
        ]
        last_exc = None
        for kwargs in kwargs_options:
            try:
                method(**kwargs)
                return   # success
            except TypeError as e:
                last_exc = e
                continue

        # If all keyword combos failed, raise with helpful message
        raise RuntimeError(
            f"Called {self._gain_setter}() with several keyword combinations "
            f"but all failed.\n\nLast error: {last_exc}\n\n"
            "Run moku_diagnostic.py to find the exact parameter names."
        )

    # ── simulation helpers ────────────────────────────────────────────

    def _sim_step(self, kp, ki, integ, prev_e, setpoint):
        """One PID step against the sim plant. Returns (pos, new_integ, new_e)."""
        fb    = np.round(self._plant.pos)
        e     = setpoint - fb
        integ = float(np.clip(integ + e * self._dt_sim, -10.0, 10.0))
        v     = float(np.clip(kp * e + ki * integ, -10.0, 10.0))
        pos   = self._plant.step(v, self._dt_sim)
        self._sim_t += self._dt_sim
        return pos, integ, e

    # ── main entry point ──────────────────────────────────────────────

    def run(self):
        """
        Run relay test, compute gains, push to hardware.
        Returns (kp, ki, kd, Tu, Ku).
        Raises RuntimeError on failure.
        """
        self._progress("Auto-tune: starting relay test...")

        if self._pid is not None:
            self._hw_set_relay()

        pos_history    = []   # (time, centred_position)
        cross_times    = []   # times of zero-crossings
        t0             = time.perf_counter()
        integ_sim      = 0.0
        prev_e_sim     = 0.0
        target_crosses = RELAY_CYCLES * 2 + 2

        while True:
            now     = time.perf_counter()
            elapsed = now - t0

            if elapsed > RELAY_TIMEOUT_S:
                raise RuntimeError(
                    f"Auto-tune timed out after {RELAY_TIMEOUT_S:.0f} s.\n\n"
                    "No sustained oscillation detected.\n\n"
                    "Check:\n"
                    "  - Hardware is wired correctly\n"
                    "  - ADC scale matches your sensor\n"
                    "  - Relay Kp is large enough (increase it)\n"
                    "  - Input 1 is connected to the piezo sensor"
                )

            # Read position
            if self._pid is not None:
                pos = self._hw_read()
                time.sleep(1.0 / 100)   # poll at 100 Hz
            else:
                # Simulation: run relay as high-Kp PID
                sp  = self._offset_d    # static setpoint for tuning
                pos, integ_sim, prev_e_sim = self._sim_step(
                    self._relay_kp, 0.0, integ_sim, prev_e_sim, sp)
                time.sleep(self._dt_sim)

            pos_c = pos - self._offset_d
            pos_history.append((elapsed, pos_c))

            # Detect zero-crossing (sign change)
            n = len(pos_history)
            if n >= MIN_HALF_SAMPLES + 2:
                prev_c = pos_history[-2][1]
                if prev_c * pos_c < 0:          # sign changed
                    cross_times.append(elapsed)
                    nc = len(cross_times)
                    self._progress(
                        f"Auto-tune: oscillating  "
                        f"({nc // 2}/{RELAY_CYCLES} cycles complete)...")
                    if nc >= target_crosses:
                        break

        self._progress("Auto-tune: oscillation captured — computing gains...")

        # ── compute Tu and Ku ─────────────────────────────────────────
        valid_crosses = cross_times[2:]      # skip first transient crosses
        if len(valid_crosses) < 4:
            raise RuntimeError(
                "Not enough oscillation cycles detected.\n"
                "Try increasing Relay Kp or checking hardware wiring.")

        half_periods = np.diff(np.array(valid_crosses))
        Tu           = float(np.mean(half_periods)) * 2.0    # full period

        t_valid_start = cross_times[2]
        valid_pos     = [p for t, p in pos_history if t >= t_valid_start]
        a             = float(np.std(valid_pos))   # RMS amplitude

        if a < 1e-6:
            raise RuntimeError(
                "Oscillation amplitude is near zero.\n"
                "Check ADC scale and ensure piezo sensor is connected to Input 1.")

        # Ku from relay formula:  Ku = 4*d / (pi*a)
        # where d = relay amplitude in D-counts  ≈ relay_kp * 1 D-count error
        relay_d = self._relay_kp   # effective relay amplitude in output units
        Ku      = (4.0 * relay_d) / (math.pi * a)

        # Ziegler-Nichols PID
        kp = 0.60 * Ku
        Ti = Tu / 2.0
        Td = Tu / 8.0
        ki = kp / Ti
        kd = kp * Td

        self._progress(
            f"Auto-tune: gains computed  —  "
            f"Tu={Tu*1000:.1f} ms  Ku={Ku:.3f}  "
            f"=>  Kp={kp:.3g}  Ki={ki:.3g}  Kd={kd:.4g}")

        # ── push final gains to hardware ──────────────────────────────
        if self._pid is not None:
            self._hw_push_gains(kp, ki, kd)
            self._progress(
                f"Gains pushed to Moku hardware — "
                f"Kp={kp:.3g}  Ki={ki:.3g}  Kd={kd:.4g}  "
                f"(running at MHz speed)")

        return kp, ki, kd, Tu, Ku


# =============================================================================
# Live monitor thread  (polls PIDController.get_data() for the plot)
# =============================================================================

class _MonitorThread:
    """
    Polls pid.get_data() at ~MONITOR_HZ to feed the live plot.
    Falls back to simulation if pid is None.
    """

    def __init__(self, pid, channel, adc_scale,
                 waveform, freq_hz, amp, offset_d, kp, ki, kd):
        self._pid       = pid
        self._channel   = channel
        self._scale     = adc_scale
        self._waveform  = waveform
        self._freq_hz   = freq_hz
        self._amp       = amp
        self._offset_d  = offset_d
        self._kp        = kp
        self._ki        = ki
        self._kd        = kd

        self._running   = False
        self._thread    = None
        self._t0        = None

        n = int(LIVE_PLOT_SECS * MONITOR_HZ) + 10
        self.buf_t   = deque(maxlen=n)
        self.buf_sp  = deque(maxlen=n)
        self.buf_fb  = deque(maxlen=n)
        self.last_err = None

        # Sim plant for fallback
        self._plant  = _SimPlant(offset_d, freq_hz)
        self._integ  = 0.0
        self._prev_e = 0.0
        self._dt_sim = 0.005

    def start(self):
        self._running = True
        self._t0      = time.perf_counter()
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_snapshot(self):
        return np.array(self.buf_t), np.array(self.buf_sp), np.array(self.buf_fb)

    def _setpoint_at(self, t):
        w = self._waveform.lower().split("/")[0].strip()
        if w == "sine":
            return self._amp * math.sin(2.0*math.pi*self._freq_hz*t) + self._offset_d
        elif w == "square":
            period = 1.0 / max(self._freq_hz, 1e-9)
            return self._amp * (1.0 if (t % period)/period < 0.5 else -1.0) + self._offset_d
        return self._offset_d

    def _loop(self):
        dt_poll = 1.0 / MONITOR_HZ
        while self._running:
            t0_tick = time.perf_counter()
            elapsed = t0_tick - self._t0
            try:
                sp = self._setpoint_at(elapsed)

                if self._pid is not None:
                    # Hardware: self-discovering key lookup
                    data = self._pid.get_data()
                    if not hasattr(self, "_data_key"):
                        self._data_key = None
                        if isinstance(data, dict):
                            for k in ["ch1","input1","ch_1","monitor1","ch2"]:
                                if k in data:
                                    self._data_key = k
                                    break
                            if self._data_key is None:
                                for k, v in data.items():
                                    if hasattr(v, "__len__") and len(v) > 0:
                                        self._data_key = k
                                        break
                            if self._data_key is None and data:
                                self._data_key = list(data.keys())[0]
                    raw = (data.get(self._data_key, list(data.values())[0] if data else 0.0)
                           if isinstance(data, dict) else data)
                    fb = (float(np.mean(raw)) if hasattr(raw, "__len__") and len(raw) > 0
                          else float(raw)) * self._scale
                else:
                    # Simulation: run PID step
                    fb_raw = np.round(self._plant.pos)
                    e      = sp - fb_raw
                    self._integ = float(np.clip(
                        self._integ + e * self._dt_sim, -10.0, 10.0))
                    deriv  = (e - self._prev_e) / self._dt_sim
                    v      = float(np.clip(
                        self._kp*e + self._ki*self._integ + self._kd*deriv,
                        -10.0, 10.0))
                    # run many sim steps between plot samples
                    steps = max(1, int(dt_poll / self._dt_sim))
                    for _ in range(steps):
                        self._plant.step(v, self._dt_sim)
                    fb = float(self._plant.pos)
                    self._prev_e = e

                self.buf_t .append(elapsed)
                self.buf_sp.append(sp)
                self.buf_fb.append(fb)

            except Exception as exc:
                self.last_err = str(exc)

            sleep = dt_poll - (time.perf_counter() - t0_tick)
            if sleep > 0:
                time.sleep(sleep)


# =============================================================================
# GUI
# =============================================================================

class PIDControlFrame(ttk.Frame):
    """
    Notebook tab: PID Closed-Loop Control.

    Left panel  — all settings + buttons
    Right panel — Matplotlib figure (preview after tune / live monitor)

    Workflow:
      Connect  ->  Auto-Tune  ->  done
      (Moku runs the loop at MHz; plot shows live feedback)
    """

    def __init__(self, parent, moku_tab=None):
        super().__init__(parent, padding=10)
        self._moku_tab      = moku_tab
        self._pid           = None    # _MokuPID instance
        self._auto_thread   = None
        self._monitor       = None    # _MonitorThread
        self._plot_after_id = None

        _default_ip = moku_tab.ip_var.get() if moku_tab else "192.168.73.1"

        # ── Tk vars ───────────────────────────────────────────────────
        self.ip_var         = tk.StringVar(value=_default_ip)
        self.channel_var    = tk.IntVar(value=1)
        self.adc_scale_var  = tk.DoubleVar(value=1.0)
        self.relay_kp_var   = tk.DoubleVar(value=RELAY_KP)

        self.waveform_var   = tk.StringVar(value="Sine")
        self.freq_var       = tk.DoubleVar(value=1.0)
        self.amp_var        = tk.DoubleVar(value=10.0)
        self.offset_var     = tk.DoubleVar(value=0.0)

        self.kp_var         = tk.DoubleVar(value=0.0)
        self.ki_var         = tk.DoubleVar(value=0.0)
        self.kd_var         = tk.DoubleVar(value=0.0)

        self.status_var     = tk.StringVar(
            value="Ready  —  wire hardware, connect, then click Auto-Tune")
        self.conn_status_var = tk.StringVar(value="Not connected")

        self._build_ui()

    # ─────────────────────────────────────────────────────────────────
    # UI construction
    # ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=0, minsize=295)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_left(self).grid(row=0, column=0, sticky="nsew",
                                     padx=(0, 10))
        self._build_right(self).grid(row=0, column=1, sticky="nsew")

        ttk.Separator(self, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        ttk.Label(self, textvariable=self.status_var,
                  foreground="gray", anchor="w",
                  wraplength=900).grid(
            row=2, column=0, columnspan=2, sticky="ew")

    def _build_left(self, parent):
        f = ttk.Frame(parent)

        ttk.Label(f, text="PID Closed-Loop Control",
                  font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 8))

        # ── Wiring reminder ──────────────────────────────────────────
        wr = ttk.LabelFrame(f, text="Hardware Wiring", padding=8)
        wr.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(wr,
                  text="Output 1  ->  Piezo amplifier\n"
                       "Input  1  <-  Piezo sensor voltage",
                  font=("Segoe UI", 9), foreground="grey",
                  justify="left").pack(anchor="w")

        # ── Connection ───────────────────────────────────────────────
        conn = ttk.LabelFrame(f, text="Step 1  —  Connect", padding=8)
        conn.pack(fill=tk.X, pady=(0, 6))
        conn.columnconfigure(1, weight=1)

        ttk.Label(conn, text="Moku:Go IP:").grid(
            row=0, column=0, sticky="e", padx=(0, 4))
        ttk.Entry(conn, textvariable=self.ip_var, width=16).grid(
            row=0, column=1, sticky="ew")

        btn_row = ttk.Frame(conn)
        btn_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self._conn_btn = ttk.Button(
            btn_row, text="Connect", bootstyle=SUCCESS,
            command=self._connect)
        self._conn_btn.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_row, text="Disconnect", bootstyle=DANGER,
                   command=self._disconnect).pack(side=tk.LEFT)

        ttk.Label(conn, textvariable=self.conn_status_var,
                  font=("Segoe UI", 8), foreground="teal").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        if not HAS_MOKU:
            ttk.Label(conn,
                      text="moku not installed  ->  simulation mode\n"
                           "(pip install moku  to use real hardware)",
                      font=("Segoe UI", 8), foreground="darkorange",
                      justify="left").grid(
                row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # ── Waveform params ──────────────────────────────────────────
        wp = ttk.LabelFrame(f, text="Setpoint Waveform", padding=8)
        wp.pack(fill=tk.X, pady=(0, 6))
        wp.columnconfigure(1, weight=1)
        for r, (lbl, w) in enumerate([
            ("Waveform:",
             ttk.Combobox(wp, textvariable=self.waveform_var,
                          values=["Sine", "Square", "Noise/Static"],
                          state="readonly", width=14)),
            ("Frequency (Hz):",
             ttk.Entry(wp, textvariable=self.freq_var, width=12)),
            ("Amplitude (D-cnt):",
             ttk.Entry(wp, textvariable=self.amp_var, width=12)),
            ("Offset (D-cnt):",
             ttk.Entry(wp, textvariable=self.offset_var, width=12)),
        ]):
            ttk.Label(wp, text=lbl).grid(
                row=r, column=0, sticky="e", padx=(0, 4), pady=2)
            w.grid(row=r, column=1, sticky="ew", pady=2)

        # ── Auto-tune settings ───────────────────────────────────────
        ts = ttk.LabelFrame(f, text="Tune Settings", padding=8)
        ts.pack(fill=tk.X, pady=(0, 6))
        ts.columnconfigure(1, weight=1)
        for r, (lbl, var, tip) in enumerate([
            ("ADC scale (D/V):", self.adc_scale_var,
             "From sensor datasheet"),
            ("Relay Kp:",        self.relay_kp_var,
             "High = stronger relay. Increase if timeout."),
            ("Channel:",         self.channel_var,
             "1 or 2"),
        ]):
            ttk.Label(ts, text=lbl).grid(
                row=r, column=0, sticky="e", padx=(0, 4), pady=2)
            ttk.Entry(ts, textvariable=var, width=10).grid(
                row=r, column=1, sticky="w", pady=2)
            ttk.Label(ts, text=tip, font=("Segoe UI", 7),
                      foreground="grey").grid(
                row=r, column=2, sticky="w", padx=(4, 0))

        # ── Auto-tune ────────────────────────────────────────────────
        at = ttk.LabelFrame(f, text="Step 2  —  Auto-Tune  (fully automatic)", padding=8)
        at.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(at,
                  text="Runs a ~15 s relay test on your piezo,\n"
                       "detects the natural oscillation period,\n"
                       "computes Kp/Ki/Kd via Ziegler-Nichols,\n"
                       "and pushes gains to hardware automatically.",
                  font=("Segoe UI", 8), foreground="grey",
                  justify="left").pack(anchor="w", pady=(0, 6))

        self._tune_btn = ttk.Button(
            at, text="Auto-Tune", bootstyle=WARNING,
            command=self._start_autotune)
        self._tune_btn.pack(fill=tk.X, ipady=5)

        # ── Computed gains display ────────────────────────────────────
        gf = ttk.LabelFrame(f, text="Computed Gains  (auto-filled)", padding=8)
        gf.pack(fill=tk.X, pady=(0, 6))
        gf.columnconfigure(1, weight=1)
        for r, (lbl, var, tip) in enumerate([
            ("Kp:", self.kp_var, "Proportional"),
            ("Ki:", self.ki_var, "Integral  — kills the staircase"),
            ("Kd:", self.kd_var, "Derivative — damps overshoot"),
        ]):
            ttk.Label(gf, text=lbl).grid(
                row=r, column=0, sticky="e", padx=(0, 4), pady=2)
            ttk.Entry(gf, textvariable=var, width=10).grid(
                row=r, column=1, sticky="w", pady=2)
            ttk.Label(gf, text=tip, font=("Segoe UI", 7),
                      foreground="grey").grid(
                row=r, column=2, sticky="w", padx=(4, 0))

        ttk.Label(gf,
                  text="You can manually adjust and click Re-Push below.",
                  font=("Segoe UI", 7), foreground="grey").grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        self._repush_btn = ttk.Button(
            gf, text="Re-Push Gains to Hardware",
            bootstyle=SECONDARY, command=self._repush_gains,
            state="disabled")
        self._repush_btn.grid(row=4, column=0, columnspan=3,
                               sticky="ew", pady=(6, 0))

        # ── Live monitor ─────────────────────────────────────────────
        lm = ttk.LabelFrame(f, text="Step 3  —  Live Monitor", padding=8)
        lm.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(lm,
                  text="After auto-tune, plot shows live feedback\n"
                       "from the Moku monitor channel.",
                  font=("Segoe UI", 8), foreground="grey",
                  justify="left").pack(anchor="w", pady=(0, 6))

        btn_lm = ttk.Frame(lm)
        btn_lm.pack(fill=tk.X)
        self._mon_start_btn = ttk.Button(
            btn_lm, text="Start Monitor", bootstyle=PRIMARY,
            command=self._start_monitor, state="disabled")
        self._mon_start_btn.pack(side=tk.LEFT, padx=(0, 4), ipady=3,
                                  expand=True, fill=tk.X)
        self._mon_stop_btn = ttk.Button(
            btn_lm, text="Stop", bootstyle=SECONDARY,
            command=self._stop_monitor)
        self._mon_stop_btn.pack(side=tk.LEFT, ipady=3, expand=True, fill=tk.X)

        return f

    def _build_right(self, parent):
        f = ttk.Frame(parent)
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        self._fig  = Figure(figsize=(9, 7))
        self._ax1  = self._fig.add_subplot(2, 1, 1)
        self._ax2  = self._fig.add_subplot(2, 1, 2)
        self._fig.subplots_adjust(hspace=0.42, left=0.1, right=0.97,
                                   top=0.92, bottom=0.08)
        self._draw_placeholder()

        self._canvas = FigureCanvasTkAgg(self._fig, master=f)
        self._canvas.draw()
        self._canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        tb_frame = ttk.Frame(f)
        tb_frame.grid(row=1, column=0, sticky="ew")
        NavigationToolbar2Tk(self._canvas, tb_frame)
        return f

    # ─────────────────────────────────────────────────────────────────
    # Plot helpers
    # ─────────────────────────────────────────────────────────────────

    def _draw_placeholder(self):
        for ax in (self._ax1, self._ax2):
            ax.clear()
            ax.set_facecolor("#f8f9fa")
            ax.text(0.5, 0.5,
                    "1.  Connect  ->  Auto-Tune\n"
                    "    Kp/Ki/Kd computed and pushed automatically\n\n"
                    "2.  Start Monitor  ->  live plot appears here",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=10, color="#aaaaaa", linespacing=1.8)
            ax.set_axis_off()

    def _draw_preview(self, kp, ki, kd):
        """Simulation preview shown immediately after auto-tune completes."""
        try:
            waveform = self.waveform_var.get()
            freq     = float(self.freq_var.get())
            amp      = float(self.amp_var.get())
            off      = float(self.offset_var.get())

            time_, y_ol, sp, cl = _run_pid_preview(
                waveform, freq, amp, off, kp, ki, kd)

            freq_safe = max(freq, 0.01)
            fs        = 1000.0
            show_n    = min(len(time_), int(2 * fs / freq_safe))
            t   = time_[:show_n]

            ol_err = y_ol - sp
            cl_err = cl   - sp
            ol_std = float(np.std(ol_err))
            cl_std = float(np.std(cl_err))
            sr     = (1 - cl_std / max(ol_std, 1e-9)) * 100

            for ax in (self._ax1, self._ax2):
                ax.clear(); ax.set_axis_on()

            self._ax1.step(t, y_ol[:show_n], color="#e74c3c", where="post",
                            alpha=0.55, lw=1.2, label="Open-loop staircase")
            self._ax1.plot(t, sp[:show_n], "k--", lw=1.5, label="Setpoint")
            self._ax1.set_title("BEFORE  —  Open-loop  (simulation preview)",
                                 fontsize=10, fontweight="bold", color="#c0392b")
            self._ax1.set_ylabel("D-counts")
            self._ax1.legend(fontsize=8); self._ax1.grid(True, alpha=0.25)
            self._ax1.text(
                0.02, 0.97,
                f"RMSE = {float(np.sqrt(np.mean(ol_err**2))):.3f}",
                transform=self._ax1.transAxes, ha="left", va="top",
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#ffe0e0", alpha=0.85))

            self._ax2.plot(t, cl[:show_n], color="#2980b9", lw=2,
                            label="PID controlled (smooth)")
            self._ax2.plot(t, sp[:show_n], "k--", lw=1.5, label="Setpoint")
            self._ax2.set_title(
                "AFTER  —  Closed-loop PID  (simulation preview)",
                fontsize=10, fontweight="bold", color="#1a6fa0")
            self._ax2.set_ylabel("D-counts")
            self._ax2.set_xlabel("Time (s)")
            self._ax2.legend(fontsize=8); self._ax2.grid(True, alpha=0.25)
            self._ax2.text(
                0.02, 0.97,
                f"RMSE = {float(np.sqrt(np.mean(cl_err**2))):.3f}   "
                f"sigma-reduction = {sr:.1f}%",
                transform=self._ax2.transAxes, ha="left", va="top",
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="#ddeeff", alpha=0.85))

            self._fig.suptitle(
                f"Simulation preview  |  "
                f"Kp={kp:.3g}  Ki={ki:.3g}  Kd={kd:.4g}",
                fontsize=9, color="#555555")
            self._canvas.draw()
        except Exception:
            pass    # preview is optional

    def _refresh_live_plot(self):
        if self._monitor is None:
            return

        t_arr, sp_arr, fb_arr = self._monitor.get_snapshot()

        if len(t_arr) > 2:
            for ax in (self._ax1, self._ax2):
                ax.clear(); ax.set_axis_on()

            self._ax1.plot(t_arr, sp_arr, "k--", lw=1.5, label="Setpoint")
            self._ax1.plot(t_arr, fb_arr, color="#2980b9", lw=1.5,
                            alpha=0.85, label="Feedback (sensor)")
            self._ax1.set_title("Live  —  Setpoint vs Feedback",
                                 fontsize=10, fontweight="bold")
            self._ax1.set_ylabel("D-counts")
            self._ax1.legend(fontsize=8)
            self._ax1.grid(True, alpha=0.25)

            err_arr = sp_arr - fb_arr
            self._ax2.plot(t_arr, err_arr, color="#e67e22", lw=1.2)
            self._ax2.axhline(0, color="grey", lw=0.5, linestyle="--")
            self._ax2.set_title("Live  —  Tracking Error  e(t)",
                                 fontsize=10, fontweight="bold")
            self._ax2.set_ylabel("D-counts")
            self._ax2.set_xlabel("Time (s)")
            self._ax2.grid(True, alpha=0.25)

            if len(err_arr) > 5:
                rmse = float(np.sqrt(np.mean(err_arr**2)))
                self._ax1.text(
                    0.02, 0.97,
                    f"RMSE = {rmse:.3f}  |  "
                    f"Kp={self.kp_var.get():.3g}  "
                    f"Ki={self.ki_var.get():.3g}  "
                    f"Kd={self.kd_var.get():.4g}",
                    transform=self._ax1.transAxes, ha="left", va="top",
                    fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor="#ddeeff", alpha=0.85))

            self._fig.tight_layout(pad=1.2)
            self._canvas.draw_idle()

        if self._monitor.last_err:
            self.status_var.set(f"Monitor warning: {self._monitor.last_err}")
            self._monitor.last_err = None

        self._plot_after_id = self.after(
            int(1000 / MONITOR_HZ), self._refresh_live_plot)

    # ─────────────────────────────────────────────────────────────────
    # Connection
    # ─────────────────────────────────────────────────────────────────

    def _connect(self):
        ip = self.ip_var.get().strip()

        if not HAS_MOKU:
            self.conn_status_var.set(
                "moku not installed — simulation mode active")
            self.status_var.set(
                "Running in simulation mode. Click Auto-Tune to continue.")
            self._tune_btn.config(state="normal")
            return

        if not ip:
            messagebox.showwarning("Missing IP",
                                   "Enter the Moku:Go IP address.")
            return

        self._disconnect(silent=True)
        try:
            self.conn_status_var.set(f"Connecting to {ip}...")
            self.update_idletasks()
            self._pid = _MokuPID(ip, force_connect=True)
            self.conn_status_var.set(f"Connected  —  {ip}")
            self.status_var.set(
                "Connected. Click Auto-Tune to begin.")
            self._tune_btn.config(state="normal")
        except Exception as exc:
            self._pid = None
            self.conn_status_var.set("Connection failed")
            messagebox.showerror("Connection failed", str(exc))

    def _disconnect(self, silent=False):
        self._stop_monitor()
        if self._pid is not None:
            try:
                self._pid.relinquish_ownership()
            except Exception:
                pass
            self._pid = None
        self.conn_status_var.set("Not connected")
        if not silent:
            self.status_var.set("Disconnected.")

    # ─────────────────────────────────────────────────────────────────
    # Auto-tune
    # ─────────────────────────────────────────────────────────────────

    def _start_autotune(self):
        if self._auto_thread and self._auto_thread.is_alive():
            self.status_var.set("Auto-tune already running...")
            return
        self._stop_monitor()
        self._tune_btn.config(state="disabled")
        self._repush_btn.config(state="disabled")
        self.status_var.set("Auto-tune starting...")

        self._auto_thread = threading.Thread(
            target=self._run_autotune, daemon=True)
        self._auto_thread.start()

    def _run_autotune(self):
        try:
            tuner = _AutoTuner(
                pid        = self._pid,
                channel    = int(self.channel_var.get()),
                freq_hz    = float(self.freq_var.get()),
                offset_d   = float(self.offset_var.get()),
                adc_scale  = float(self.adc_scale_var.get()),
                relay_kp   = float(self.relay_kp_var.get()),
                progress_cb= lambda msg: self.after(
                    0, lambda m=msg: self.status_var.set(m)),
            )
            kp, ki, kd, Tu, Ku = tuner.run()

            def _on_success():
                self.kp_var.set(round(kp, 4))
                self.ki_var.set(round(ki, 4))
                self.kd_var.set(round(kd, 6))
                self._tune_btn.config(state="normal")
                self._repush_btn.config(state="normal")
                self._mon_start_btn.config(state="normal")
                self.status_var.set(
                    f"Auto-tune complete  |  "
                    f"Tu={Tu*1000:.1f} ms  Ku={Ku:.3f}  =>  "
                    f"Kp={kp:.3g}  Ki={ki:.3g}  Kd={kd:.4g}  "
                    f"{'[pushed to Moku hardware]' if self._pid else '[simulation]'}  "
                    f"—  click Start Monitor to watch live")
                self._draw_preview(kp, ki, kd)

            self.after(0, _on_success)

        except Exception as exc:
            msg = str(exc)
            self.after(0, lambda: [
                self.status_var.set(f"Auto-tune failed: {msg}"),
                self._tune_btn.config(state="normal"),
                messagebox.showerror("Auto-tune failed", msg),
            ])

    # ─────────────────────────────────────────────────────────────────
    # Re-push gains manually
    # ─────────────────────────────────────────────────────────────────

    def _repush_gains(self):
        kp = float(self.kp_var.get())
        ki = float(self.ki_var.get())
        kd = float(self.kd_var.get())

        if self._pid is None:
            self.status_var.set(
                f"Simulation mode — gains set to "
                f"Kp={kp:.3g}  Ki={ki:.3g}  Kd={kd:.4g}")
            return

        try:
            try:
                self._pid.set_by_gain(
                    channel=int(self.channel_var.get()),
                    prop_gain=kp, int_gain=ki, diff_gain=kd)
            except Exception:
                self._pid.set_control_loop_parameters(
                    channel=int(self.channel_var.get()),
                    prop_gain=kp, int_gain=ki, diff_gain=kd)
            self.status_var.set(
                f"Gains pushed  —  "
                f"Kp={kp:.3g}  Ki={ki:.3g}  Kd={kd:.4g}")
        except Exception as e:
            messagebox.showerror("Push failed", str(e))

    # ─────────────────────────────────────────────────────────────────
    # Live monitor
    # ─────────────────────────────────────────────────────────────────

    def _start_monitor(self):
        if self._monitor is not None:
            return
        self._monitor = _MonitorThread(
            pid       = self._pid,
            channel   = int(self.channel_var.get()),
            adc_scale = float(self.adc_scale_var.get()),
            waveform  = self.waveform_var.get(),
            freq_hz   = float(self.freq_var.get()),
            amp       = float(self.amp_var.get()),
            offset_d  = float(self.offset_var.get()),
            kp        = float(self.kp_var.get()),
            ki        = float(self.ki_var.get()),
            kd        = float(self.kd_var.get()),
        )
        self._monitor.start()
        self.status_var.set(
            f"Monitoring live  "
            f"({'hardware' if self._pid else 'simulation'} mode)")
        self._refresh_live_plot()

    def _stop_monitor(self):
        if self._plot_after_id:
            self.after_cancel(self._plot_after_id)
            self._plot_after_id = None
        if self._monitor:
            self._monitor.stop()
            self._monitor = None
        self.status_var.set("Monitor stopped.")

    # ─────────────────────────────────────────────────────────────────
    def destroy(self):
        self._stop_monitor()
        self._disconnect(silent=True)
        super().destroy()
