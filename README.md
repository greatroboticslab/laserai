# Laser Lab Control — Setup & Usage Guide

## Files You Need

Replace / add these files in your project folder:

| File | What it does |
|------|-------------|
| `app.py` | Main entry point — run this |
| `pid_control.py` | New PID Closed-Loop tab |
| `moku_waveform.py` | Updated Moku waveform tab |
| `moku_diagnostic.py` | Run this FIRST on the moku laptop |

Keep all your existing files (`display.py`, `record_data.py`, `process_raw.py`, `moku_data/`).

---

## Step 1 — Install packages (moku laptop only)

```bash
pip install ttkbootstrap matplotlib numpy scipy moku
```

Verify:

```bash
python -c "from moku.instruments import PIDController; print('OK')"
```

---

## Step 2 — Run the diagnostic FIRST

Before running `app.py`, run this once with the Moku connected:

```bash
python moku_diagnostic.py
```

This tells you the **exact key names** your firmware uses in `get_data()` and confirms which gain-setter method exists. The script will print something like:

```
Keys in response:
  'ch1' : list/array  len=1024  first_val=0.0023

>>> IMPORTANT — copy this into pid_control.py:
    ch = data['ch1']
```

`pid_control.py` now auto-discovers these keys at runtime, so you should **not need to edit anything**. But if auto-tune times out or gives wrong readings, the diagnostic output tells you exactly what to fix.

---

## Step 3 — Wire the hardware

```
Moku:Go Output 1  ──►  Piezo amplifier input
Piezo sensor out  ──►  Moku:Go Input 1
```

Both connections must be made before running Auto-Tune.

---

## Step 4 — Run the app

```bash
python app.py
```

Connect your laptop to the MokuGo Wi-Fi (e.g. `MokuGo-003703`) first.
Default IP: `192.168.73.1`

---

## Step 5 — Use the PID Closed-Loop tab

The tab has three steps clearly labelled:

### Step 1 — Connect

Enter the IP and click **Connect**. The status line confirms the connection.

If `moku` is not installed the tab still works in simulation mode — useful for offline demo.

### Step 2 — Set parameters (before Auto-Tune)

| Field | What to set |
|-------|------------|
| Waveform | Sine / Square / Noise/Static |
| Frequency | Your target frequency in Hz |
| Amplitude | Expected motion range in D-counts |
| Offset | DC offset (0 if centred) |
| ADC scale | D-counts per Volt from your sensor datasheet. Start with `1.0` if unknown |
| Relay Kp | Leave at `80`. Increase to `150` if auto-tune times out |
| Channel | `1` unless your sensor is on channel 2 |

### Step 3 — Click Auto-Tune

This runs for ~15 seconds automatically:

1. Sets a very high proportional gain (acts like a bang-bang relay)
2. Watches the piezo oscillate naturally
3. Measures the oscillation period and amplitude
4. Computes Kp, Ki, Kd using Ziegler-Nichols formulas
5. Pushes the gains to the Moku hardware immediately

The Moku then runs the closed-loop at MHz speed — no Python in the path.

After auto-tune the plot shows a simulation preview of Before vs After so you can see the expected improvement.

### Step 4 — Click Start Monitor

Shows the live sensor feedback from the Moku. The top panel shows setpoint vs actual position; the bottom shows tracking error e(t).

---

## What to watch during Auto-Tune

| What you see | What it means |
|-------------|--------------|
| "Oscillating (1/6 cycles)" counting up | Working correctly — wait |
| Counter stops or never starts | Relay Kp too small, or wiring issue |
| "Timed out after 30 s" | Increase Relay Kp to 150 or check ADC scale |
| Gains computed and pushed | Done — Moku is now in closed-loop |
| Very large Kp/Ki numbers | ADC scale is too small — increase it |
| Very small Kp numbers (< 0.01) | ADC scale is too large — decrease it |

---

## If Auto-Tune fails

**Timeout (no oscillation detected)**
- Check hardware wiring — Input 1 must be the sensor, Output 1 must be the amp
- Increase Relay Kp from 80 to 150 or 200
- Check ADC scale matches your sensor

**Wrong gain values (system unstable after tuning)**
- Likely ADC scale is off — run `moku_diagnostic.py` to see raw voltage values
- Try ADC scale = peak sensor voltage / peak D-count amplitude
- You can manually adjust Kp/Ki/Kd in the Computed Gains fields and click **Re-Push Gains**

**`set_by_gain` or `set_control_loop_parameters` not found**
- Run `moku_diagnostic.py` — it lists all available methods
- Paste the output and the exact method name can be patched in

---

## Re-tuning later

You can re-run Auto-Tune as many times as needed. Each run overwrites the previous gains. You can also manually edit Kp/Ki/Kd in the Computed Gains section and click **Re-Push Gains** to apply them without running the full relay test.

---

## Suggested starting gains (if you skip Auto-Tune)

| Waveform | Freq range | Kp | Ki | Kd |
|----------|-----------|----|----|-----|
| Sine | 1–100 Hz | 1.2 | 15.0 | 0.005 |
| Square | 100–400 Hz | 0.6 | 30.0 | 0.002 |
| Noise/Static | DC | 0.5 | 45.0 | 0.010 |

---

## Quick command reference

```bash
# Run diagnostic (moku laptop, Moku connected)
python moku_diagnostic.py

# Run diagnostic with custom IP
python moku_diagnostic.py 192.168.1.xx

# Run the app
python app.py
```
