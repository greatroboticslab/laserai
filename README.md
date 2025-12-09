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

This makes the tool usable even on new lab machines where Moku software isn't installed yet.

---

## 2. Raw Data Processor (GUI)

Implemented in `process_raw.py` .
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

The root script `app.py` (user did not upload — but referenced) manages:

* App initialization
* Notebook-style tab structure
* Embedding the MokuWaveformFrame and ProcessRawFrame GUIs
* Building as a Windows `.exe` via PyInstaller

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

### From PowerShell (not WSL):

```
pyinstaller app.py --onefile --noconsole
```

This generates:

```
/dist/app.exe
```

Note: Running PyInstaller **inside WSL** will create a Linux binary instead. Always build from Windows-side PowerShell.

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

# **How It Works (High-Level)**

## 1. Waveform Control

`MokuWaveformFrame` builds a Bootstrap-styled interface allowing a user to define electrical waveforms.
When the "Apply" button is pressed:

1. Input ranges are validated
2. Arguments are assembled
3. The app calls:

```
instrument.generate_waveform(channel=..., type=..., amplitude=..., ...)
```

The GUI updates connection status, errors, and applied settings in real-time.

---

## 2. Displacement Calculation

From the physics side:

* The interferometer tracks optical phase via the variable **D**
* Nanometer displacement ~= `(wavelength / 2) * phase_shift`
* `"Relative"` mode subtracts the initial D value for drift measurements

This conversion is automated inside:

```
raw_to_nm()
```

Plots are rendered using `matplotlib` and exported as PNGs.

---

# **Usage Overview**

1. Launch the app
2. Select:

   * **Waveform Control**
   * or **Raw Data Processing**
3. Configure settings in the GUI
4. Run commands
5. Retrieve output (waveforms or processed plots/CSVs)

The UI was built carefully to be friendly for researchers, with guard-rails and automatic fallback for missing software.

---

# **License**

[MIT] or choose another license—just tell me if you want this added.
