# Notice

If you are **Dr. Zhang Hongbo** or a member of the **UMD Robotics / Laser Lab**, you may download the compiled Windows application or find the complete dataset/code in the shared Google Drive under:
**`thang_data/code`**

---

# **LaserAI: Moku:Go Control + Displacement Processing Toolkit**

LaserAI is a Python-based toolkit designed for laboratories using the **Moku:Go** platform for waveform generation and laser interferometry experiments.

This application provides:

* A **graphical interface** for configuring and controlling the Moku:Go waveform generator
* **PID-based waveform smoothing** using Moku:Go's built-in PID Controller via Multi-Instrument Mode
* A **cross-platform raw data processing engine** converting displacement readings into nanometers
* Native support for **Windows, WSL, and Linux** folder picking and export paths
* Auto-generation of **CSV files and visual plots** for experimental analysis

LaserAI is built with **Python 3.13**, **ttkbootstrap**, **matplotlib**, and the **Liquid Instruments Moku API**.

---

# **Features**

## 1. Moku:Go Waveform Generator with PID Smoothing (GUI)

Located in `MokuWaveformFrame` (see `moku_waveform.py`).

### Waveform Generation

* Connect to a Moku:Go via IP address
* Generate **Sine**, **Square**, or **Noise** waveforms
* Fully configurable:

  * Amplitude (4 mVpp – 10 Vpp)
  * Frequency (1 mHz – 20 MHz)
  * Offset voltage
  * Phase
  * Duty cycle (square only)
* Built-in safety validation for all parameters
* Ability to **stop output** or **disconnect** safely

### PID Smoothing (Open-Loop)

The waveform tab includes a built-in **PID smoothing toggle** that uses Moku:Go's hardware PID Controller to clean up the generated waveform before it reaches the physical output.

#### How it works

When you click **Connect**, the app deploys **Multi-Instrument Mode (MiM)** on the Moku:Go with two instruments running simultaneously on the FPGA:

* **Slot 1 — Waveform Generator**: Produces the target waveform (sine, square, noise)
* **Slot 2 — PID Controller**: Processes the waveform signal to reduce noise and ringing

When PID is **OFF** (default):
```
WG (Slot 1) → Output 1    (direct, same as standalone mode)
```

When PID is **ON**:
```
WG (Slot 1) → PID (Slot 2) → Output 1    (smoothed at MHz on the FPGA)
```

Toggling PID on/off only changes the internal signal routing. The Waveform Generator never stops or restarts — all waveform settings (frequency, amplitude, etc.) are preserved.

#### How to use PID Smoothing

1. **Connect** to the Moku:Go (enter IP, click Connect)
2. **Set your waveform** (type, frequency, amplitude) and click **Apply Waveform**
3. Verify the waveform is working on your measurement display
4. **Enable PID Smoothing** — toggle the checkbox in the PID section
5. **Adjust gains** if needed:
   * Start with **Prop gain only** (default 10 dB), Int and Diff at 0
   * If the waveform needs more smoothing, increase Prop gain
   * If slow drift appears, add a small Int gain (e.g., 10 dB) with a low Int corner frequency
   * **Avoid Diff gain** — derivative action amplifies high-frequency noise
6. Click **Apply Gains** after changing values
7. **Disable PID** — uncheck the toggle to return to direct WG output

#### PID Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| Prop gain (dB) | 10.0 | Proportional gain — main smoothing control. Higher = more effect |
| Int gain (dB) | 0.0 | Integrator gain — corrects slow drift. Start at 0, add if needed |
| Diff gain (dB) | 0.0 | Differentiator gain — usually leave at 0 (amplifies noise) |
| Int corner (Hz) | 100.0 | Integrator saturation frequency |
| Diff corner (Hz) | 100.0 | Differentiator saturation frequency |
| Output limit (V) | 5.0 | Voltage clamp to protect piezo hardware |

#### Suggested starting gains

| Waveform | Prop gain | Int gain | Diff gain | Notes |
|----------|-----------|----------|-----------|-------|
| Sine (1–10 Hz) | 10 dB | 0 dB | 0 dB | Start here, increase prop if needed |
| Square | 10 dB | 0 dB | 0 dB | Same starting point |
| Any (more smoothing) | 20 dB | 10 dB | 0 dB | Add int for extra filtering |

