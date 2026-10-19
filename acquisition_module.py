"""Arduino ADC acquisition module.

WHY CHANGED: the original module used the SEELab (eyes17) device for ADC
capture via device.capture2() and device.capture1(). SEELab has been removed
from the project. All acquisition now goes through the Arduino's built-in
10-bit ADC (A0 = channel 1, A1 = channel 2) via the SAMPLE serial command.

Arduino ADC limits:
  - Resolution: 10-bit (0–1023, maps to 0–5 V with default 5 V reference)
  - Max reliable sample rate: ~2 kHz (gap_us ≥ 500 µs) when streaming over serial
  - For faster sampling consider an external SPI ADC (ADS1248, MCP3208)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

from arduino_serial_module import ArduinoSampleConfig

ADC_VREF_V = 5.0     # Arduino Vcc reference voltage
ADC_BITS   = 1023.0  # 10-bit max


@dataclass
class AcquisitionConfig:
    samples: int = 300
    time_gap_us: int = 500   # must be >= 100; below ~500 serial TX dominates timing
    channel_0: str = "A0"    # maps to oscilloscope channel 1 (was SEELab A1)
    channel_1: str = "A1"    # maps to oscilloscope channel 2 (was SEELab A2)
    max_samples: int = 500   # Arduino firmware hard limit


@dataclass
class AcquisitionFrame:
    time: np.ndarray          # milliseconds
    channels: Dict[str, np.ndarray]
    differential: np.ndarray = field(default_factory=lambda: np.array([]))


class AcquisitionBuffer:
    """Rolling frame buffer — O(1) eviction via deque."""

    def __init__(self, max_frames: int = 100):
        self.max_frames = max(1, int(max_frames))
        self.frames: deque = deque(maxlen=self.max_frames)

    def append(self, frame: AcquisitionFrame):
        self.frames.append(frame)

    def latest(self) -> Optional[AcquisitionFrame]:
        return self.frames[-1] if self.frames else None

    def clear(self):
        self.frames.clear()


def clamp_samples(samples: int, max_samples: int = 500) -> int:
    try:
        return max(16, min(int(samples), int(max_samples)))
    except Exception:
        return 300


def _adc_to_volts(raw: int) -> float:
    return float(raw) / ADC_BITS * ADC_VREF_V


def capture_a1_a2(arduino, config: Optional[AcquisitionConfig] = None) -> Optional[AcquisitionFrame]:
    """Capture dual-channel ADC from Arduino A0 (ch1) and A1 (ch2).

    Replaces the SEELab eyes17 device.capture2() call. Sends a SAMPLE command
    to the Arduino and reads back the streamed CSV data over serial.
    """
    config = config or AcquisitionConfig()
    try:
        count = clamp_samples(config.samples, config.max_samples)
        gap_us = max(100, int(config.time_gap_us))

        sample_cfg = ArduinoSampleConfig(
            channel_0=config.channel_0,
            channel_1=config.channel_1,
            count=count,
            gap_us=gap_us,
            timeout_s=count * gap_us / 1_000_000.0 * 4 + 5.0,
        )

        if not arduino.request_sample(sample_cfg):
            return None

        rows = arduino.read_sample_data(count, timeout_s=sample_cfg.timeout_s)
        if len(rows) < 2:
            return None

        actual = len(rows)
        time_axis = np.arange(actual) * gap_us / 1000.0   # milliseconds
        ch0 = np.array([_adc_to_volts(r[0]) for r in rows])
        ch1 = np.array([_adc_to_volts(r[1]) if len(r) > 1 else 0.0 for r in rows])

        return AcquisitionFrame(
            time=time_axis,
            channels={"A1": ch0, "A2": ch1},
            differential=ch0 - ch1,
        )

    except Exception as exc:
        print(f"Capture A1/A2 error: {exc}")
        return None


def capture_single_channel(arduino, channel: str = "A0", samples: int = 300, time_gap_us: int = 500):
    """Capture a single Arduino analog channel.

    Replaces device.capture1(). Returns (time_ms_array, voltage_array) or (None, None).
    """
    try:
        count = clamp_samples(samples, 500)
        gap_us = max(100, int(time_gap_us))

        cfg = ArduinoSampleConfig(
            channel_0=channel,
            channel_1="",
            count=count,
            gap_us=gap_us,
        )

        if not arduino.request_sample(cfg):
            return None, None

        rows = arduino.read_sample_data(count, timeout_s=count * gap_us / 1_000_000.0 * 4 + 5.0)
        if not rows:
            return None, None

        time_axis = np.arange(len(rows)) * gap_us / 1000.0
        voltages = np.array([_adc_to_volts(r[0]) for r in rows])
        return time_axis, voltages

    except Exception as exc:
        print(f"Single channel capture error: {exc}")
        return None, None


def calculate_measurements(time_axis, voltage):
    try:
        y = np.asarray(voltage, dtype=float)
        x = np.asarray(time_axis, dtype=float)
        if len(y) < 2 or len(x) != len(y):
            return {}

        vpp = float(np.max(y) - np.min(y))
        rms = float(np.sqrt(np.mean(y ** 2)))
        peak = float(np.max(y))
        mean = float(np.mean(y))
        frequency = estimate_frequency(x, y)

        return {"vpp": vpp, "rms": rms, "peak": peak, "mean": mean, "frequency": frequency}

    except Exception as exc:
        print(f"Measurement error: {exc}")
        return {}


def estimate_frequency(time_axis, voltage) -> float:
    try:
        x = np.asarray(time_axis, dtype=float)
        y = np.asarray(voltage, dtype=float)
        if len(x) < 4:
            return 0.0

        level = np.mean(y)
        crossings = np.where((y[:-1] < level) & (y[1:] >= level))[0]
        if len(crossings) < 2:
            return 0.0

        periods = np.diff(x[crossings])
        periods = periods[periods > 0]
        if len(periods) == 0:
            return 0.0

        period_ms = float(np.median(periods))
        if period_ms <= 0:
            return 0.0
        return 1000.0 / period_ms   # ms → Hz

    except Exception:
        return 0.0


def calculate_current_from_sense(sense_voltage, sense_resistor_ohm: float = 100.0):
    try:
        safe_r = max(0.001, float(sense_resistor_ohm))
        return np.asarray(sense_voltage, dtype=float) / safe_r
    except Exception as exc:
        print(f"Current calculation error: {exc}")
        return np.array([])
