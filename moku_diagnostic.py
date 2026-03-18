"""
moku_diagnostic.py
==================
Run this FIRST on the moku laptop before running app.py.

It tells you exactly:
  - Which methods exist on your firmware for setting PID gains
  - What keys get_data() actually returns
  - Which key names to use

Usage:
  python moku_diagnostic.py
  python moku_diagnostic.py 192.168.1.xx   (custom IP)
"""

import sys
import json

IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.73.1"

print(f"\n{'='*60}")
print(f"  Moku:Go Diagnostic")
print(f"  IP: {IP}")
print(f"{'='*60}\n")

# ── 1. Check moku package ────────────────────────────────────────────
try:
    from moku.instruments import PIDController
    print("[OK] moku package found")
except ImportError:
    print("[FAIL] moku package not installed")
    print("       Run:  pip install moku")
    sys.exit(1)

# ── 2. Connect ───────────────────────────────────────────────────────
print(f"\nConnecting to {IP} ...")
try:
    pid = PIDController(IP, force_connect=True)
    print(f"[OK] Connected\n")
except Exception as e:
    print(f"[FAIL] Could not connect: {e}")
    print("\nCheck:")
    print("  - Moku:Go is powered on")
    print("  - Your laptop is on the MokuGo Wi-Fi")
    print("  - IP is correct (default hotspot = 192.168.73.1)")
    sys.exit(1)

# ── 3. List all methods ──────────────────────────────────────────────
all_methods = [m for m in dir(pid) if not m.startswith("_")]
print("Available methods on PIDController:")
for m in all_methods:
    print(f"  {m}")

# ── 4. Check which gain-setter exists ────────────────────────────────
print("\nGain-setter detection:")
if hasattr(pid, "set_by_gain"):
    print("  [FOUND] set_by_gain()")
    print("          --> pid_control.py will use this")
elif hasattr(pid, "set_control_loop_parameters"):
    print("  [FOUND] set_control_loop_parameters()")
    print("          --> pid_control.py will use this as fallback")
else:
    print("  [WARNING] Neither set_by_gain nor set_control_loop_parameters found!")
    print("  These methods exist — pick the correct one:")
    gain_candidates = [m for m in all_methods if any(
        x in m.lower() for x in ["gain", "pid", "param", "control", "loop"])]
    for m in gain_candidates:
        print(f"    {m}")

# ── 5. Call get_data() and show exact keys ───────────────────────────
print("\nCalling get_data() ...")
try:
    data = pid.get_data()
    print(f"[OK] get_data() returned {type(data).__name__}")
    print(f"\nKeys in response:")
    if isinstance(data, dict):
        for k, v in data.items():
            if hasattr(v, "__len__"):
                print(f"  '{k}' : list/array  len={len(v)}  "
                      f"first_val={v[0] if len(v) > 0 else 'empty'}")
            else:
                print(f"  '{k}' : {type(v).__name__}  value={v}")
    else:
        print(f"  (Not a dict — raw value: {data})")

    # Tell them exactly what key to use in pid_control.py
    print("\n>>> IMPORTANT — copy this into pid_control.py _AutoTuner._hw_read():")
    if isinstance(data, dict):
        first_key = list(data.keys())[0]
        print(f"    ch = data['{first_key}']")
        print(f"    (First key in response = '{first_key}')")
    print()

except Exception as e:
    print(f"[FAIL] get_data() error: {e}")

# ── 6. Check relinquish_ownership ────────────────────────────────────
print("Checking cleanup methods:")
if hasattr(pid, "relinquish_ownership"):
    print("  [FOUND] relinquish_ownership()")
else:
    print("  [MISSING] relinquish_ownership() — disconnect may not clean up properly")
    close_candidates = [m for m in all_methods if any(
        x in m.lower() for x in ["close", "release", "disconnect", "relinquish"])]
    if close_candidates:
        print(f"  Alternatives: {close_candidates}")

# ── 7. Cleanup ───────────────────────────────────────────────────────
try:
    pid.relinquish_ownership()
    print("\n[OK] Disconnected cleanly")
except Exception:
    pass

print(f"\n{'='*60}")
print("  Diagnostic complete.")
print("  Share the output above if you need help fixing pid_control.py")
print(f"{'='*60}\n")