#### Important notes

* PID smoothing is **open-loop** — the PID acts as a signal filter on the WG output, not a feedback controller
* The PID runs on the Moku:Go FPGA at **125 MSa/s** — no Python in the signal path
* All gains are in **dB**, not linear values
* The Moku AI recommends using the **Digital Filter Box** or **FIR Filter Builder** instruments if you need more precise bandwidth shaping — the PID Controller is a simpler but effective option for basic smoothing

### Setup Detection

* Automatic detection of:
  * Missing `moku` Python package
  * Missing `mokucli` installation
* A guided "Setup Required" page that helps users install missing components

---

## 2. Raw Data Processor (GUI)

Implemented in `process_raw.py`.
Designed for processing interferometer output logs formatted like:

```
D:<float>   N:<integer>
```

### What it does:

* Recursively scans all `.txt` files in a folder
* Extracts displacement samples (`D`) and sample index (`N`)
* Converts to nanometers using:

```
nm = (D - baseline) * (wavelength / 2) - correction
```

* Supports two operating modes:

  1. **Absolute** mode
  2. **Relative** (baseline-subtracted) mode

* Auto-creates:

  * CSV file
  * Full plot of all samples
  * Zoomed plot of first *N* points

### Output Location:

Always saved under your OS **Downloads** folder in:

```
output_<foldername>
```

### Windows, WSL, and Linux Support:

* Native folder picker in Windows
* Under WSL:

  * Uses PowerShell.exe to open Windows dialogs
  * Converts paths between WSL and NTFS
* Will automatically open the export folder after processing

---

## 3. Integrated Application Launcher

The root script `app.py` manages:

* App initialization
* Notebook-style tab structure
* Embedding the MokuWaveformFrame and ProcessRawFrame GUIs
* Building as a Windows `.exe` via PyInstaller

---

## 4. Automated Record Data (Frequency Sweep Logger)

The **Record Data** tab provides an automated data-collection workflow designed to replicate and standardize the manual UMD GUI logging procedure used in the lab.

This feature is intended for experiments where displacement data must be collected at multiple test frequencies (for example, 1–10 Hz) with consistent timing and waveform settings.

### Preconditions (automatically enforced)

The **Record Data** feature is only enabled when **all** of the following conditions are met:

1. The **Moku:Go is connected** and ready to accept waveform parameter changes
2. **MQTT is connected and receiving data**
3. The **uMD GUI is running and actively streaming data** into the uMD GUI tab

If any condition is not met, the Record button remains disabled and the status message indicates what is missing.

### What the Record Data tab does

Once started, the tool will:

1. Automatically apply waveform settings to the Moku:Go
2. Step through a user-defined frequency range (start to end, inclusive)
3. Record raw displacement data for a fixed duration at each frequency
4. Generate one log file per frequency
5. Save all files to a user-selected output folder

All frequency stepping and timing is handled automatically without manual intervention.

**Note:** If PID smoothing is enabled in the Moku:Go Waveform tab, the recorded data will reflect the smoothed output. The Record Data tab calls the same waveform generator — PID state is preserved during recording.

### User-configurable inputs

The Record Data tab allows the user to specify:

* **Output folder path** (default: OS Downloads directory)

  * Includes a Browse button to select a different location
* **Output subfolder name** to group files from a single experiment run
* **Recording duration per frequency** (in seconds)
* **Frequency range** (start and end values)
* **Waveform voltage (Vpp)** (default: 5 Vpp)
* **Sample frequency** (used for documentation in the log header, default: 1000 Hz)

### Progress window

When recording begins, a modal progress window appears displaying:

* Overall progress across all frequencies
* The current frequency being recorded
* The name of the file currently being written
* Elapsed time and estimated remaining time
* A **Stop** button to safely cancel the run

The main application UI remains locked until recording completes or is stopped.

### Output file format

Each test frequency produces a separate text file named:

```
log_<frequency>Hz.txt
```

Each file begins with a header documenting the test conditions:

```
Sample Frequency = 1000 Hz Voltage = 5 Vpp Test Frequency = 1 Hz
```

Followed by raw displacement entries:

```
D:68 N:1
D:68 N:2
D:69 N:3
```

Where:

* **D** is the raw displacement count from the interferometer
* **N** is a local serial index starting at 1 for each file

