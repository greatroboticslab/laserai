# Notice

If you are **Dr. Zhang Hongbo** or a member of the **UMD Robotics / Laser Lab**, you may download the compiled Windows application or find the complete dataset/code in the shared Google Drive under:
**`thang_data/code`**

---

# LaserAI

LaserAI is a Python desktop application for a laser displacement / interferometry workflow. It combines Moku:Go waveform generation, a VB-based interferometer application (`uMD_GUI.exe`), a bundled local MQTT broker, automated recording, and raw-data processing into one interface.

The Python app is the orchestration and UI layer. The VB application is still the current source of truth for the interferometer-side processed data stream.

---

## Overview

This project connects several pieces of your lab workflow into one application:

- **Moku:Go** for waveform generation
- **uMD_GUI.exe** for interferometer-side processing and MQTT publishing
- **Mosquitto** as a bundled local MQTT broker
- **Python GUI** for:
  - launching the VB app
  - receiving MQTT payloads
  - converting raw interferometer values into displacement in nm
  - recording data runs
  - processing raw `.txt` logs into CSV and plots

---

## System Architecture

The current signal and software flow is:

Moku:Go waveform output
→ physical laser / interferometer setup
→ VB uMD_GUI.exe reads/derives signal values
→ VB publishes MQTT payloads to topic "vb_to_py"
→ Python display.py subscribes to MQTT
→ Python parses payload into refCount / D / phaseRaw
→ Python computes displacement in nm
→ record_data.py logs measurement series while commanding Moku waveform settings

Important: Python is **not** currently doing the low-level interferometer decoding. The VB application still produces the MQTT payloads that Python consumes.

---

## Features

### 1. Moku:Go waveform control

The Moku tab lets you connect to a Moku:Go and generate supported waveform types.

Supported waveform types:

* Sine
* Square
* Ramp
* Pulse
* Noise

The Moku tab is the **single source of truth** for waveform configuration.

Depending on the waveform type, only the relevant settings are shown or enabled to reduce confusion.

Examples:

* **Sine**: amplitude, frequency, offset, phase
* **Square**: amplitude, frequency, offset, phase, duty
* **Ramp**: amplitude, frequency, offset, phase, symmetry
* **Pulse**: amplitude, frequency, offset, phase, pulse width, edge time
* **Noise**: amplitude only

### 2. PID smoothing with Multi-Instrument Mode

On connect, the app deploys Moku:Go in **Multi-Instrument Mode (MiM)**:

* **Slot 1**: Waveform Generator
* **Slot 2**: PID Controller

When PID is off:

```text
WG (Slot 1) → Output 1
```

When PID is on:

```text
WG (Slot 1) → PID (Slot 2) → Output 1
```

This allows waveform generation and hardware-side PID smoothing without redeploying the waveform generator.

### 3. Live MQTT displacement display

The Display tab:

* launches `uMD_GUI.exe`
* ensures a local Mosquitto broker is running
* subscribes to `vb_to_py`
* parses MQTT payloads
* computes displacement in nm
* displays the latest received values

Supported MQTT payload formats:

1. CSV: `refCount,D,phaseRaw`
2. Single float: treated as already being displacement in nm

### 4. Automated recording

The Record Data tab automates waveform-based experiment logging.

It uses the currently selected waveform configuration from the **Moku tab** and records the incoming interferometer displacement counts from the VB → MQTT stream.

For periodic waveforms:

* Sine
* Square
* Ramp
* Pulse

the recorder can sweep frequency from a user-defined start to end value.

For **Noise**, recording runs as a single non-swept acquisition.

The Record tab only shows the configuration relevant to the waveform currently selected in the Moku tab.

### 5. Raw data processing

The Process Raw tab:

* scans `.txt` files recursively
* extracts `D:<value> N:<serial>` records
* converts to nanometers
* exports CSV
* creates plots

It supports:

* **Absolute mode**
* **Relative (baseline-subtracted) mode**

---

## Interferometer Math

The VB side publishes payloads in the form:

```text
refCount,D,phaseRaw
```

Python mirrors the same displacement conversion logic:

```text
phase = phaseRaw / 256.0
displacement_nm = (D - phase) * (632.991372 / 2.0) - correction
```

Current constants:

* `WAVELENGTH_NM = 632.991372`
* `PHASE_SCALE = 256.0`
* `CORRECTION_NM = 0.0`

This means:

* each full fringe contributes `λ/2`
* `phaseRaw` refines the displacement within that fringe
* the result is a nanometer-scale displacement estimate

---

## File Structure

```text
laserai/
│
├── app.py
├── display.py
├── moku_waveform.py
├── record_data.py
├── process_raw.py
├── README.md
├── requirements.txt
│
├── broker_mqtt/
│   └── mosquitto.exe
│
├── umd_gui/
│   └── uMD_GUI.exe
│
├── moku_data/
│
├── build/
├── dist/
└── .venv/
```

---

## File Responsibilities

### `app.py`

Main GUI entry point.

Responsibilities:

* creates the Tk / ttkbootstrap app
* builds the notebook tabs
* resolves `BASE_DIR` safely for both Python and PyInstaller
* exports `MOKU_DATA_PATH`
* prepends bundled `moku` tools to `PATH` when needed
* wires app shutdown to `display_tab.shutdown()`

### `display.py`

MQTT and VB application integration.

Responsibilities:

* launches `uMD_GUI.exe`
* starts the bundled Mosquitto broker if needed
* subscribes to MQTT topic `vb_to_py`
* parses payloads
* computes displacement in nm
* stores latest received data for display and recording

### `moku_waveform.py`

Moku:Go waveform control and PID smoothing.

Responsibilities:

