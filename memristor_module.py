"""
Memristor analysis helpers.

This module stores memristor research calculations only.  Pulse timing belongs
to Arduino, acquisition belongs to SEELab, and plotting belongs to GUI code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class ConductancePoint:
    pulse_number: int
    device_voltage: float
    sense_voltage: float
    current_amp: float
    conductance_siemens: float
    resistance_ohm: float
    mode: str = ""


class ConductanceTracker:
    def __init__(self, sense_resistor_ohm: float = 100.0):
        self.sense_resistor_ohm = max(0.001, float(sense_resistor_ohm))
        self.points: List[ConductancePoint] = []

    def clear(self):
        self.points.clear()

    def add_measurement(self, input_voltage, sense_voltage, mode="") -> ConductancePoint:
        try:
            pulse_number = len(self.points) + 1
            input_voltage = float(input_voltage)
            sense_voltage = float(sense_voltage)
            current = sense_voltage / self.sense_resistor_ohm
            device_voltage = input_voltage - sense_voltage

            if abs(device_voltage) < 1e-12:
                conductance = 0.0
            else:
                conductance = abs(current) / abs(device_voltage)

            if abs(current) < 1e-12:
                resistance = float("inf")
            else:
                resistance = abs(device_voltage) / abs(current)

            point = ConductancePoint(
                pulse_number=pulse_number,
                device_voltage=device_voltage,
                sense_voltage=sense_voltage,
                current_amp=current,
                conductance_siemens=conductance,
                resistance_ohm=resistance,
                mode=mode,
            )
            self.points.append(point)
            return point

        except Exception as exc:
            print("Conductance Measurement Error")
            print(exc)
            point = ConductancePoint(
                pulse_number=len(self.points) + 1,
                device_voltage=0.0,
                sense_voltage=0.0,
                current_amp=0.0,
                conductance_siemens=0.0,
                resistance_ohm=float("inf"),
                mode=mode,
            )
            self.points.append(point)
            return point

    def add_from_waveforms(self, input_waveform, sense_waveform, mode="mean") -> ConductancePoint:
        input_data = np.asarray(input_waveform, dtype=float)
        sense_data = np.asarray(sense_waveform, dtype=float)

        if len(input_data) == 0 or len(sense_data) == 0:
            return self.add_measurement(0.0, 0.0, mode)

        if mode == "peak":
            input_voltage = input_data[np.argmax(np.abs(input_data))]
            sense_voltage = sense_data[np.argmax(np.abs(sense_data))]
        elif mode == "last":
            input_voltage = input_data[-1]
            sense_voltage = sense_data[-1]
        else:
            input_voltage = np.mean(input_data)
            sense_voltage = np.mean(sense_data)

        return self.add_measurement(input_voltage, sense_voltage, mode)

    def arrays(self):
        pulse_numbers = np.array([point.pulse_number for point in self.points])
        conductance = np.array([point.conductance_siemens for point in self.points])
        resistance = np.array([point.resistance_ohm for point in self.points])
        current = np.array([point.current_amp for point in self.points])
        return pulse_numbers, conductance, resistance, current


def build_set_reset_plan(
    set_pulses=10,
    reset_pulses=10,
    set_width_us=1000,
    reset_width_us=1000,
    delay_ms=100,
):
    """
    Return Arduino-ready SET/RESET packet dictionaries.

    The caller should pass these values to arduino_serial_module rather than
    generating timing loops in Python.
    """

    return {
        "set": {
            "high_time_us": int(set_width_us),
            "low_time_us": int(delay_ms * 1000),
            "pulse_count": int(set_pulses),
            "mode": "SET",
        },
        "reset": {
            "high_time_us": int(reset_width_us),
            "low_time_us": int(delay_ms * 1000),
            "pulse_count": int(reset_pulses),
            "mode": "RESET",
        },
    }


def clamp_pv1_voltage(voltage):
    """Clamp PV1 to the safe SEELab 0 V to 5 V range."""

    try:
        return min(max(float(voltage), 0.0), 5.0)
    except Exception:
        return 0.0


def build_linear_amplitude_sequence(start_voltage, stop_voltage, step_voltage):
    """Build safe PV1 amplitude steps for incremental pulse experiments."""

    try:
        start_voltage = clamp_pv1_voltage(start_voltage)
        stop_voltage = clamp_pv1_voltage(stop_voltage)
        step_voltage = abs(float(step_voltage))

        if step_voltage <= 0:
            step_voltage = 0.1

        values = []

        if start_voltage <= stop_voltage:
            voltage = start_voltage
            while voltage <= stop_voltage + 1e-9:
                values.append(clamp_pv1_voltage(voltage))
                voltage += step_voltage
        else:
            voltage = start_voltage
            while voltage >= stop_voltage - 1e-9:
                values.append(clamp_pv1_voltage(voltage))
                voltage -= step_voltage

        return values

    except Exception as exc:
        print("Amplitude Sequence Error")
        print(exc)
        return []
