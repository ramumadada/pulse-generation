"""
Signal conditioning module.

Reusable DSP utilities for the instrumentation platform.  Keep this module free
of GUI code so oscilloscope, FFT, IV, and memristor modules can share it.
"""

from __future__ import annotations

import numpy as np


def sanitize_waveform(y):
    try:
        data = np.asarray(y, dtype=float)
        if len(data) == 0:
            return data

        finite = np.isfinite(data)
        if finite.all():
            return data

        fallback = np.nanmedian(data[finite]) if finite.any() else 0.0
        return np.where(finite, data, fallback)

    except Exception as exc:
        print("Waveform Sanitize Error")
        print(exc)
        return np.array([])


def remove_dc_offset(y):
    try:
        data = sanitize_waveform(y)
        if len(data) == 0:
            return data
        return data - np.mean(data)
    except Exception as exc:
        print("DC Offset Removal Error")
        print(exc)
        return sanitize_waveform(y)


def baseline_correction(y, baseline_fraction=0.08):
    try:
        data = sanitize_waveform(y)
        if len(data) == 0:
            return data

        fraction = min(max(float(baseline_fraction), 0.01), 0.5)
        count = max(1, int(len(data) * fraction))
        baseline = np.median(data[:count])
        return data - baseline

    except Exception as exc:
        print("Baseline Correction Error")
        print(exc)
        return sanitize_waveform(y)


def moving_average(y, window_size=5):
    try:
        data = sanitize_waveform(y)
        window = max(1, int(window_size))
        if window <= 1 or len(data) < window:
            return data

        kernel = np.ones(window) / window
        return np.convolve(data, kernel, mode="same")

    except Exception as exc:
        print("Moving Average Error")
        print(exc)
        return sanitize_waveform(y)


def low_pass_filter(y, sample_rate_hz, cutoff_hz):
    try:
        data = sanitize_waveform(y)
        if len(data) < 2:
            return data

        sample_rate = max(1.0, float(sample_rate_hz))
        cutoff = max(0.001, float(cutoff_hz))
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * np.pi * cutoff)
        alpha = dt / (rc + dt)

        output = np.empty_like(data)
        output[0] = data[0]
        for index in range(1, len(data)):
            output[index] = output[index - 1] + alpha * (data[index] - output[index - 1])

        return output

    except Exception as exc:
        print("Low Pass Filter Error")
        print(exc)
        return sanitize_waveform(y)


def estimate_noise_floor(y):
    try:
        data = sanitize_waveform(y)
        if len(data) == 0:
            return 0.0

        median = np.median(data)
        mad = np.median(np.abs(data - median))
        return float(1.4826 * mad)

    except Exception as exc:
        print("Noise Floor Error")
        print(exc)
        return 0.0


def compensate_noise(y, threshold=None):
    try:
        data = sanitize_waveform(y)
        if threshold is None:
            threshold = estimate_noise_floor(data)

        threshold = max(0.0, float(threshold))
        return np.where(np.abs(data) < threshold, 0.0, data)

    except Exception as exc:
        print("Noise Compensation Error")
        print(exc)
        return sanitize_waveform(y)


def condition_waveform(
    y,
    sample_rate_hz,
    remove_offset=False,
    baseline=False,
    moving_average_window=0,
    low_pass_cutoff_hz=0,
    noise_compensation=False,
):
    try:
        data = sanitize_waveform(y)

        if remove_offset:
            data = remove_dc_offset(data)

        if baseline:
            data = baseline_correction(data)

        if moving_average_window and moving_average_window > 1:
            data = moving_average(data, moving_average_window)

        if low_pass_cutoff_hz and low_pass_cutoff_hz > 0:
            data = low_pass_filter(data, sample_rate_hz, low_pass_cutoff_hz)

        if noise_compensation:
            data = compensate_noise(data)

        return data

    except Exception as exc:
        print("Signal Conditioning Error")
        print(exc)
        return sanitize_waveform(y)
