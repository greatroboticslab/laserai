"""
pid_autotune.py  —  PID Autotuner + Closed-Loop Controller  (LaserLab v5)
==========================================================================
Two modes:

1. AUTOTUNE (relay-feedback, Astrom-Hagglund 1984)
   - Injects a relay signal into the WG offset
   - Measures resulting oscillation to find Ku (ultimate gain) and Pu (period)
   - Computes Ziegler-Nichols PID gains per waveform type

2. CLOSED-LOOP (software PID using interferometer feedback)
   - Reads live displacement from interferometer (via display_tab.last_nm)
   - Computes error = setpoint - displacement
   - Adjusts WG offset in real time to drive error toward zero
   - Uses the Kp/Ki/Kd gains found by autotune

Signal path (closed-loop running):
   interferometer → error = setpoint - nm → software PID → WG offset → PZT
         ↑___________________________________________________________|

Waveform recommendations:
   Sine   → PID  (standard ZN)
   Square → PI   (avoid step overshoot)
   Ramp   → PID  (integrator removes ramp error)
   Pulse  → PI   (fast response, no ringing)
   Noise  → P    (no integrator windup)
"""

import math
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _mean(lst):
    return sum(lst) / len(lst) if lst else 0.0

def _clip(v, lo, hi):
    return max(lo, min(hi, v))

def _lin_to_db(x):
    return 20.0 * math.log10(max(abs(x), 1e-12))


_WAVE_ZN_MODE = {
    "Sine":   "pid",
    "Square": "pi",
    "Ramp":   "pid",
    "Pulse":  "pi",
    "Noise":  "p",
}

_WAVE_ZN_REASON = {
    "Sine":   "Standard ZN PID — optimal for continuous sine tracking",
    "Square": "Conservative PI — avoids overshoot on step transitions",
    "Ramp":   "ZN PID — integrator corrects steady-state ramp error",
    "Pulse":  "Conservative PI — fast response, minimal ringing",
    "Noise":  "P-only — no integrator to wind up on random excitation",
}

_NOISE_TUNE_FREQ = 10.0  # Hz — used during relay test when waveform is Noise


# ─────────────────────────────────────────────────────────────────────────────
# Relay-feedback autotuner
# ─────────────────────────────────────────────────────────────────────────────
class RelayAutotuner:
    """Astrom-Hagglund (1984) relay-feedback identification."""

    def __init__(self, relay_amp_nm=200.0, n_cycles=8, dt=0.001):
        self.relay_amp = relay_amp_nm
        self.n_cycles  = n_cycles
        self.dt        = dt
        self.reset()

    def reset(self):
        self._relay       = +self.relay_amp
        self._peaks       = []
        self._t           = 0.0
        self._wc          = 300   # 300 ms warmup — enough to measure operating point
        self._wn          = 0
        self._warmup_sum  = 0.0
        self._op_point    = 0.0   # mean displacement measured during warmup
        self._prev        = 0.0
        self._prev_s      = 0
        self.done         = False
        self.Ku           = None
        self.Pu           = None

    def feed(self, measured):
        self._t += self.dt

        # Warmup: accumulate samples to find operating point
        if self._wn < self._wc:
            self._wn += 1
            self._warmup_sum += measured
            if self._wn == self._wc:
                self._op_point = self._warmup_sum / self._wc
            return self._relay

        # Center measurement around operating point so relay
        # detects crossings relative to where the system actually sits,
        # not relative to absolute zero.
        centered = measured - self._op_point

        s = 1 if centered >= 0.0 else -1
        if s != self._prev_s and self._prev_s != 0:
            self._peaks.append((self._t, abs(self._prev)))
            self._relay = -self._relay

        self._prev_s = s
        self._prev   = centered

        if len(self._peaks) >= self.n_cycles * 2:
            self._compute()

        return self._relay

    def _compute(self):
        pk      = self._peaks[-self.n_cycles * 2:]
        ts      = [p[0] for p in pk]
        amps    = [p[1] for p in pk]
        periods = [ts[i + 2] - ts[i] for i in range(len(ts) - 2)]
        if not periods:
            return
        self.Pu = _mean(periods)
        Ac      = _mean(amps)
        if Ac > 0.0 and self.Pu > 0.0:
            self.Ku   = (4.0 * self.relay_amp) / (math.pi * Ac)
            self.done = True

    def zn_gains(self, mode="pid"):
        if not self.done:
            raise RuntimeError("Autotune not complete.")
        Ku, Pu = self.Ku, self.Pu
        if mode == "pid":
            Kp = 0.60 * Ku
            Ti = 0.50 * Pu
            Td = 0.12 * Pu
            Ki = Kp / Ti
            Kd = Kp * Td
        elif mode == "pi":
            Kp = 0.45 * Ku
            Ti = 0.83 * Pu
            Ki = Kp / Ti
            Kd = 0.0
        else:
            Kp = 0.50 * Ku
            Ki = 0.0
            Kd = 0.0
        return Kp, Ki, Kd


