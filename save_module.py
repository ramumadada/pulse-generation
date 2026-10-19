"""Save utilities — screenshots, waveform CSVs, FFT CSVs, experiment logs.

WHY CHANGED: the original file used bare relative paths like "screenshots/"
and "waveform_data/" which resolved to whatever directory the user ran Python
from, not the project folder. Running from a different directory silently
created folders in the wrong place or failed to write files. All paths now
resolve relative to this file using Path(__file__).parent.

Style: removed the excessive blank line between every statement that made
15-line functions appear as 60-line blocks.
"""

from __future__ import annotations

import csv
import datetime
from pathlib import Path

import pyqtgraph.exporters

BASE_DIR = Path(__file__).parent

_OUTPUT_DIRS = ["screenshots", "waveform_data", "fft_data", "experiment_logs"]


def _ensure_dirs() -> None:
    for name in _OUTPUT_DIRS:
        (BASE_DIR / name).mkdir(exist_ok=True)


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def save_cro_image(cro_plot) -> str | None:
    try:
        _ensure_dirs()
        filename = str(BASE_DIR / "screenshots" / f"CRO_{_timestamp()}.png")
        exporter = pyqtgraph.exporters.ImageExporter(cro_plot.plotItem)
        exporter.export(filename)
        return filename
    except Exception as e:
        print(f"Save CRO error: {e}")
        return None


def save_fft_image(fft_plot) -> str | None:
    try:
        _ensure_dirs()
        filename = str(BASE_DIR / "screenshots" / f"FFT_{_timestamp()}.png")
        exporter = pyqtgraph.exporters.ImageExporter(fft_plot.plotItem)
        exporter.export(filename)
        return filename
    except Exception as e:
        print(f"Save FFT error: {e}")
        return None


def save_waveform_csv(x, y) -> str | None:
    try:
        _ensure_dirs()
        filename = str(BASE_DIR / "waveform_data" / f"WAVEFORM_{_timestamp()}.csv")
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Time(us)", "Voltage(V)"])
            writer.writerows(zip(x, y))
        return filename
    except Exception as e:
        print(f"Waveform CSV error: {e}")
        return None


def save_fft_csv(xf, yf) -> str | None:
    try:
        _ensure_dirs()
        filename = str(BASE_DIR / "fft_data" / f"FFT_{_timestamp()}.csv")
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Frequency(Hz)", "Magnitude"])
            writer.writerows(zip(xf, yf))
        return filename
    except Exception as e:
        print(f"FFT CSV error: {e}")
        return None


def save_experiment_log(pin, frequency, duty, amplitude, thd) -> str | None:
    try:
        _ensure_dirs()
        ts = _timestamp()
        filename = str(BASE_DIR / "experiment_logs" / f"LOG_{ts}.txt")
        thd_str = f"{thd:.2f} %" if thd is not None else "N/A"
        with open(filename, "w") as f:
            f.write("EXPERIMENT LOG\n")
            f.write("=====================\n")
            f.write(f"Timestamp : {ts}\n")
            f.write(f"Pin       : {pin}\n")
            f.write(f"Frequency : {frequency} Hz\n")
            f.write(f"Duty      : {duty} %\n")
            f.write(f"Amplitude : {amplitude} V\n")
            f.write(f"THD       : {thd_str}\n")
        return filename
    except Exception as e:
        print(f"Experiment log error: {e}")
        return None


def save_dual_waveform_csv(x, a1, a2=None, differential=None) -> str | None:
    try:
        _ensure_dirs()
        filename = str(BASE_DIR / "waveform_data" / f"DUAL_WAVEFORM_{_timestamp()}.csv")
        a2 = a2 if a2 is not None else []
        differential = differential if differential is not None else []
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Time(ms)", "A1(V)", "A2(V)", "A1_minus_A2(V)"])
            for i in range(len(x)):
                writer.writerow([
                    x[i],
                    a1[i] if i < len(a1) else "",
                    a2[i] if i < len(a2) else "",
                    differential[i] if i < len(differential) else "",
                ])
        return filename
    except Exception as e:
        print(f"Dual waveform CSV error: {e}")
        return None
