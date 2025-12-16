LaserAI: Moku:Go Control + Displacement Processing Toolkit

LaserAI is a Python-based toolkit designed for laboratories using the Moku:Go platform for waveform generation and laser interferometry experiments.

This application provides:

A graphical interface for configuring and controlling the Moku:Go waveform generator

A real-time MQTT displacement monitor that listens to the UMD GUI stream

A cross-platform raw data processing engine converting displacement logs into nanometers

Native support for Windows, WSL, and Linux folder picking and export paths

Auto-generation of CSV files and visual plots for experimental analysis

LaserAI is built with Python 3.13, ttkbootstrap, matplotlib, and the Liquid Instruments Moku API.

Features
1. Moku:Go Waveform Generator (GUI)

Located in MokuWaveformFrame (see display.py).
Key capabilities:

Connect to a Moku:Go via IP address

Generate Sine, Square, or Noise waveforms

Fully configurable:

Amplitude (4 mVpp – 10 Vpp)

Frequency (1 mHz – 20 MHz)

Offset voltage

Phase

Duty cycle (square only)

Built-in safety validation for all parameters

Ability to stop output or disconnect safely

Automatic detection of:

Missing moku Python package

Missing mokucli installation

A guided "Setup Required" page that helps users install missing components

2. Live Displacement Monitor via MQTT (UMD GUI → Python)

Implemented inside display.py (the frame that handles MQTT + updates the “Latest displacement” field).

What the Python side expects

The UMD GUI (VB.NET) must publish one CSV line per sample in this exact format:

refCount,D,phaseRaw


Meaning:

refCount: reference/sample counter (used as the “x-axis / time-ish index”)

D: raw distance/phase accumulator count from the FPGA (AxisData(ax, 2))

phaseRaw: raw phase count (AxisData(ax, 4)) before VB’s /256 scaling

If the payload is not exactly 3 comma-separated values, the app will log:

[MQTT] Bad payload: ...

Topics used

VB publishes to: vb_to_py

Python subscribes to: vb_to_py

(So this path is one-way: UMD GUI → Python display.)

What “Latest displacement” means

The GUI field “Latest displacement” shows the most recent sample converted into nanometers (nm) inside Python from the raw MQTT payload.

In display.py, Python computes:

phase = phaseRaw / 256 (to match the scaling used in VB math)

then converts to nm using the same physics form:

nm = (D - phase) * (WAVELENGTH_NM / 2) - CORRECTION_NM


So the number you see is not D, and it is not phaseRaw — it is the latest converted displacement value in nm, updated every time a new MQTT message arrives.

Note: if you package the app with --noconsole, you won’t see MQTT printouts in a terminal. Use the GUI “Latest displacement” field to confirm messages are arriving (or build without --noconsole for debugging).

3. Raw Data Processor (GUI)

Implemented in process_raw.py.

Designed for processing interferometer output logs formatted like:

D:<float>   N:<integer>

What it does:

Recursively scans all .txt files in a folder

Extracts displacement samples (D) and sample index (N)

Converts to nanometers using:

nm = (D - baseline) * (wavelength / 2) - correction


Supports:

Absolute mode

Relative (baseline-subtracted) mode

Auto-creates:

CSV file

Full plot of all samples

Zoomed plot of first N points

Output Location:

Always saved under your OS Downloads folder in:

output_<foldername>

Windows, WSL, and Linux Support:

Native folder picker in Windows

Under WSL:

Uses PowerShell.exe to open Windows dialogs

Converts paths between WSL and NTFS

Will automatically open the export folder after processing

4. Integrated Application Launcher

The root script app.py manages:

App initialization

Notebook-style tab structure

Embedding the GUI frames (waveform control + processing + MQTT monitor)

Building as a Windows .exe via PyInstaller

Installation
Requirements

Python 3.13

pip packages:

ttkbootstrap
matplotlib
moku   (optional but required for real waveform control)


Install everything from requirements:

pip install -r requirements.txt

Moku Dependencies

On Windows, install:

Moku CLI (must be on PATH)

Moku Python API:

pip install --upgrade moku


Verify:

mokucli --help

Building the Windows EXE
From PowerShell (not WSL):
pyinstaller app.py --onefile --noconsole


This generates:

/dist/app.exe


Note: Running PyInstaller inside WSL will create a Linux binary instead. Always build from Windows-side PowerShell.

Repository Structure
lazer_app/
│
├── app.py                # Main launcher (GUI host)
├── display.py             # Waveform GUI + MQTT displacement monitor
├── process_raw.py         # Raw data engine + GUI
├── moku_waveform.py       # Auxiliary waveform logic
│
├── broker_mqtt/           # MQTT broker binaries (Windows)
├── moku_data/             # Instrument model data (bar files)
├── umd_gui/               # UMD GUI binaries
│
├── .venv/                 # Local virtual environment (ignored)
├── build/                 # PyInstaller build output (ignored)
├── dist/                  # Final packaged exe (ignored)
│
└── .gitignore             # Repository ignore rules
