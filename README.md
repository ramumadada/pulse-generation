# Pulse Generation & Signal Analysis Platform

A modular instrumentation platform developed during a Research Internship at the
University of Hyderabad. The system uses an **Arduino UNO** as the sole hardware
controller — generating pulses, acquiring analog signals via the built-in 10-bit ADC,
and outputting bias voltages via PWM — coordinated by a Python/PyQt5 GUI.

---

## Screenshots & Demo

| Basic Setup | Oscilloscope View | IV Analyzer |
|:-----------:|:-----------------:|:-----------:|
| ![basic-1](https://drive.google.com/uc?export=view&id=basic-1) | ![basic-2](https://drive.google.com/uc?export=view&id=basic-2) | ![basic-3](https://drive.google.com/uc?export=view&id=basic-3) |

> Full image gallery and interface demo video:
> **[Google Drive — Pulse_Generation folder](https://drive.google.com/drive/folders/17KRl3tyDmtp5uRdixyRHKKvt-OUXEkjE)**
>
> Files: `basic-1.png` · `basic-2.png` · `basic-3.png` · `basic-4.png` · `basic-6.png` · `simulation.png` · `my interface.mp4`

---

## Features

- Programmable pulse train generation (frequency, duty cycle, count)
- Burst pulse generation (configurable bursts and pulses per burst)
- Incremental-amplitude pulse sweeps for memristor / device characterisation
- Real-time **dual-channel oscilloscope** (A0 & A1)
- Display trigger (rising / falling edge, adjustable level)
- FFT with peak detection, harmonic analysis, and THD calculation
- Differential channel display (A0 − A1)
- IV sweep analyzer with live voltage/current graph
- Waveform and FFT export to CSV
- Experiment logging
- Bias voltage output via PWM + RC filter on pins 5 & 6

---

## Hardware

| Component | Role |
|-----------|------|
| Arduino UNO | Pulse generation, ADC sampling (A0/A1), PWM bias voltage |
| MOSFET switching circuit | Combines Arduino timing + bias voltage into pulse output |
| RC filter (1 kΩ + 100 µF) | Converts PWM on pin 5/6 to DC bias (0–5 V) |
| Sense resistor (100 Ω) | Current measurement via A1 voltage divider |

**Arduino ADC limits:**
- 10-bit resolution → 0–1023 maps to 0–5 V
- Maximum reliable sample rate over serial: ~2 kHz (gap ≥ 500 µs)

---

## Software Stack

| Layer | Technology |
|-------|-----------|
| GUI | Python 3, PyQt5, PyQtGraph |
| Serial | pyserial |
| Signal processing | NumPy, SciPy (`butter`, `lfilter`, `savgol_filter`) |
| Firmware | Arduino C++ (`.ino`) |
| CI | GitHub Actions — ruff lint |

---

## Repository Structure

```
main_scope.py                 Main GUI — oscilloscope, FFT, pulse controls
iv_module.py                  IV sweep analyser window
arduino_pulse_engine/
  arduino_pulse_engine.ino    Arduino firmware
arduino_serial_module.py      Serial protocol layer (commands, ADC, PWM)
acquisition_module.py         ADC capture — SAMPLE command → NumPy arrays
trigger_module.py             Display trigger and scope engine
pulse_train_module.py         Pulse packet builders
fft_module.py                 FFT, THD, harmonic detection
signal_conditioning_module.py Low-pass filter, moving average
save_module.py                CSV and log export
requirements.txt              Python dependencies (pinned)
CHANGES.md                    Full changelog with reasons for every change
legacy/                       Archived legacy GUI code
```

---

## Installation

### 1. Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Arduino firmware

Open `arduino_pulse_engine/arduino_pulse_engine.ino` in the Arduino IDE
and upload it to your UNO.

### 3. Hardware wiring

| Arduino pin | Connection |
|-------------|-----------|
| Pin 9 | Pulse output → MOSFET gate |
| Pin 5 | PWM bias 1 → RC filter → device |
| Pin 6 | PWM bias 2 → RC filter → device |
| A0 | Signal input channel 1 |
| A1 | Signal input / sense resistor channel 2 |

---

## Running the Application

```bash
python main_scope.py
```

1. Select the Arduino COM port from the dropdown.
2. Click **Connect** — the app waits for the firmware ready token automatically.
3. Use the pulse controls to configure and start pulse generation.
4. The oscilloscope and FFT update in real time.
5. Open **IV Analyzer** from the menu for voltage-sweep experiments.

---

## Safety Notes

- Keep PWM bias outputs within 0–5 V (Arduino Vcc reference).
- Never connect Arduino pins directly to voltages above 5 V.
- Use appropriate MOSFET gate resistors and protection diodes.
- A0/A1 are measurement inputs — connect through a voltage divider if the signal exceeds 5 V.

---

## Author

**Ramu Madada**  
Research Internship — University of Hyderabad, 2026  
Electrical and Electronics Engineering
