"""
SEELab acquisition module for the universal instrumentation platform.

This module keeps acquisition separate from GUI plotting.  It supports A1/A2
capture, differential calculation, rolling buffering, and measurement helpers.
Arduino remains responsible for pulse timing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np


@dataclass
class AcquisitionConfig:
    samples: int = 1200
    time_gap_us: int = 4
    channel_1: str = "A1"
    channel_2: str = "A2"
    max_samples: int = 5000


@dataclass
class AcquisitionFrame:
    time: np.ndarray
    channels: Dict[str, np.ndarray]
    differential: np.ndarray = field(default_factory=lambda: np.array([]))


class AcquisitionBuffer:
    def __init__(self, max_frames: int = 100):
        self.max_frames = max(1, int(max_frames))
        self.frames = []

    def append(self, frame: AcquisitionFrame):
        self.frames.append(frame)
        if len(self.frames) > self.max_frames:
            self.frames.pop(0)

    def latest(self) -> Optional[AcquisitionFrame]:
        if not self.frames:
            return None
        return self.frames[-1]

    def clear(self):
        self.frames.clear()


def clamp_samples(samples: int, max_samples: int = 5000) -> int:
    try:
        return max(16, min(int(samples), int(max_samples)))
    except Exception:
        return 1200


def capture_a1_a2(device, config: Optional[AcquisitionConfig] = None) -> Optional[AcquisitionFrame]:
    """
    Capture synchronized A1/A2 data using eyes17 capture2.

    eyes17 capture2 returns: x1, y1, x2, y2.
    """

    config = config or AcquisitionConfig()

    try:
        samples = clamp_samples(config.samples, config.max_samples)
        time_gap_us = max(1, int(config.time_gap_us))

        result = device.capture2(samples, time_gap_us)
        if result is None or len(result) < 4:
            return None

        x1, y1, _x2, y2 = result
        time_axis = np.asarray(x1, dtype=float)
        a1 = np.asarray(y1, dtype=float)
        a2 = np.asarray(y2, dtype=float)

        count = min(len(time_axis), len(a1), len(a2))
        if count < 2:
            return None

        time_axis = time_axis[:count]
        a1 = a1[:count]
        a2 = a2[:count]

        return AcquisitionFrame(
            time=time_axis,
            channels={
                config.channel_1: a1,
                config.channel_2: a2,
            },
            differential=a1 - a2,
        )

    except Exception as exc:
        print("Acquisition A1/A2 Error")
        print(exc)
        return None


def capture_single_channel(device, channel: str = "A1", samples: int = 1200, time_gap_us: int = 4):
    try:
        safe_samples = clamp_samples(samples, 10000)
        safe_time_gap = max(1, int(time_gap_us))
        result = device.capture1(channel, safe_samples, safe_time_gap)
        if result is None:
            return None, None
        x, y = result
        return np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    except Exception as exc:
        print("Single Channel Acquisition Error")
        print(exc)
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

        return {
            "vpp": vpp,
            "rms": rms,
            "peak": peak,
            "mean": mean,
            "frequency": frequency,
        }

    except Exception as exc:
        print("Measurement Calculation Error")
        print(exc)
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

        period_seconds = np.median(periods) * 1e-3
        if period_seconds <= 0:
            return 0.0

        return float(1.0 / period_seconds)

    except Exception:
        return 0.0


def calculate_current_from_sense(sense_voltage, sense_resistor_ohm: float = 100.0):
    try:
        safe_resistor = max(0.001, float(sense_resistor_ohm))
        return np.asarray(sense_voltage, dtype=float) / safe_resistor
    except Exception as exc:
        print("Current Calculation Error")
        print(exc)
        return np.array([])