# ─────────────────────────────────────────────────────────────────────────────
# Software PID (runs continuously during closed-loop mode)
# ─────────────────────────────────────────────────────────────────────────────
class SoftwarePID:
    """
    Discrete-time PID controller with anti-windup.
    error  : setpoint_nm - measured_nm
    output : correction in nm  (divide by sensitivity to get Volts)
    """

    def __init__(self, Kp, Ki, Kd, dt=0.001, max_output_nm=500.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.max_output = max_output_nm
        self.reset()

    def reset(self):
        self._integral  = 0.0
        self._prev_error = 0.0

    def update(self, error):
        self._integral += error * self.dt

        # anti-windup: clip integral so Ki contribution stays within ±max_output
        if self.Ki > 0:
            self._integral = _clip(
                self._integral,
                -self.max_output / self.Ki,
                self.max_output / self.Ki,
            )

        derivative = (error - self._prev_error) / self.dt
        output = (self.Kp * error
                  + self.Ki * self._integral
                  + self.Kd * derivative)
        self._prev_error = error
        return _clip(output, -self.max_output, self.max_output)


# ─────────────────────────────────────────────────────────────────────────────
# Autotune + Closed-Loop GUI tab
# ─────────────────────────────────────────────────────────────────────────────
class AutotuneTab(ttk.Frame):

    def __init__(self, parent, moku_tab, display_tab):
        super().__init__(parent, padding=14)
        self.moku_tab    = moku_tab
        self.display_tab = display_tab

        # autotune state
        self._tuner       = None
        self._running     = False
        self._thread      = None
        self._result      = None
        self._was_noise   = False
        self._active_wave = "Sine"

        # closed-loop state
        self._cl_running  = False
        self._cl_thread   = None

        self._log_q = queue.Queue()

        self._build_ui()
        self._poll_log()

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        r = 0
        ttk.Label(
            self,
            text="PID Autotune  —  Relay-Feedback (Astrom-Hagglund)",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=r, column=0, columnspan=6, sticky="w", pady=(0, 8))

        # recommendation
        r += 1
        wf = ttk.LabelFrame(self, text="  Waveform Mode Recommendation  ", padding=8)
        wf.grid(row=r, column=0, columnspan=6, sticky="ew", pady=(0, 8))
        self._rec_var = tk.StringVar(value="Click 'Refresh' to see recommendation.")
        ttk.Label(wf, textvariable=self._rec_var, foreground="#1A5276",
                  font=("Segoe UI", 10), justify="left").pack(side="left", anchor="w")
        ttk.Button(wf, text="Refresh", bootstyle=SECONDARY,
                   command=self._refresh_recommendation).pack(side="left", padx=(12, 0))

        # parameters
        r += 1
        pf = ttk.LabelFrame(self, text="Autotune Parameters", padding=8)
        pf.grid(row=r, column=0, columnspan=6, sticky="ew", pady=(0, 8))

        self._v_relay  = tk.DoubleVar(value=200.0)
        self._v_cycles = tk.IntVar(value=8)
        self._v_sens   = tk.DoubleVar(value=100.0)
        self._v_mode   = tk.StringVar(value="pid")

        for i, (lbl, var, tip) in enumerate([
            ("Relay amplitude (nm):", self._v_relay,
             "Must be > ~80 nm.  Increase if peaks never grow."),
            ("Cycles to measure:", self._v_cycles,
             "8 is standard.  Use 12 for noisy systems."),
            ("PZT sensitivity (nm/V):", self._v_sens,
             "nm per volt of WG offset.  Typical: 50–200 nm/V."),
        ]):
            ttk.Label(pf, text=lbl).grid(row=i, column=0, sticky="e",
                                          padx=(0, 4), pady=2)
            ttk.Entry(pf, textvariable=var, width=10).grid(row=i, column=1,
                                                            sticky="w", pady=2)
            ttk.Label(pf, text=tip, foreground="grey",
                      font=("Segoe UI", 8)).grid(row=i, column=2, sticky="w",
                                                  padx=(8, 0), pady=2)

        ttk.Label(pf, text="Tune mode:").grid(row=3, column=0, sticky="e",
                                               padx=(0, 4), pady=2)
        mf = ttk.Frame(pf)
        mf.grid(row=3, column=1, columnspan=2, sticky="w")
        for txt, val in [("PID (standard)", "pid"),
                         ("PI  (conservative)", "pi"),
                         ("P only", "p")]:
            ttk.Radiobutton(mf, text=txt, value=val,
                            variable=self._v_mode).pack(side="left", padx=(0, 10))

        # result
        r += 1
        rf = ttk.LabelFrame(self, text="Autotune Result", padding=8)
        rf.grid(row=r, column=0, columnspan=6, sticky="ew", pady=(0, 8))

        self._sv = {k: tk.StringVar(value="--")
                    for k in ["Ku", "Pu", "Kp", "Ki", "Kd",
                               "hw_kp", "hw_ki", "hw_fi"]}

        for col, (lbl, key) in enumerate([("Ku (ultimate gain):", "Ku"),
                                           ("Pu (ultimate period):", "Pu")]):
            ttk.Label(rf, text=lbl).grid(row=0, column=col*2, sticky="e", padx=(0, 4))
            ttk.Label(rf, textvariable=self._sv[key],
                      font=("Segoe UI", 10, "bold"),
                      foreground="#1A5276").grid(row=0, column=col*2+1,
                                                  sticky="w", padx=(0, 20))

        ttk.Label(rf, text="Software PID ->").grid(row=1, column=0,
                                                    sticky="e", padx=(0, 4))
        for col, (lbl, key) in enumerate([("Kp:", "Kp"), ("Ki:", "Ki"), ("Kd:", "Kd")]):
            ttk.Label(rf, text=lbl).grid(row=1, column=col*2+1,
                                          sticky="e", padx=(0, 2))
            ttk.Label(rf, textvariable=self._sv[key],
                      font=("Segoe UI", 10, "bold"),
                      foreground="#1A5276").grid(row=1, column=col*2+2,
                                                  sticky="w", padx=(0, 12))

        ttk.Label(rf, text="Hardware PID ->").grid(row=2, column=0,
                                                    sticky="e", padx=(0, 4))
        for col, (lbl, key) in enumerate([("Kp (dB):", "hw_kp"),
                                           ("Ki (dB):", "hw_ki"),
                                           ("fi (Hz):", "hw_fi")]):
            ttk.Label(rf, text=lbl).grid(row=2, column=col*2+1,
                                          sticky="e", padx=(0, 2))
            ttk.Label(rf, textvariable=self._sv[key],
                      font=("Segoe UI", 10, "bold"),
                      foreground="#117A65").grid(row=2, column=col*2+2,
                                                  sticky="w", padx=(0, 12))

        # autotune buttons
        r += 1
        bf = ttk.Frame(self)
        bf.grid(row=r, column=0, columnspan=6, sticky="w", pady=(0, 6))

        self._btn_start = ttk.Button(bf, text="Start Autotune",
                                     bootstyle=SUCCESS, command=self._start)
        self._btn_start.pack(side="left", padx=(0, 8))

        self._btn_stop = ttk.Button(bf, text="Stop",
                                    bootstyle=DANGER, command=self._stop,
                                    state="disabled")
        self._btn_stop.pack(side="left", padx=(0, 8))

        self._btn_apply = ttk.Button(bf, text="Apply to Moku:Go",
                                     bootstyle=PRIMARY, command=self._apply,
                                     state="disabled")
        self._btn_apply.pack(side="left")

        # progress bar
        r += 1
        self._pb = ttk.Progressbar(self, mode="indeterminate")
        self._pb.grid(row=r, column=0, columnspan=6, sticky="ew", pady=(0, 8))

        # ── Closed-loop section ───────────────────────────────────────────────
        r += 1
        clf = ttk.LabelFrame(self, text="  Closed-Loop Control  ", padding=8)
        clf.grid(row=r, column=0, columnspan=6, sticky="ew", pady=(0, 8))

        ttk.Label(
            clf,
            text=(
                "Reads live interferometer displacement and adjusts WG offset\n"
                "to keep displacement at the setpoint. Run autotune first."
            ),
            foreground="grey",
            font=("Segoe UI", 9),
            justify="left",
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 6))

        ttk.Label(clf, text="Offset from lock point (nm):").grid(row=1, column=0,
                                                                   sticky="e", padx=(0, 4))
        self._v_setpoint = tk.DoubleVar(value=0.0)
        ttk.Entry(clf, textvariable=self._v_setpoint, width=10).grid(row=1, column=1,
                                                                       sticky="w")
        ttk.Label(clf, text="0 = stay at current position when loop starts",
                  foreground="grey",
                  font=("Segoe UI", 8)).grid(row=1, column=2, sticky="w", padx=(8, 0))

        self._cl_status_var = tk.StringVar(value="Idle")
        ttk.Label(clf, text="Status:").grid(row=2, column=0, sticky="e",
                                             padx=(0, 4), pady=(4, 0))
        ttk.Label(clf, textvariable=self._cl_status_var,
                  font=("Segoe UI", 10, "bold"),
                  foreground="#117A65").grid(row=2, column=1, columnspan=3,
                                             sticky="w", pady=(4, 0))

        cl_bf = ttk.Frame(clf)
        cl_bf.grid(row=3, column=0, columnspan=6, sticky="w", pady=(6, 0))

        self._btn_cl_start = ttk.Button(cl_bf, text="Run Closed-Loop",
                                        bootstyle=SUCCESS,
                                        command=self._start_closed_loop)
        self._btn_cl_start.pack(side="left", padx=(0, 8))

        self._btn_cl_stop = ttk.Button(cl_bf, text="Stop Closed-Loop",
                                       bootstyle=DANGER,
                                       command=self._stop_closed_loop,
                                       state="disabled")
        self._btn_cl_stop.pack(side="left")

        # log
        r += 1
        self._log_w = tk.Text(self, height=10, state="disabled",
                              font=("Consolas", 9), relief="flat",
                              background="#F4F7FC")
        self._log_w.grid(row=r, column=0, columnspan=6, sticky="nsew")
        self.rowconfigure(r, weight=1)
        for c in range(6):
            self.columnconfigure(c, weight=1)

        self._log("Ready.  Run autotune first, then use Closed-Loop Control.")
        self._log("Tip: WG amplitude >= 5 Vpp so displacement covers 60+ fringe counts.")

    # ── recommendation ────────────────────────────────────────────────────────
    def _refresh_recommendation(self):
        try:
            wave = self.moku_tab.wave_type_var.get().strip()
        except Exception:
            wave = "Sine"
        mode   = _WAVE_ZN_MODE.get(wave, "pid")
        reason = _WAVE_ZN_REASON.get(wave, "")
        self._rec_var.set(
            f"Waveform: {wave}  →  Recommended mode: {mode.upper()}\n{reason}"
        )
        self._v_mode.set(mode)
        self._log(f"Mode auto-set to '{mode}' for {wave}.  {reason}")

    # ── logging ───────────────────────────────────────────────────────────────
    def _log(self, msg):
        self._log_q.put(f"[{time.strftime('%H:%M:%S')}]  {msg}\n")

    def _poll_log(self):
        while not self._log_q.empty():
            m = self._log_q.get_nowait()
            self._log_w.configure(state="normal")
            self._log_w.insert("end", m)
            self._log_w.see("end")
            self._log_w.configure(state="disabled")
        self.after(100, self._poll_log)

    # ── autotune start / stop ─────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return
        if not self.moku_tab.is_connected():
            messagebox.showwarning("Not connected",
                                   "Connect to Moku:Go first (Waveform tab).")
            return
        if self._get_nm() is None:
            messagebox.showwarning("No data",
                                   "No displacement received.\n"
                                   "Open uMD GUI tab and confirm streaming.")
            return

        try:
            wave = self.moku_tab.wave_type_var.get().strip()
        except Exception:
            wave = "Sine"

        self._active_wave = wave
        self._was_noise   = (wave == "Noise")

        recommended = _WAVE_ZN_MODE.get(wave, "pid")
        self._v_mode.set(recommended)
        self._log(f"Waveform: {wave}  →  mode auto-set to '{recommended}'.")
        if self._was_noise:
            self._log("Noise detected: switching to 10 Hz Sine for relay test, "
                      "will restore Noise when done.")

        self._running = True
        self._result  = None
        self._tuner   = RelayAutotuner(
            relay_amp_nm=float(self._v_relay.get()),
            n_cycles=int(self._v_cycles.get()),
        )

        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._btn_apply.config(state="disabled")
        self._pb.start(10)

        self._log(f"Autotune started: relay={self._v_relay.get():.0f} nm  "
                  f"cycles={self._v_cycles.get()}  mode={recommended}")
        self._thread = threading.Thread(target=self._autotune_worker, daemon=True)
        self._thread.start()

    def _stop(self):
        self._running = False
        self._pb.stop()
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled")
        self._restore_waveform()
        self._log("Autotune stopped.  WG restored.")

    # ── autotune worker ───────────────────────────────────────────────────────
    def _autotune_worker(self):
        try:
            orig_offset = float(self.moku_tab.offset_var.get())
        except Exception:
            orig_offset = 0.0

        sens = max(1.0, float(self._v_sens.get()))
        dt   = 0.001
        ctr  = 0

        if self._was_noise:
            try:
                wg = self.moku_tab._wg
                if wg:
                    wg.generate_waveform(
                        channel=int(self.moku_tab.channel_var.get()),
                        type="Sine",
                        amplitude=float(self.moku_tab.amplitude_var.get()),
                        frequency=_NOISE_TUNE_FREQ,
                        offset=0.0,
                        phase=0.0,
                    )
            except Exception as e:
                self._log(f"Sine switch error: {e}")

        while self._running:
            t0 = time.perf_counter()

            nm       = self._get_nm() or 0.0
            relay_nm = self._tuner.feed(nm)
            relay_v  = _clip(relay_nm / sens, -4.5, 4.5)
            new_off  = _clip(orig_offset + relay_v, -5.0, 5.0)

            try:
                self._push_wg_offset(new_off, wave_type=self._active_wave)
            except Exception as e:
                self._log(f"WG error: {e}")

            ctr += 1
            if ctr % 500 == 0:
                peaks_found = len(self._tuner._peaks)
                if self._tuner._wn < self._tuner._wc:
                    self._log(f"  Warmup... measuring operating point  nm={nm:.1f}")
                elif peaks_found == 0:
                    self._log(
                        f"  Waiting for first zero-crossing...  "
                        f"nm={nm:.1f}  op_point={self._tuner._op_point:.1f}  "
                        f"centered={nm - self._tuner._op_point:.1f}  relay={relay_nm:.1f}"
                    )
                else:
                    self._log(
                        f"  nm={nm:.1f}  relay={relay_nm:.1f}  "
                        f"peaks={peaks_found}/{self._tuner.n_cycles*2}"
                    )

            if self._tuner.done:
                self._restore_waveform(orig_offset)
                self.after(0, self._on_autotune_done)
                break

            time.sleep(max(0.0, dt - (time.perf_counter() - t0)))

        self._running = False
        self.after(0, lambda: self._pb.stop())
        self.after(0, lambda: self._btn_start.config(state="normal"))
        self.after(0, lambda: self._btn_stop.config(state="disabled"))

    def _on_autotune_done(self):
        t = self._tuner
        Ku, Pu      = t.Ku, t.Pu
        Kp, Ki, Kd  = t.zn_gains(self._v_mode.get())

        hw_kp  = _lin_to_db(abs(Kp))
        ki_lin = abs(Ki / max(abs(Kp), 1e-9))
        hw_ki  = _lin_to_db(ki_lin) if Ki != 0.0 else -60.0
        hw_fi  = ki_lin / (2.0 * math.pi) if Ki != 0.0 else 0.0

        self._sv["Ku"].set(f"{Ku:.4f}")
        self._sv["Pu"].set(f"{Pu:.4f} s ({1/Pu:.2f} Hz)")
        self._sv["Kp"].set(f"{Kp:.5f}")
        self._sv["Ki"].set(f"{Ki:.5f}")
        self._sv["Kd"].set(f"{Kd:.7f}")
        self._sv["hw_kp"].set(f"{hw_kp:.1f}")
        self._sv["hw_ki"].set(f"{hw_ki:.1f}" if Ki != 0.0 else "off")
        self._sv["hw_fi"].set(f"{hw_fi:.2f}" if Ki != 0.0 else "off")

        self._result = dict(Kp=Kp, Ki=Ki, Kd=Kd,
                            hw_kp=hw_kp,
                            hw_ki=hw_ki if Ki != 0.0 else 0.0,
                            hw_fi=hw_fi)

        self._log(f"Autotune done!  Ku={Ku:.4f}  Pu={Pu:.4f}s")
        self._log(f"  Kp={Kp:.5f}  Ki={Ki:.5f}  Kd={Kd:.7f}")
        if Ki != 0.0:
            self._log(f"  HW PID: Kp={hw_kp:.1f}dB  Ki={hw_ki:.1f}dB  fi={hw_fi:.2f}Hz")
        else:
            self._log(f"  HW PID: Kp={hw_kp:.1f}dB  (P-only)")
        self._log("Ready to apply gains or run closed-loop control.")
        self._btn_apply.config(state="normal")

    # ── apply hardware gains ──────────────────────────────────────────────────
    def _apply(self):
        if not self._result:
            return
        r     = self._result
        hw_kp = _clip(r["hw_kp"], -60, 60)
        hw_ki = _clip(r["hw_ki"], -60, 60)
        hw_fi = r["hw_fi"]

        try:
            if not self.moku_tab.is_connected():
                raise RuntimeError("Moku:Go not connected.")

            self.moku_tab.prop_gain_var.set(round(hw_kp, 2))
            self.moku_tab.int_gain_var.set(round(hw_ki, 2))
            self.moku_tab.diff_gain_var.set(0.0)
            self.moku_tab.int_corner_var.set(round(hw_fi, 2) if hw_fi > 0 else 0.0)
            self.moku_tab.diff_corner_var.set(100.0)

            if self.moku_tab._pid_active:
                self.moku_tab._push_pid_gains()
                self._log("Gains pushed to live hardware PID.")
            else:
                self._log("Gains written to Moku tab.  Enable PID Smoothing to activate.")

            ki_line = (f"  Int  gain  = {hw_ki:.1f} dB\n  Int corner = {hw_fi:.2f} Hz\n"
                       if hw_fi > 0 else "  Int  gain  = off (P-only)\n")
            messagebox.showinfo(
                "Applied",
                f"PID gains written:\n\n"
                f"  Prop gain  = {hw_kp:.1f} dB\n{ki_line}"
                f"  Diff gain  = 0.0 dB (off)\n\n"
                f"Enable PID Smoothing in the Moku tab if not already on."
            )
        except Exception as e:
            self._log(f"Apply failed: {e}")
            messagebox.showerror("Apply failed", str(e))

    # ── closed-loop start / stop ──────────────────────────────────────────────
    def _start_closed_loop(self):
        if self._cl_running:
            return
        if self._running:
            messagebox.showwarning("Autotune running",
                                   "Stop autotune before starting closed-loop.")
            return
        if not self.moku_tab.is_connected():
            messagebox.showwarning("Not connected",
                                   "Connect to Moku:Go first.")
            return
        if self._get_nm() is None:
            messagebox.showwarning("No data",
                                   "No displacement data.\n"
                                   "Open uMD GUI and confirm streaming.")
            return
        if self._result is None:
            messagebox.showwarning("No gains",
                                   "Run autotune first to get PID gains.")
            return

        wave = self.moku_tab.wave_type_var.get().strip()
        if wave == "Noise":
            messagebox.showwarning("Noise waveform",
                                   "Closed-loop offset control is not supported "
                                   "for Noise waveform.\nSwitch to Sine/Square/Ramp/Pulse.")
            return

        # Record current displacement as the lock point.
        # The setpoint is an offset FROM this lock point, so setpoint=0
        # means "hold exactly where the system is right now".
        current_nm = self._get_nm() or 0.0
        self._cl_lock_point = current_nm

        self._cl_running = True
        self._btn_cl_start.config(state="disabled")
        self._btn_cl_stop.config(state="normal")
        self._btn_start.config(state="disabled")
        self._cl_status_var.set("Running...")

        offset = float(self._v_setpoint.get())
        self._log(f"Closed-loop started.  Lock point = {current_nm:.1f} nm  "
                  f"offset = {offset:+.1f} nm  "
                  f"→ target = {current_nm + offset:.1f} nm")
        self._log(f"  Kp={self._result['Kp']:.4f}  Ki={self._result['Ki']:.4f}  "
                  f"Kd={self._result['Kd']:.6f}")

        self._cl_thread = threading.Thread(target=self._cl_worker, daemon=True)
        self._cl_thread.start()

    def _stop_closed_loop(self):
        self._cl_running = False
        self._cl_status_var.set("Idle")
        self._btn_cl_start.config(state="normal")
        self._btn_cl_stop.config(state="disabled")
        self._btn_start.config(state="normal")
        self._restore_waveform()
        self._log("Closed-loop stopped.  WG offset restored.")

    # ── closed-loop worker ────────────────────────────────────────────────────
    def _cl_worker(self):
        Kp   = self._result["Kp"]
        Ki   = self._result["Ki"]
        Kd   = self._result["Kd"]
        sens = max(1.0, float(self._v_sens.get()))
        dt   = 0.001

        pid = SoftwarePID(Kp, Ki, Kd, dt)

        try:
            orig_offset = float(self.moku_tab.offset_var.get())
        except Exception:
            orig_offset = 0.0

        ctr = 0
        while self._cl_running:
            t0 = time.perf_counter()

            offset     = float(self._v_setpoint.get())
            target     = self._cl_lock_point + offset
            nm         = self._get_nm() or 0.0
            error      = target - nm
            correction = pid.update(error)           # nm
            correction_v = _clip(correction / sens, -4.5, 4.5)
            new_offset  = _clip(orig_offset + correction_v, -5.0, 5.0)

            try:
                self._push_wg_offset(new_offset)
            except Exception as e:
                self._log(f"CL WG error: {e}")

            ctr += 1
            if ctr % 1000 == 0:
                status = (f"nm={nm:.1f}  target={target:.1f}  "
                          f"error={error:.1f}  correction={correction:.1f}nm")
                self._cl_status_var.set(status)  # safe from thread (StringVar is thread-safe)
                self._log(f"  CL: {status}")

            time.sleep(max(0.0, dt - (time.perf_counter() - t0)))

        self._cl_running = False
        self.after(0, lambda: self._btn_cl_start.config(state="normal"))
        self.after(0, lambda: self._btn_cl_stop.config(state="disabled"))
        self.after(0, lambda: self._btn_start.config(state="normal"))
        self.after(0, lambda: self._cl_status_var.set("Idle"))

    # ── WG push helpers ───────────────────────────────────────────────────────
    def _push_wg_offset(self, new_offset, wave_type=None):
        """Push WG with updated offset. Handles all wave types."""
        wg = self.moku_tab._wg
        if not wg:
            return

        if wave_type is None:
            wave_type = self.moku_tab.wave_type_var.get().strip()

        ch  = int(self.moku_tab.channel_var.get())
        amp = float(self.moku_tab.amplitude_var.get())

        if wave_type == "Noise":
            # Relay test on Noise uses Sine instead
            wg.generate_waveform(
                channel=ch,
                type="Sine",
                amplitude=amp,
                frequency=_NOISE_TUNE_FREQ,
                offset=new_offset,
                phase=0.0,
            )
            return

        kwargs = {
            "channel":   ch,
            "type":      wave_type,
            "amplitude": amp,
            "frequency": float(self.moku_tab.frequency_var.get()),
            "offset":    new_offset,
            "phase":     float(self.moku_tab.phase_var.get()),
        }

        if wave_type == "Square":
            kwargs["duty"] = float(self.moku_tab.duty_var.get())
        elif wave_type == "Ramp":
            kwargs["symmetry"] = float(self.moku_tab.symmetry_var.get())
        elif wave_type == "Pulse":
            kwargs["pulse_width"] = float(self.moku_tab.pulse_width_var.get())
            kwargs["edge_time"]   = float(self.moku_tab.edge_time_var.get())

        wg.generate_waveform(**kwargs)

    def _restore_waveform(self, offset=None):
        """Restore original waveform after autotune or closed-loop."""
        try:
            wg = self.moku_tab._wg
            if not wg:
                return

            wave = self.moku_tab.wave_type_var.get().strip()
            ch   = int(self.moku_tab.channel_var.get())
            amp  = float(self.moku_tab.amplitude_var.get())

            if wave == "Noise":
                wg.generate_waveform(channel=ch, type="Noise", amplitude=amp)
                return

            off = offset if offset is not None else float(self.moku_tab.offset_var.get())

            kwargs = {
                "channel":   ch,
                "type":      wave,
                "amplitude": amp,
                "frequency": float(self.moku_tab.frequency_var.get()),
                "offset":    off,
                "phase":     float(self.moku_tab.phase_var.get()),
            }

            if wave == "Square":
                kwargs["duty"] = float(self.moku_tab.duty_var.get())
            elif wave == "Ramp":
                kwargs["symmetry"] = float(self.moku_tab.symmetry_var.get())
            elif wave == "Pulse":
                kwargs["pulse_width"] = float(self.moku_tab.pulse_width_var.get())
                kwargs["edge_time"]   = float(self.moku_tab.edge_time_var.get())

            wg.generate_waveform(**kwargs)
        except Exception:
            pass

    # ── helpers ───────────────────────────────────────────────────────────────
    def _get_nm(self):
        for attr in ("last_nm", "latest_nm", "displacement_nm",
                     "_latest_nm", "last_displacement", "current_nm"):
            try:
                v = getattr(self.display_tab, attr, None)
                if v is not None:
                    return float(v)
            except Exception:
                pass
        return None
