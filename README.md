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
