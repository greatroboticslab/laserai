# Notice

If you are **Dr. Zhang Hongbo** or a member of the **UMD Robotics / Laser Lab**, you may download the compiled Windows application or find the complete dataset/code in the shared Google Drive under:
**`thang_data/code`**

---

# **LaserAI: Moku:Go Control + Displacement Processing Toolkit**

LaserAI is a Python-based toolkit designed for laboratories using the **Moku:Go** platform for waveform generation and laser interferometry experiments.

This application provides:

* A **graphical interface** for configuring and controlling the Moku:Go waveform generator
* A **cross-platform raw data processing engine** converting displacement readings into nanometers
* Native support for **Windows, WSL, and Linux** folder picking and export paths
* Auto-generation of **CSV files and visual plots** for experimental analysis

LaserAI is built with **Python 3.13**, **ttkbootstrap**, **matplotlib**, and the **Liquid Instruments Moku API**.

---

# **Features**

## 1. Moku:Go Waveform Generator (GUI)

Located in `MokuWaveformFrame` (see `display.py`).
Key capabilities:

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

This feature is intended for experiments where displacement data must be collected at multiple test frequencies (for example, like the lathe or piezo)

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
lazer_app/
│
├── app.py                # Main launcher (GUI host)
├── display.py            # Contains MokuWaveformFrame (GUI)
├── process_raw.py        # Raw data engine + GUI
├── moku_waveform.py      # Auxiliary waveform logic
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

   * Waveform Control
   * Record Data
   * Raw Data Processing

3. Configure settings in the selected tab

4. Run the desired operation

5. Retrieve output files from the selected folder

---

# **License**

MIT
