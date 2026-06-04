# Hybrid Pulse Generation + Oscilloscope Platform (Arduino-Based Programmable Pulse Generator and Signal Analysis System)

Professional modular instrumentation platform using Python, PyQt5, PyQtGraph, SEELab/eyes17, Arduino UNO, MOSFET switching hardware, and external analog electronics.

## Core Architecture

- Python GUI: control, plotting, analysis, logging, and experiment coordination.
- SEELab: A1/A2 acquisition, PV1/PV2 voltage control, FFT source data, and analog measurements.
- Arduino UNO: hardware-timed gate pulses on D9/Timer1, pulse trains, burst timing, and PWM timing.
- MOSFET stage: Arduino controls gate timing, SEELab PV1 controls real analog pulse amplitude.

## Main Features

- Dual-channel oscilloscope with A1, A2, and A1-A2 differential display.
- FFT analysis and THD display.
- Persistent oscilloscope PiP visible while using sub-pages.
- Arduino pulse train and burst control.
- Timer1 fast burst mode on D9 / OC1A.
- Incremental PV1 amplitude pulse train mode.
- CSV waveform and FFT export.
- Experiment logging.

## Hardware Principle

Arduino D9 controls the MOSFET gate timing.

SEELab PV1 controls the real pulse amplitude.

SEELab A1 observes the pulse output.

SEELab A2 observes load/sense/current waveform.

## Run

```powershell
python main_scope.py
```

The application opens full screen by default.

## Arduino Firmware

Upload:

```text
arduino_pulse_engine/arduino_pulse_engine.ino
```

Arduino serial baud rate:

```text
115200
```

After upload, open the GUI, select the Arduino COM port, connect, press `Status`, then run pulse train, burst, fast burst, or incremental PV1 pulse mode.

## Safety

- Keep PV1 between 0 V and 5 V.
- Do not connect PV1 directly to Arduino pins.
- Use MOSFET switching and protection resistors.
- Arduino D9 is for gate timing only.
- SEELab PV1 is the real amplitude source.
- SEELab A1/A2/A3 are measurement inputs only.
