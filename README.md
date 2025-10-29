# 🔬 Laser Displacement Data Parser & Grapher (GUI)

A desktop application built with Python + ttkbootstrap that converts raw interferometer
text logs into processed CSV datasets and plots.

It supports both absolute and relative displacement conversion, generates full and zoomed
graphs automatically, and saves all outputs to your system’s Downloads folder.

------------------------------------------------------------------------------------------
*******************
# Before you read further: If you are a Doctor Zhang Hongbo researcher and is only loooking for the app, the app is downloadable in the google drive thang_data/Code/lazerApp_
*******************
# 🧭 Overview

Tab                     | Description
------------------------ | -----------------------------------------------
Process Raw              | Main tool to select a folder of `.txt` data files,
                         | choose processing mode, and auto-generate CSV + plots.
Placeholder              | Reserved area for future tools (demo tab).

Cross-platform (Windows/macOS/Linux/WSL) with native file-explorer dialogs.

------------------------------------------------------------------------------------------
# ✨ Features

📁  Folder-based batch processing — select an entire folder of `.txt` files.
⚙️  Automatic output → ~/Downloads/output_<selected_folder_name>/
🧮  Converts interferometer logs: D:<raw_count> N:<sequence_number>
📊  Generates plots:
     • *_all.png  → entire dataset
     • *_zoom.png → first N points (zoomed view)
📄  Exports CSVs:
     • Absolute: Time_ms, Absolute_Displacement_nm
     • Relative: Time_ms, Delta_Displacement_nm
🪟  Modern GUI with progress bar and native dialogs.

------------------------------------------------------------------------------------------
# ⚖️ Absolute vs Relative Modes

Mode     | Description
--------- | -----------------------------------------------------------
1 (Abs)   | Converts raw interferometer counts directly to nanometers.
2 (Rel)   | Subtracts the first D-value so plots start at 0 nm.

Absolute ≈ odometer, Relative ≈ trip meter.

------------------------------------------------------------------------------------------
# 📂 Input / Output Example

Input file:
  Sample Frequency = 1000 Hz
  D:623187844 N:2248769
  D:623187845 N:2248770

Output (Downloads/output_folder/):
  example_absolute.csv
  example_absolute_all.png
  example_absolute_zoom.png

Example CSV (relative mode):
  Time_ms,Delta_Displacement_nm
  0.000,0.000
  1.000,316.495
  2.000,632.991

------------------------------------------------------------------------------------------
# 🧩 Dependencies  (requirements.txt)

ttkbootstrap
paho-mqtt
matplotlib
pyserial
pyinstaller

Install them inside a virtual environment:
  pip install -r requirements.txt

------------------------------------------------------------------------------------------
# 🚀 Run the App  (Developer)

  python app.py

When launched:
  1. Click the “Process Raw” tab.
  2. Browse to your data folder.
  3. Choose mode (Absolute / Relative).
  4. Adjust sample frequency / zoom points.
  5. Press “Run” → results in Downloads/.

------------------------------------------------------------------------------------------
# 🧱 Build a Stand-Alone Executable

Windows:
  pyinstaller app.py --onefile --noconsole

macOS:
  pyinstaller app.py --onefile --windowed --name "Laser Data Parser"

Output:  dist/app.exe  or  dist/Laser Data Parser.app

------------------------------------------------------------------------------------------
# 🧠 Technical Notes

• Output path automatically resolves to the OS Downloads folder.
• Supports WSL → Windows Explorer integration.
• Uses matplotlib (Agg backend) for headless plot generation.
• Modular structure:
    ├── app.py           # main window / tab manager
    ├── process_raw.py   # logic & GUI for processing
    └── placeholder.py   # stub for future tools

------------------------------------------------------------------------------------------
# 🧰 Future Extensions

• Batch post-processing (filtering / FFT)
• MQTT live-stream parser
• 3D surface mapping
• Data quality validation tools

------------------------------------------------------------------------------------------
# 🏷️ License
MIT © Great Robotics Lab

------------------------------------------------------------------------------------------
Tip: The built `.exe` automatically uses your native file explorer and
writes results straight to your Downloads folder — no manual paths required.
