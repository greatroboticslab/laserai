# Notice

If you are **Dr. Zhang Hongbo** or a member of the **UMD Robotics / Laser Lab**, you may download the compiled Windows application or find the complete dataset/code in the shared Google Drive under:  
**`thang_data/code`**

---

# LaserAI: Moku:Go Control + Displacement Processing Toolkit

LaserAI is a Python-based toolkit designed for laboratories using the **Moku:Go** platform for waveform generation and laser interferometry experiments.

This application provides:

- A **graphical interface** for configuring and controlling the Moku:Go waveform generator  
- A **real-time MQTT displacement monitor** that listens to the UMD GUI stream  
- A **cross-platform raw data processing engine** converting displacement logs into nanometers  
- Native support for **Windows, WSL, and Linux** folder picking and export paths  
- Auto-generation of **CSV files and visual plots** for experimental analysis  

LaserAI is built with **Python 3.13**, **ttkbootstrap**, **matplotlib**, and the **Liquid Instruments Moku API**.

---

# Features

## 1) Moku:Go Waveform Generator (GUI)

Located in `MokuWaveformFrame` (see `display.py`).

Key capabilities:

- Connect to a Moku:Go via IP address
- Generate **Sine**, **Square**, or **Noise** waveforms
- Fully configurable:
  - Amplitude (4 mVpp – 10 Vpp)
  - Frequency (1 mHz – 20 MHz)
  - Offset voltage
  - Phase
  - Duty cycle (square only)
- Built-in safety validation for all parameters
- Ability to **stop output** or **disconnect** safely
- Automatic detection of:
  - Missing `moku` Python package
  - Missing `mokucli` installation
- A guided "Setup Required" page that helps users install missing components

---

## 2) Live Displacement Monitor via MQTT (UMD GUI → Python)

Implemented inside `display.py` (the GUI component that subscribes to MQTT and updates the **Latest displacement** field).

### Expected MQTT payload format

The UMD GUI (VB.NET) must publish **one CSV line per sample** in this exact format:

```text
refCount,D,phaseRaw
Field meanings:

refCount: reference/sample counter (acts like a “time-ish index”)

D: raw distance accumulator count from the FPGA (AxisData(ax, 2))

phaseRaw: raw phase count (AxisData(ax, 4)) before VB’s /256 scaling

If the payload is not exactly 3 comma-separated values, the Python app will log:

text
Copy code
[MQTT] Bad payload: b'...'
MQTT topics used
VB publishes to: vb_to_py

Python subscribes to: vb_to_py

(One-way stream: UMD GUI → Python display.)

What “Latest displacement” means
The GUI field Latest displacement shows the most recent sample converted into nanometers (nm) inside Python from the raw MQTT payload.

In display.py, Python computes:

phase = phaseRaw / 256 (to match the scaling used in VB math)

then converts to nm using the same physics form:

text
Copy code
nm = (D - phase) * (WAVELENGTH_NM / 2) - CORRECTION_NM
So the number you see is not D, and it is not phaseRaw — it is the latest converted displacement value (nm), updated each time a new MQTT message arrives.

Note: if you package the app with --noconsole, you won’t see MQTT printouts in a terminal. Use the Latest displacement field to confirm messages are arriving (or build without --noconsole while debugging).

3) Raw Data Processor (GUI)
Implemented in process_raw.py.

Designed for processing interferometer output logs formatted like:

text
Copy code
D:<float>   N:<integer>
What it does
Recursively scans all .txt files in a folder

Extracts displacement samples (D) and sample index (N)

Converts to nanometers using:

text
Copy code
nm = (D - baseline) * (wavelength / 2) - correction
Supports two operating modes:

Absolute mode

Relative (baseline-subtracted) mode

Auto-creates:

CSV file

Full plot of all samples

Zoomed plot of first N points

Output location
Always saved under your OS Downloads folder in:

text
Copy code
output_<foldername>
Windows, WSL, and Linux support
Native folder picker in Windows

Under WSL:

Uses PowerShell.exe to open Windows dialogs

Converts paths between WSL and NTFS

Automatically opens the export folder after processing

4) Integrated Application Launcher
The root script app.py manages:

App initialization

Notebook-style tab structure

Embedding the GUI frames (waveform control + processing + MQTT monitor)

Building as a Windows .exe via PyInstaller

Installation
Requirements
Python 3.13

pip packages:

bash
Copy code
pip install -r requirements.txt
Dependencies include:

ttkbootstrap

matplotlib

moku (optional but required for real waveform control)

Moku Dependencies
On Windows, install:

Moku CLI (must be on PATH)

Moku Python API:

bash
Copy code
pip install --upgrade moku
Verify:

bash
Copy code
mokucli --help
If the app cannot find the CLI or API, it will show a setup panel and explain how to fix it.

Building the Windows EXE
From PowerShell (not WSL)
bash
Copy code
pyinstaller app.py --onefile --noconsole
This generates:

text
Copy code
/dist/app.exe
Running PyInstaller inside WSL will create a Linux binary instead. Always build from Windows-side PowerShell.

Repository Structure
text
Copy code
lazer_app/
│
├── app.py                # Main launcher (GUI host)
├── display.py            # Waveform GUI + MQTT displacement monitor
├── process_raw.py        # Raw data engine + GUI
├── moku_waveform.py      # Auxiliary waveform logic
│
├── broker_mqtt/          # MQTT broker binaries (Windows)
├── moku_data/            # Instrument model data (bar files)
├── umd_gui/              # UMD GUI binaries
│
├── .venv/                # Local virtual environment (ignored)
├── build/                # PyInstaller build output (ignored)
├── dist/                 # Final packaged exe (ignored)
│
└── .gitignore            # Repository ignore rules
