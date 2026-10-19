# Hybrid Pulse Generation and Signal Analysis Platform

A modular instrumentation platform developed during my Research Internship at the University of Hyderabad. The system combines Arduino UNO, Python, SEELab (eyes17), and external electronics to generate, control, visualize, and analyze electrical pulse signals in real time.

## Project Overview

This project was developed to provide an affordable and flexible platform for pulse generation, waveform visualization, and signal analysis. It integrates embedded systems, instrumentation, signal processing, and software development into a single experimental setup.

## Key Features

* Programmable pulse train generation
* Burst pulse generation
* Variable pulse width and timing control
* Variable-amplitude pulse generation using SEELab PV1
* Real-time dual-channel oscilloscope
* FFT and frequency-domain analysis
* Differential signal measurement (A1-A2)
* Waveform and FFT data export to CSV
* Experiment logging and data recording
* Persistent oscilloscope view across application modules

## Technologies Used

### Software

* Python
* PyQt5
* PyQtGraph
* Serial Communication

### Hardware

* Arduino UNO
* SEELab (eyes17)
* MOSFET Switching Circuit
* Analog Signal Conditioning Circuits

## System Architecture

The platform uses a hybrid architecture:

* Arduino UNO generates pulse timing, pulse trains, burst signals, and PWM-based control signals.
* SEELab provides analog voltage generation, signal acquisition, and measurement capabilities.
* Python GUI coordinates hardware control, data acquisition, visualization, and signal analysis.
* MOSFET switching circuitry combines timing control and analog voltage control to generate programmable pulse outputs.

## Applications

* Embedded Systems Learning
* Instrumentation Experiments
* Signal Processing Education
* Pulse Generation Research
* Laboratory Demonstrations
* Electronics and Control System Experiments

## Skills Demonstrated

* Embedded Systems Development
* Arduino Programming
* Python Application Development
* Hardware-Software Integration
* Signal Processing
* Oscilloscope and Measurement Systems
* Data Acquisition Systems
* Electronic Circuit Design
* Research and Experimentation

## Demonstration Videos and Images

Project Photos and Demonstrations:

https://drive.google.com/drive/folders/17KRl3tyDmtp5uRdixyRHKKvt-OUXEkjE

## Repository Structure

```text
main_scope.py                 Main GUI Application
arduino_pulse_engine/         Arduino Firmware
waveform_data/                Exported CSV Waveform Data
fft_data/                     Exported FFT CSV Data
experiment_logs/              Experiment Records
screenshots/                  Saved oscilloscope images
```

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install eyes17 (SEELab — not on PyPI)

eyes17 must be installed separately. Download the package from the SEELab
website or your lab's distribution and run:

```bash
pip install eyes17-<version>.whl
```

Refer to `HARDWARE_SETUP.md` for the exact version and download link.

## How to Run

1. Upload the Arduino firmware from `arduino_pulse_engine/`.
2. Connect Arduino UNO and SEELab to USB.
3. Launch the Python application.

```bash
python main_scope.py
```

4. Select the Arduino COM port.
5. Connect and verify hardware status.
6. Generate pulse trains, burst pulses, or variable-amplitude pulse signals.

## Safety Notes

* Operate SEELab PV1 within 0–5 V.
* Do not connect PV1 directly to Arduino pins.
* Use appropriate MOSFET switching and protection circuitry.
* Use A1/A2 inputs only for measurement purposes.

## Author

Ramu Madada

Research Internship – University of Hyderabad (2026)

Electrical and Electronics Engineering