* connects to Moku:Go
* deploys Multi-Instrument Mode
* manages waveform configuration
* applies waveform changes
* exposes the current waveform config to the Record tab
* optionally enables PID smoothing

### `record_data.py`

Automated acquisition workflow.

Responsibilities:

* checks readiness conditions
* mirrors the current waveform selected in the Moku tab
* sweeps frequency when appropriate
* records one log file per run
* writes raw `D / N` records
* manages modal progress and stop handling

### `process_raw.py`

Offline raw-data processor.

Responsibilities:

* parses `.txt` logs
* converts counts to displacement in nm
* generates CSV outputs
* creates plots
* provides some cross-platform folder helpers

---

## Current Workflow

Typical use:

1. Launch the application
2. Connect to **Moku:Go** in the Moku tab
3. Select waveform type and settings
4. Apply waveform
5. Optionally enable PID smoothing
6. Open the **uMD GUI** tab and launch `uMD_GUI.exe`
7. Confirm MQTT data is streaming
8. Go to **Record Data**
9. Record a sweep or single run depending on waveform type
10. Use **Process Raw** to convert logs into CSV and plots

---

## Recording Behavior

The Record tab does **not** own waveform configuration.

Instead, it reads the waveform currently configured in the Moku tab.

### Periodic waveforms

For these waveform types:

* Sine
* Square
* Ramp
* Pulse

the Record tab performs a frequency sweep using the configured waveform type and its relevant parameters.

### Noise

Noise does not use the same frequency-sweep model as periodic waveforms.

For Noise:

* the Record tab hides frequency sweep controls
* one run is recorded using the current Noise configuration

---

## Output Format

Each recording produces a `.txt` log file.

Examples:

* `log_1Hz.txt`
* `log_2Hz.txt`
* `log_pulse.txt`
* `log_noise.txt`

Header example:

```text
Sample Frequency = 1000 Hz Voltage = 5 Vpp Waveform = Square Channel = 1 Test Frequency = 3 Hz Offset = 0 V Phase = 0 deg Duty = 50 %
```

Data lines:

```text
D:68 N:1
D:68 N:2
D:69 N:3
```

Where:

* `D` is the raw displacement count received from the VB → MQTT pipeline
* `N` is a local serial counter starting at 1 for each file

This format is intentionally compatible with the raw processor.

---

## Raw Processing Output

The raw processor exports:

* CSV file
* full plot of all samples
* zoomed plot of the first N points

Modes:

* **Absolute**
* **Relative (baseline-subtracted)**

Outputs are saved under the system Downloads folder in:

```text
output_<foldername>
```

---

## Installation

### Requirements

* Python 3.13 recommended
* Windows is the primary target environment

Install dependencies:

```bash
pip install -r requirements.txt
```

### `requirements.txt`

Current dependencies:

```text
ttkbootstrap
paho-mqtt
matplotlib
pyserial
pyinstaller
moku
```

---

## Moku Setup

You need:

* the **Moku Python package**
* **Moku CLI**
* instrument data compatible with your installed MokuOS version

Install / update the Python package:

```bash
pip install --upgrade moku
```

Verify the CLI:

```bash
mokucli --help
```

Download instrument data if needed:

```bash
mokucli instrument download <MokuOS_version>
```

If Moku dependencies are not available, the waveform tab will show a setup screen instead of the full waveform controls.

---

## Running the App

From the project root:

```bash
python app.py
```

---

## Building the Windows EXE

Use PowerShell and run from the project root.

### One-line version

```powershell
python -m PyInstaller --name LaserLab_v4.1 --onefile --noconsole --add-data "moku_data;moku_data" --add-data "umd_gui;umd_gui" --add-data "broker_mqtt;broker_mqtt" app.py
```

### Multi-line PowerShell version

```powershell
python -m PyInstaller --name LaserLab_v4.1 --onefile --noconsole `
  --add-data "moku_data;moku_data" `
  --add-data "umd_gui;umd_gui" `
  --add-data "broker_mqtt;broker_mqtt" `
  app.py
```

Important:

* In **PowerShell**, use the backtick `` ` `` for line continuation
* Do **not** paste the shell prompt itself into the terminal
* Do **not** include `>>`

Expected output:

```text
dist\LaserLab_v4.1.exe
```

---

## PyInstaller Notes

This project depends on runtime-relative bundled folders, so these must be included in the build:

* `moku_data`
* `umd_gui`
* `broker_mqtt`

The app uses a PyInstaller-safe base directory helper so resources can be found both:

* during normal Python execution
* in a one-file packaged executable

---

## Known Design Constraints

* The VB application is still part of the measurement path
* Python currently does not replace VB-side interferometer decoding
* Windows is the main target platform
* The app is designed to avoid hardcoded absolute paths
* Tkinter UI updates should remain on the main thread
* Worker threads may read latest shared values, but the UI itself should not be updated directly from worker threads

---

## Known Good Areas

* PyInstaller base-directory strategy
* Bundled `uMD_GUI.exe` launch pattern
* Bundled Mosquitto launch pattern
* MQTT payload parsing structure
* Record Data modal progress approach
* Process Raw export pipeline

---

## Areas to Watch / Active Development

* readiness booleans for the Record tab
* exact meaning of “uMD running” versus “actively streaming”
* precise sample-rate behavior during recording
* exact accepted Moku API kwargs depending on installed package version and device firmware
* future expansion into additional modulation / burst / sweep features if needed

---

## Notes on the VB Application

`uMD_GUI.exe` is a Visual Basic executable included under:

```text
umd_gui/uMD_GUI.exe
```

It is not just a viewer. It is currently part of the live data production path and publishes interferometer-derived values over MQTT.

The source code for the VB application exists separately, even though the compiled EXE is what this project currently launches.

---

## License

MIT
