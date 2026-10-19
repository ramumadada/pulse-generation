"""FFT analysis utilities for the pulse generation platform."""

from __future__ import annotations

import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import savgol_filter


def apply_window(y: np.ndarray, window_type: str = "hanning") -> np.ndarray:
    """Multiply signal by a spectral window to reduce leakage."""
    N = len(y)
    if window_type == "hanning":
        window = np.hanning(N)
    elif window_type == "hamming":
        window = np.hamming(N)
    elif window_type == "blackman":
        window = np.blackman(N)
    else:
        window = np.ones(N)
    return y * window


def smooth_fft(yf: np.ndarray, window_size: int = 5) -> np.ndarray:
    """Smooth an FFT magnitude spectrum using Savitzky-Golay filter.

    WHY CHANGED: previously used np.convolve(..., mode='same') which
    zero-pads both ends of the spectrum, creating fake artefact humps near
    DC and near Nyquist. savgol_filter fits a polynomial at each point and
    handles edge samples correctly — no zero-padding artefacts.
    """
    w = max(3, window_size if window_size % 2 == 1 else window_size + 1)
    if len(yf) < w:
        return yf
    return savgol_filter(yf, window_length=w, polyorder=2)


def calculate_fft(
    y: np.ndarray,
    time_gap: float,
    window_type: str = "hanning",
    smooth: bool = True,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Compute one-sided FFT magnitude spectrum.

    Args:
        y: voltage samples array
        time_gap: sample spacing in microseconds
        window_type: spectral window — hanning / hamming / blackman
        smooth: apply Savitzky-Golay smoothing after transform

    Returns:
        (frequencies_hz, magnitudes) or (None, None) on bad input
    """
    try:
        if y is None or len(y) == 0:
            return None, None

        y = apply_window(y, window_type)
        N = len(y)
        yf = fft(y)
        xf = fftfreq(N, time_gap * 1e-6)

        positive = xf >= 0
        xf = xf[positive]
        yf = np.abs(yf[positive])

        if smooth:
            yf = smooth_fft(yf)

        return xf, yf

    except Exception as e:
        print(f"FFT error: {e}")
        return None, None


def detect_peak_marker(
    xf: np.ndarray, yf: np.ndarray
) -> tuple[float, float]:
    """Return (frequency_hz, magnitude) of the strongest non-DC bin."""
    peak_index = int(np.argmax(yf[1:])) + 1
    return float(xf[peak_index]), float(yf[peak_index])


def detect_peak_frequency(xf: np.ndarray, yf: np.ndarray) -> float:
    """Return the frequency of the strongest non-DC bin.

    WHY CHANGED: was a copy-paste duplicate of detect_peak_marker.
    Now delegates to it so the two functions can never diverge.
    """
    freq, _ = detect_peak_marker(xf, yf)
    return freq


def detect_harmonics(
    xf: np.ndarray,
    yf: np.ndarray,
    fundamental_freq: float,
    harmonics: int = 5,
) -> list[tuple[float, float]]:
    """Return (frequency, magnitude) pairs for harmonics 1 through N.

    WHY CHANGED: previously looked up bins for every harmonic regardless
    of whether the frequency exceeded Nyquist. Above Nyquist, argmin
    returns the last bin — a completely wrong value that silently corrupted
    THD. Now stops as soon as the next harmonic would exceed the Nyquist
    limit (the last frequency in xf).
    """
    nyquist = float(xf[-1])
    harmonic_data = []
    for n in range(1, harmonics + 1):
        target = fundamental_freq * n
        if target > nyquist:
            break
        index = int(np.argmin(np.abs(xf - target)))
        harmonic_data.append((float(xf[index]), float(yf[index])))
    return harmonic_data


def calculate_thd(
    xf: np.ndarray,
    yf: np.ndarray,
    fundamental_freq: float,
    harmonics: int = 5,
) -> float | None:
    """Compute Total Harmonic Distortion as a percentage.

    Returns None when the fundamental magnitude is zero (flat signal, DC
    input, or wrong sample rate) instead of crashing with ZeroDivisionError.

    WHY CHANGED: fundamental_mag could be 0, causing ZeroDivisionError that
    was silently swallowed by the caller, leaving the GUI with no THD value
    and no visible error.
    """
    harmonic_data = detect_harmonics(xf, yf, fundamental_freq, harmonics)
    if not harmonic_data:
        return None

    fundamental_mag = harmonic_data[0][1]
    if fundamental_mag == 0:
        return None  # undefined for a zero-amplitude fundamental

    harmonic_power = sum(mag ** 2 for _, mag in harmonic_data[1:])
    return float(np.sqrt(harmonic_power) / fundamental_mag * 100)
