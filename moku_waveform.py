import os
import sys
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

import ttkbootstrap as tb
from ttkbootstrap.constants import *


try:
    from moku.instruments import WaveformGenerator
    from moku import MokuException
except Exception:  # moku package missing or import error
    WaveformGenerator = None

    class MokuException(Exception):
        """Fallback exception if real MokuException is not available."""
        pass


# Safe limits taken from the Waveform Generator / generate_waveform docs.
MOKUGO_AMPLITUDE_MIN = 4e-3   # Vpp
MOKUGO_AMPLITUDE_MAX = 10.0   # Vpp

MOKUGO_FREQ_MIN = 1e-3        # Hz
MOKUGO_FREQ_MAX = 20e6        # Hz

MOKUGO_OFFSET_MIN = -5.0      # V
MOKUGO_OFFSET_MAX = 5.0       # V

MOKU_PHASE_MIN = 0.0          # degrees
MOKU_PHASE_MAX = 360.0        # degrees

DUTY_MIN = 0.0                # %
DUTY_MAX = 100.0              # %


class MokuWaveformFrame(ttk.Frame):
    """
    Notebook tab for Moku:Go waveform control.

    Behaviour:
      - On init, checks for:
          * presence of the moku Python package (WaveformGenerator import)
          * presence of `mokucli` on PATH
      - If both are OK: shows full waveform generator UI.
      - If either is missing: shows a grey "setup required" screen with:
          * instructions + docs link
          * button to re-check; if things are fixed, it swaps to full UI.
    """
    def __init__(self, parent, has_mokucli: bool | None = None):
        super().__init__(parent, padding=16)

        # Cache instrument instance when connected
        self._instrument = None

        # Let caller pass in detection result, or detect here.
        if has_mokucli is None:
            has_mokucli = self._check_mokucli()
        self._has_mokucli = has_mokucli

        # Tk variables for waveform settings
        # Default to common hotspot IP for MokuGo
        self.ip_var = tk.StringVar(value="192.168.73.1")
        self.status_var = tk.StringVar(value="Not connected")

        self.channel_var = tk.IntVar(value=1)
        self.wave_type_var = tk.StringVar(value="Sine")

        self.amplitude_var = tk.DoubleVar(value=1.0)
        self.frequency_var = tk.DoubleVar(value=1000.0)
        self.offset_var = tk.DoubleVar(value=0.0)
        self.phase_var = tk.DoubleVar(value=0.0)
        self.duty_var = tk.DoubleVar(value=50.0)

        # Decide which UI to show
        if WaveformGenerator is not None and self._has_mokucli:
            self._build_waveform_ui()
        else:
            self._build_setup_ui()

        # Make frame stretch nicely
        self.columnconfigure(0, weight=1)
        for c in range(1, 4):
            self.columnconfigure(c, weight=1)

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _check_mokucli() -> bool:
        """Return True if `mokucli` is on PATH."""
        return shutil.which("mokucli") is not None

    # ------------------------------------------------------------------
    # Setup / missing-deps UI
    # ------------------------------------------------------------------
    def _build_setup_ui(self):
        """Show greyed-out page with installation instructions."""
        # Clear any existing children
        for child in self.winfo_children():
            child.destroy()

        # Header
        ttk.Label(
            self,
            text="Moku:Go Waveform (Setup Required)",
            font=("Segoe UI", 13, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # Greyish frame to give the "disabled" vibe
        setup_frame = ttk.LabelFrame(
            self,
            text="Moku CLI / API not ready",
            padding=12,
            bootstyle=SECONDARY
        )
        setup_frame.grid(row=1, column=0, columnspan=4, sticky="nsew")
        for c in range(4):
            setup_frame.columnconfigure(c, weight=1)

        # Figure out what's missing
        parts = []
        if WaveformGenerator is None:
            parts.append("- The Python package 'moku' (Waveform API)")
        if not self._has_mokucli:
            parts.append("- The Moku command-line tool 'mokucli'")

        missing_txt = "\n".join(parts) if parts else "- (Unable to detect components)"

        ttk.Label(
            setup_frame,
            text=(
                "This tab is disabled because the Moku Python stack is not fully installed.\n\n"
                "Missing components:\n"
                f"{missing_txt}\n"
            ),
            justify="left"
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # Instructions text (scrollable & copyable)
        instructions = (
            "Quick setup (run these in a terminal):\n"
            "  1. Install / update the Python package:\n"
            "       pip install --upgrade moku\n"
            "  2. Install Moku CLI:\n"
            "       - Download the installer from:\n"
            "         https://liquidinstruments.com/utilities/\n"
            "       - Getting started docs:\n"
            "         https://apis.liquidinstruments.com/api/getting-started/starting-python.html\n"
            "  3. Make sure 'mokucli' is on your PATH:\n"
            "       mokucli --help\n"
            "     If that prints usage text, you're good.\n"
            "  4. Download instrument data (only once per machine):\n"
            "       mokucli instrument download <MokuOS_version>\n"
        )

        text_frame = ttk.Frame(setup_frame)
        text_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(0, 8))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        txt = tk.Text(
            text_frame,
            height=10,
            wrap="word",
        )
        txt.insert("1.0", instructions)
        txt.configure(state="disabled")   # still selectable / copyable
        txt.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        txt.configure(yscrollcommand=scroll.set)

        # Clickable hyperlinks under the instructions
        link_frame = ttk.Frame(setup_frame)
        link_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 4))

        def open_utilities(event=None):
            webbrowser.open("https://liquidinstruments.com/utilities/", new=1)

        def open_docs(event=None):
            webbrowser.open(
                "https://apis.liquidinstruments.com/api/getting-started/starting-python.html",
                new=1,
            )

        util_link = tk.Label(
            link_frame,
            text="Open Moku Utilities page",
            fg="blue",
            cursor="hand2",
        )
        util_link.pack(side="left", padx=(0, 12))
        util_link.bind("<Button-1>", open_utilities)

        docs_link = tk.Label(
            link_frame,
            text="Open Python getting-started docs",
            fg="blue",
            cursor="hand2",
        )
        docs_link.pack(side="left")
        docs_link.bind("<Button-1>", open_docs)

        # Buttons row
        btn_row = ttk.Frame(setup_frame)
        btn_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))

        ttk.Button(
            btn_row,
            text="Verify Moku setup",
            bootstyle=PRIMARY,
            command=self._on_verify_clicked
        ).pack(side="left")

        ttk.Label(
            setup_frame,
            text="Once the commands above succeed, click 'Verify Moku setup' to enable this tab.",
            justify="left"
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

        # Make setup_frame expand
        self.rowconfigure(1, weight=1)

    def _on_verify_clicked(self):
        """User pressed the 'Verify Moku setup' button."""
        self._has_mokucli = self._check_mokucli()

        if WaveformGenerator is None:
            messagebox.showerror(
                "Moku Python package missing",
                "The 'moku' Python package is still not importable.\n\n"
                "Make sure you ran:\n"
                "    pip install --upgrade moku\n"
                "in the same environment that runs this app."
            )
            return

        if not self._has_mokucli:
            messagebox.showerror(
                "mokucli not found",
                "I still cannot find 'mokucli' on PATH.\n\n"
                "Try opening a fresh terminal / restarting your PC after installing Moku CLI,\n"
                "then run 'mokucli --help' to confirm it works from the command line."
            )
            return

        # If we got here, both the Python package and mokucli look OK.
        messagebox.showinfo(
            "Moku ready",
            "Moku CLI and the Python package look good.\n\n"
            "Enabling the waveform controls."
        )
        # Swap UI to the full waveform view
        self._build_waveform_ui()

    # ------------------------------------------------------------------
    # Full waveform UI (when everything is installed)
    # ------------------------------------------------------------------
    def _build_waveform_ui(self):
        """Build the full waveform generator UI (replaces any existing content)."""
        # Clear existing widgets (e.g., setup UI)
        for child in self.winfo_children():
            child.destroy()

        # Title
        ttk.Label(
            self,
            text="Moku:Go Waveform Generator",
            font=("Segoe UI", 13, "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w")

        # Connection frame
        conn_frame = ttk.LabelFrame(self, text="Connection", padding=8)
        conn_frame.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 5))
        conn_frame.columnconfigure(1, weight=1)

        ttk.Label(conn_frame, text="Moku:Go IP:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(conn_frame, textvariable=self.ip_var, width=20).grid(row=0, column=1, sticky="ew")

        ttk.Button(
            conn_frame,
            text="Connect",
            bootstyle=SUCCESS,
            command=self._connect
        ).grid(row=0, column=2, padx=(8, 0))

        ttk.Button(
            conn_frame,
            text="Disconnect",
            bootstyle=DANGER,
            command=self._disconnect
        ).grid(row=0, column=3, padx=(4, 0))

        ttk.Label(conn_frame, textvariable=self.status_var).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(5, 0)
        )

        # New: Wi-Fi help button + tip text
        ttk.Button(
            conn_frame,
            text="Wi-Fi help",
            bootstyle=INFO,
            command=self._open_wifi_settings
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

        ttk.Label(
            conn_frame,
            text=(
                "Tip: connect this computer to the MokuGo Wi-Fi "
                "(ex: 'MokuGo-003703')\n"
                "or to the same lab network where the Moku:Go is connected, "
                "then use its IP above."
            ),
            justify="left"
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(2, 0))

        # Waveform settings
        wf_frame = ttk.LabelFrame(self, text="Waveform Settings", padding=8)
        wf_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=(10, 5))
        for c in range(4):
            wf_frame.columnconfigure(c, weight=1)

        # Channel
        ttk.Label(wf_frame, text="Channel:").grid(row=0, column=0, sticky="e", pady=2)
        ttk.Combobox(
            wf_frame,
            textvariable=self.channel_var,
            values=[1, 2],
            state="readonly",
            width=5
        ).grid(row=0, column=1, sticky="w", pady=2)

        # Waveform type
        ttk.Label(wf_frame, text="Type:").grid(row=0, column=2, sticky="e", pady=2)
        type_cb = ttk.Combobox(
            wf_frame,
            textvariable=self.wave_type_var,
            values=["Sine", "Square", "Noise"],
            state="readonly",
            width=10
        )
        type_cb.grid(row=0, column=3, sticky="w", pady=2)
        type_cb.bind("<<ComboboxSelected>>", self._on_type_changed)

        # Amplitude
        ttk.Label(wf_frame, text="Amplitude (Vpp):").grid(row=1, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.amplitude_var, width=10).grid(
            row=1, column=1, sticky="w", pady=2
        )
        ttk.Label(
            wf_frame,
            text=f"[{MOKUGO_AMPLITUDE_MIN:.4f} – {MOKUGO_AMPLITUDE_MAX:.1f}]"
        ).grid(row=1, column=2, columnspan=2, sticky="w", pady=2)

        # Frequency
        ttk.Label(wf_frame, text="Frequency (Hz):").grid(row=2, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.frequency_var, width=10).grid(
            row=2, column=1, sticky="w", pady=2
        )
        ttk.Label(
            wf_frame,
            text=f"[{MOKUGO_FREQ_MIN:g} – {MOKUGO_FREQ_MAX:g}]"
        ).grid(row=2, column=2, columnspan=2, sticky="w", pady=2)

        # Offset
        ttk.Label(wf_frame, text="Offset (V):").grid(row=3, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.offset_var, width=10).grid(
            row=3, column=1, sticky="w", pady=2
        )
        ttk.Label(
            wf_frame,
            text=f"[{MOKUGO_OFFSET_MIN:.1f} – {MOKUGO_OFFSET_MAX:.1f}]"
        ).grid(row=3, column=2, columnspan=2, sticky="w", pady=2)

        # Phase
        ttk.Label(wf_frame, text="Phase (deg):").grid(row=4, column=0, sticky="e", pady=2)
        ttk.Entry(wf_frame, textvariable=self.phase_var, width=10).grid(
            row=4, column=1, sticky="w", pady=2
        )
        ttk.Label(
            wf_frame,
            text=f"[{MOKU_PHASE_MIN:.0f} – {MOKU_PHASE_MAX:.0f}]"
        ).grid(row=4, column=2, columnspan=2, sticky="w", pady=2)

        # Duty (Square only)
        ttk.Label(wf_frame, text="Duty (%):").grid(row=5, column=0, sticky="e", pady=2)
        self.duty_entry = ttk.Entry(wf_frame, textvariable=self.duty_var, width=10)
        self.duty_entry.grid(row=5, column=1, sticky="w", pady=2)
        ttk.Label(
            wf_frame,
            text=f"[{DUTY_MIN:.0f} – {DUTY_MAX:.0f}] (Square only)"
        ).grid(row=5, column=2, columnspan=2, sticky="w", pady=2)

        # Action buttons
        btn_frame = ttk.Frame(self, padding=(0, 10, 0, 0))
        btn_frame.grid(row=3, column=0, columnspan=4, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        ttk.Button(
            btn_frame,
            text="Apply Waveform",
            bootstyle=PRIMARY,
            command=self._apply_waveform
        ).grid(row=0, column=0, sticky="e", padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="Stop Output",
            bootstyle=SECONDARY,
            command=self._stop_output
        ).grid(row=0, column=1, sticky="w", padx=(5, 0))

        # Make main rows stretch
        self.rowconfigure(2, weight=1)

        # Ensure duty field is in the right state
        self._on_type_changed()

    # ------------------------------------------------------------------
    # Wi-Fi helper
    # ------------------------------------------------------------------
    def _open_wifi_settings(self):
        """
        Try to open the OS Wi-Fi settings.

        On Windows: opens the modern Wi-Fi settings panel.
        On Linux/macOS/WSL: shows an info dialog telling the user to connect manually.
        """
        try:
            if sys.platform == "win32":
                # Windows 10/11 modern Wi-Fi settings
                os.startfile("ms-settings:network-wifi")
            elif sys.platform.startswith("darwin"):
                # macOS: open Network preferences (best-effort)
                subprocess.run(
                    ["open", "x-apple.systempreferences:com.apple.preference.network"],
                    check=False,
                )
                messagebox.showinfo(
                    "Wi-Fi settings",
                    "Network preferences have been opened.\n"
                    "Connect to the MokuGo Wi-Fi (e.g. 'MokuGo-003703') "
                    "or the same network as your Moku:Go."
                )
            else:
                # Linux / WSL / other: just explain what to do
                messagebox.showinfo(
                    "Wi-Fi instructions",
                    "Connect this computer to the MokuGo Wi-Fi network "
                    "(for example 'MokuGo-003703'),\n"
                    "or to the same lab network where the Moku:Go is connected.\n\n"
                    "Use your OS network menu / Wi-Fi settings to change networks."
                )
        except Exception as e:
            messagebox.showerror(
                "Cannot open Wi-Fi settings",
                "Could not open Wi-Fi settings automatically.\n\n"
                "Please connect manually to the MokuGo Wi-Fi "
                "(for example 'MokuGo-003703').\n\n"
                f"Details: {e}"
            )

    # ------------------------------------------------------------------
    # Connection logic
    # ------------------------------------------------------------------
    def _connect(self):
        if WaveformGenerator is None:
            messagebox.showerror(
                "Moku Python package missing",
                "Cannot import the Moku WaveformGenerator.\n\n"
                "Make sure the 'moku' package is installed in this environment."
            )
            return

        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Missing IP", "Please enter the Moku:Go IP address.")
            return

        # Close any existing connection first
        self._disconnect(silent=True)

        try:
            self.status_var.set("Connecting...")
            self.update_idletasks()

            self._instrument = WaveformGenerator(ip, force_connect=True)
            self.status_var.set(f"Connected to {ip}")
        except Exception as e:
            self._instrument = None
            self.status_var.set("Not connected")
            messagebox.showerror("Connection failed", str(e))

    def _disconnect(self, silent: bool = False):
        if self._instrument is not None:
            try:
                self._instrument.relinquish_ownership()
            except Exception:
                pass
            finally:
                self._instrument = None

        self.status_var.set("Not connected")
        if not silent:
            messagebox.showinfo("Disconnected", "Disconnected from Moku:Go.")

    # ------------------------------------------------------------------
    # Waveform application
    # ------------------------------------------------------------------
    def _apply_waveform(self):
        if self._instrument is None:
            messagebox.showwarning(
                "Not connected",
                "Connect to your Moku:Go first."
            )
            return

        # Get values from UI
        try:
            channel = int(self.channel_var.get())
        except ValueError:
            messagebox.showerror("Invalid channel", "Channel must be 1 or 2.")
            return

        wave_type = self.wave_type_var.get()

        try:
            amplitude = float(self.amplitude_var.get())
            frequency = float(self.frequency_var.get())
            offset = float(self.offset_var.get())
            phase = float(self.phase_var.get())
            duty = float(self.duty_var.get())
        except ValueError:
            messagebox.showerror(
                "Invalid input",
                "One or more numeric fields contain invalid values."
            )
            return

        # Range checks (guard rails)
        if not (MOKUGO_AMPLITUDE_MIN <= amplitude <= MOKUGO_AMPLITUDE_MAX):
            messagebox.showerror(
                "Amplitude out of range",
                f"Amplitude {amplitude} Vpp is out of range.\n\n"
                f"Allowed: {MOKUGO_AMPLITUDE_MIN:.4f} – {MOKUGO_AMPLITUDE_MAX:.1f} Vpp."
            )
            return

        if not (MOKUGO_FREQ_MIN <= frequency <= MOKUGO_FREQ_MAX):
            messagebox.showerror(
                "Frequency out of range",
                f"Frequency {frequency} Hz is out of range.\n\n"
                f"Allowed: {MOKUGO_FREQ_MIN:g} – {MOKUGO_FREQ_MAX:g} Hz."
            )
            return

        if not (MOKUGO_OFFSET_MIN <= offset <= MOKUGO_OFFSET_MAX):
            messagebox.showerror(
                "Offset out of range",
                f"Offset {offset} V is out of range.\n\n"
                f"Allowed: {MOKUGO_OFFSET_MIN:.1f} – {MOKUGO_OFFSET_MAX:.1f} V."
            )
            return

        if not (MOKU_PHASE_MIN <= phase <= MOKU_PHASE_MAX):
            messagebox.showerror(
                "Phase out of range",
                f"Phase {phase}° is out of range.\n\n"
                f"Allowed: {MOKU_PHASE_MIN:.0f} – {MOKU_PHASE_MAX:.0f}°."
            )
            return

        if wave_type == "Square":
            if not (DUTY_MIN <= duty <= DUTY_MAX):
                messagebox.showerror(
                    "Duty out of range",
                    f"Duty {duty}% is out of range.\n\n"
                    f"Allowed: {DUTY_MIN:.0f} – {DUTY_MAX:.0f}%."
                )
                return

        # Send to Moku
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

            self._instrument.generate_waveform(**kwargs)
            self.status_var.set(
                f"{wave_type} on ch{channel}: {amplitude} Vpp, "
                f"{frequency:g} Hz, offset {offset} V"
            )
        except MokuException as e:
            messagebox.showerror("Moku error", str(e))
        except Exception as e:
            messagebox.showerror("Error applying waveform", str(e))

    def _stop_output(self):
        if self._instrument is None:
            messagebox.showwarning(
                "Not connected",
                "Connect to your Moku:Go first."
            )
            return

        try:
            channel = int(self.channel_var.get())
        except ValueError:
            messagebox.showerror("Invalid channel", "Channel must be 1 or 2.")
            return

        try:
            self._instrument.generate_waveform(channel=channel, type="Off")
            self.status_var.set(f"Channel {channel} output OFF")
        except Exception as e:
            messagebox.showerror("Error stopping output", str(e))

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    def _on_type_changed(self, event=None):
        wave_type = self.wave_type_var.get()
        if wave_type == "Square":
            self.duty_entry.config(state="normal")
        else:
            self.duty_entry.config(state="disabled")

    def destroy(self):
        # Clean up connection on tab close
        self._disconnect(silent=True)
        super().destroy()
