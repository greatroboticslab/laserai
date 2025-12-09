# display.py
#
# - Launches external uMD_GUI.exe (VB app)
# - Ensures a local MQTT broker (mosquitto.exe in broker_mqtt/) is running
#   * On Windows: run mosquitto.exe directly
#   * On WSL: convert path with wslpath -w and run via cmd.exe (just like uMD_GUI.exe)
# - Subscribes to "vb_to_py" and converts raw interferometer data to displacement (nm)
# - Displays latest displacement; ready to be extended with graphs

import os
import sys
import subprocess
import socket
import time
import tkinter as tk
from tkinter import ttk, messagebox

import ttkbootstrap as tb
from ttkbootstrap.constants import *

from collections import deque

import paho.mqtt.client as mqtt

# -------------------------------------------------------------------
# Helpers from process_raw (is_wsl, wsl_to_win_path, raw_to_nm)
# -------------------------------------------------------------------
try:
    from process_raw import is_wsl, wsl_to_win_path, raw_to_nm
except ImportError:
    
    import platform

    def is_wsl() -> bool:
        try:
            rel = platform.release().lower()
            ver = platform.version().lower()
            return ("microsoft" in rel) or ("microsoft" in ver) or os.path.exists(
                "/proc/sys/fs/binfmt_misc/WSLInterop"
            )
        except Exception:
            return False

    def wsl_to_win_path(path: str) -> str:
        return path

    def raw_to_nm(D, wavelength=632.991372, phase=0.0, correction=0.0):
        # (D - phase) * λ/2 - correction  in vb code
        return (D - phase) * (wavelength / 2.0) - correction


# -------------------------------------------------------------------
# MQTT / interferometer config
# -------------------------------------------------------------------
WAVELENGTH_NM = 632.991372
PHASE_SCALE = 256.0          # PhaseValue / 256.0
CORRECTION_NM = 0.0          # Should match CurrentValueCorrection (primary axis) in VB

MQTT_BROKER_HOST = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "vb_to_py"       # VB publishes "refCount,D,phaseRaw" here

MAX_POINTS = 5000             # Points to keep in buffer for plotting
UI_UPDATE_MS = 50             # UI refresh interval (~20 fps)