This format is intentionally compatible with the existing Raw Data Processor.

---

# **Architecture**

## Multi-Instrument Mode (MiM)

LaserAI connects to the Moku:Go using **Multi-Instrument Mode** instead of deploying a standalone Waveform Generator. This allows two instruments to run simultaneously on the FPGA:

```
┌─────────────────────────────────────────────────┐
│                  Moku:Go FPGA                   │
│                                                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │   Slot 1     │      │   Slot 2     │        │
│  │  Waveform    │─────▶│    PID       │──▶ Output 1
│  │  Generator   │      │  Controller  │        │
│  └──────────────┘      └──────────────┘        │
│         │                                       │
│         └──────────────────────────────────▶ Output 1
│              (when PID is OFF)                  │
└─────────────────────────────────────────────────┘
```

When PID is OFF, the WG output routes directly to Output 1. When PID is ON, the WG output passes through the PID Controller first. The routing switch happens internally on the FPGA with zero interruption to the waveform.

## System Data Flow

```
[Moku:Go WG + PID]  →  [Piezo Amplifier]  →  [Physical Displacement]
                                                       ↓
                                              [Laser Interferometer]
                                                       ↓
                                              [VB uMD_GUI.exe]
                                                       ↓
                                              [MQTT (vb_to_py)]
                                                       ↓
                                              [Python display.py]
                                                       ↓
                                              [Graph + Log Files]
```

---

# **Installation**

## Requirements

* Python **3.13**
* pip packages:

  ```
  ttkbootstrap
  matplotlib
  moku   (optional but required for real waveform control)
  ```

Install everything from requirements:

```
pip install -r requirements.txt
```

---

## Moku Dependencies

On Windows, install:

* **Moku CLI** (must be on PATH)
* **Moku Python API**:

```
pip install --upgrade moku
```

Verify:

```
mokucli --help
```

If the app cannot find the CLI or API, it will show a setup panel and explain how to fix it.

---

# **Building the Windows EXE**

From PowerShell (not WSL):

```
pyinstaller app.py --onefile --noconsole
```

This generates:

```
/dist/app.exe
```

Note: Running PyInstaller inside WSL will create a Linux binary instead. Always build from Windows-side PowerShell.

---

# **Repository Structure**

```
laserai/
│
├── app.py                # Main launcher (GUI host)
├── moku_waveform.py      # Waveform Generator + PID smoothing (MiM)
├── display.py            # uMD GUI display + MQTT subscriber
├── record_data.py        # Automated frequency sweep recorder
├── process_raw.py        # Raw data engine + GUI
│
├── moku_diagnostic.py    # Standalone hardware diagnostic tool
│
├── broker_mqtt/          # MQTT broker binaries (Windows)
│
├── moku_data/            # Instrument model data (bar files)
│
├── umd_gui/              # Legacy UMD GUI binaries
│
├── .venv/                # Local virtual environment (ignored)
├── build/                # PyInstaller build output (ignored)
├── dist/                 # Final packaged exe (ignored)
│
└── .gitignore            # Repository ignore rules
```

---

# **Usage Overview**

1. Launch the app

2. Select one of the available tabs:

   * **Moku:Go Waveform** — generate waveforms + optional PID smoothing
   * **uMD GUI** — view live displacement data
   * **Record Data** — automated frequency sweep recording
   * **Process Raw** — offline data processing

3. **Typical workflow:**

   * Connect to Moku:Go → Apply Waveform → (optional) Enable PID Smoothing
   * Switch to uMD GUI tab to observe live displacement
   * Use Record Data tab to capture data at multiple frequencies
   * Use Process Raw tab to convert logs to CSV + plots

---

# **Diagnostic Tool**

`moku_diagnostic.py` is a standalone script for verifying hardware connectivity and Multi-Instrument Mode support. Run it before using the app if you encounter connection issues:

```bash
python moku_diagnostic.py                # default IP 192.168.73.1
python moku_diagnostic.py 192.168.1.xx   # custom IP
```

The diagnostic tests:
* Standalone PID Controller connectivity
* Multi-Instrument Mode availability
* WaveformGenerator + PIDController deployment in MiM
* Signal routing configuration
* `set_control_matrix`, `get_data()`, and cleanup methods

---

# **License**

MIT