# -------------------------------------------------------------------
# Local mosquitto broker management (from broker_mqtt/)
# -------------------------------------------------------------------
def _is_port_open(port: int) -> bool:
    """Return True if something is listening on localhost:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((MQTT_BROKER_HOST, port)) == 0


def ensure_broker_running():
    """
    If nothing is listening on MQTT_PORT, try to start the bundled mosquitto
    from the broker_mqtt folder.

    On Windows: run mosquitto.exe directly.
    On WSL: convert Linux path to Windows with wslpath -w and start via cmd.exe.

    Returns a Popen object if we started one, or None if a broker was already
    running or could not be started.
    """
    if _is_port_open(MQTT_PORT):
        print(f"[MQTT] Broker already running on {MQTT_BROKER_HOST}:{MQTT_PORT}")
        return None

    base_dir = os.path.dirname(os.path.abspath(__file__))
    broker_dir_linux = os.path.join(base_dir, "broker_mqtt")
    broker_exe_linux = os.path.join(broker_dir_linux, "mosquitto.exe")

    if not os.path.exists(broker_exe_linux):
        print(f"[MQTT] mosquitto.exe not found at: {broker_exe_linux}")
        return None

    # --------- WSL branch: use wslpath + cmd.exe to run Windows mosquitto.exe ---------
    if is_wsl():
        try:
            # Convert EXE + directory to Windows paths
            result_exe = subprocess.run(
                ["wslpath", "-w", broker_exe_linux],
                capture_output=True,
                text=True,
                check=True
            )
            broker_exe_win = result_exe.stdout.strip()

            result_dir = subprocess.run(
                ["wslpath", "-w", broker_dir_linux],
                capture_output=True,
                text=True,
                check=True
            )
            broker_dir_win = result_dir.stdout.strip()

        except Exception as e:
            print("[MQTT] Failed to translate mosquitto path via wslpath:", e)
            return None

        print("[MQTT] Starting Windows mosquitto broker from WSL...")
        try:
            # Run: cmd.exe /C "mosquitto.exe -p 1883"
            cmd = ["cmd.exe", "/C", f'"{broker_exe_win}" -p {MQTT_PORT}']
            proc = subprocess.Popen(
                cmd,
                cwd=broker_dir_win or None,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print("[MQTT] Failed to start Windows mosquitto via cmd.exe:", e)
            return None

    # --------- Native Windows (or non-WSL) branch ---------
    else:
        print("[MQTT] Starting bundled mosquitto broker (native)...")
        try:
            proc = subprocess.Popen(
                [broker_exe_linux, "-p", str(MQTT_PORT)],
                cwd=broker_dir_linux,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print("[MQTT] Failed to start mosquitto:", e)
            return None

    # awit psuedo
    for _ in range(20):
        time.sleep(0.1)
        if _is_port_open(MQTT_PORT):
            print("[MQTT] Broker started.")
            return proc

    print("[MQTT] Broker did not start in time.")
    return None


# -------------------------------------------------------------------
# DisplayFrame: main UI for launching uMD_GUI + showing displacement
# -------------------------------------------------------------------
class DisplayFrame(ttk.Frame):
    """
    A ttkbootstrap Frame that:
        - Launches / closes uMD_GUI.exe
        - Ensures an MQTT broker is running (bundled mosquitto.exe)
        - Subscribes to uMD_GUI's MQTT data and computes displacement in nm
        - Displays the latest displacement (nm)
    """

    def __init__(self, parent):
        super().__init__(parent, padding=16)


        self.exe_rel_path = os.path.join("umd_gui", "uMD_GUI.exe")
        self.process = None        # uMD_GUI process handle


        self.broker_proc = ensure_broker_running()


        self.mqtt_client = None
        self.data_buffer = deque(maxlen=MAX_POINTS)  
        self.last_nm = None

        self._build_ui()
        self._setup_mqtt()
        self._start_ui_updates()

    # ---------------------------
    # UI
    # ---------------------------
    def _build_ui(self):
        """Builds the display tab UI."""

        title_label = ttk.Label(
            self,
            text="uMD GUI / Displacement Display",
            font=("Helvetica", 16, "bold"),
        )
        title_label.pack(anchor="w", pady=(0, 10))

        tool_frame = ttk.Frame(self)
        tool_frame.pack(fill="both", expand=True)

        ttk.Label(
            tool_frame,
            text="Launch the external uMD GUI and stream live displacement data\n"
                 "over MQTT to this display.",
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        self.status_var = tk.StringVar(value="Status: Not Running")
        ttk.Label(
            tool_frame,
            textvariable=self.status_var,
            bootstyle="inverse-secondary",
        ).pack(anchor="w", pady=(0, 10))

        self.disp_var = tk.StringVar(value="Latest displacement: --- nm")
        ttk.Label(
            tool_frame,
            textvariable=self.disp_var,
            bootstyle="inverse-info",
        ).pack(anchor="w", pady=(0, 10))

        btn_frame = ttk.Frame(tool_frame)
        btn_frame.pack(anchor="w", pady=(10, 0))

        ttk.Button(
            btn_frame,
            text="Launch uMD GUI",
            bootstyle="success",
            command=self._launch_app,
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            btn_frame,
            text="Force Close",
            bootstyle="danger",
            command=self._close_app,
        ).pack(side="left")


    # ---------------------------
    # MQTT
    # ---------------------------
    def _setup_mqtt(self):
        """Create and start the MQTT client."""
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except TypeError:
            # Older paho-mqtt versions
            self.mqtt_client = mqtt.Client()

        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        try:
            self.mqtt_client.connect(MQTT_BROKER_HOST, MQTT_PORT, keepalive=60)
            self.mqtt_client.loop_start()
            print(f"[MQTT] Connecting to {MQTT_BROKER_HOST}:{MQTT_PORT}")
        except Exception as e:
            print("[MQTT] Error connecting to broker:", e)

    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"[MQTT] Connected, code={reason_code}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Subscribed to '{MQTT_TOPIC}'")

    def _on_mqtt_message(self, client, userdata, msg):
        """
        Called whenever a message arrives on vb_to_py.

        Payload format: "refCount,D,phaseRaw"
        """
        try:
            ref_str, d_str, phase_str = msg.payload.decode().split(",")

            D = int(d_str)
            phase_counts = int(phase_str)
        except ValueError:
            print("[MQTT] Bad payload:", msg.payload)
            return

        phase = phase_counts / PHASE_SCALE

        nm = raw_to_nm(
            D,
            wavelength=WAVELENGTH_NM,
            phase=phase,
            correction=CORRECTION_NM,
        )

        self.data_buffer.append(nm)
        self.last_nm = nm

    def _start_ui_updates(self):
        """Periodic UI update; called in the Tk main thread."""
        if self.last_nm is not None:
            self.disp_var.set(f"Latest displacement: {self.last_nm:.3f} nm")


        self.after(UI_UPDATE_MS, self._start_ui_updates)

    # ---------------------------
    # EXE path + process handling
    # ---------------------------
    def _launch_app(self):
        """
        Launch the external uMD_GUI.exe application.

        Uses the same WSL pattern you already had:
          - Build Linux path to uMD_GUI.exe
          - If WSL, convert to Windows path via wslpath -w and launch with explorer.exe
          - Else, run directly on Windows
        """

        linux_path = os.path.abspath(self.exe_rel_path)

        if not os.path.exists(linux_path) and not is_wsl():
            messagebox.showerror("File Not Found", f"Could not find executable at:\n{linux_path}")
            return

        try:
            self.status_var.set("Status: Launching...")

            if is_wsl():
                
                result = subprocess.run(
                    ["wslpath", "-w", linux_path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                win_path = result.stdout.strip()


                subprocess.Popen(["explorer.exe", win_path])
                self.status_var.set("Status: Launched in Windows")

            else:

                self.process = subprocess.Popen(
                    [linux_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.status_var.set(f"Status: Running (PID: {self.process.pid})")

        except Exception as e:
            self.status_var.set("Status: Error")
            messagebox.showerror("Launch Error", f"Could not launch uMD_GUI.exe:\n{e}")

    def _close_app(self):
        """Terminate the launched uMD_GUI.exe process, if any."""
        if self.process:
            try:
                self.process.terminate()
                self.process = None
                self.status_var.set("Status: Closed by user")
            except Exception as e:
                messagebox.showerror("Error", f"Could not close process:\n{e}")
        else:
            self.status_var.set("Status: No process attached")


# -------------------------------------------------------------------
# Standalone test
# -------------------------------------------------------------------
if __name__ == "__main__":
    app = tb.Window(themename="darkly")
    app.title("uMD Display Test")

    frame = DisplayFrame(app)
    frame.pack(fill="both", expand=True)

    def on_close():

        frame._close_app()

        if frame.broker_proc is not None:
            try:
                frame.broker_proc.terminate()
            except Exception:
                pass
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()
