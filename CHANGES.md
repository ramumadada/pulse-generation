# Changelog

All changes made in this improvement pass, with the file, what changed, and why.

---

## fft_module.py

### Bug fix — division by zero in `calculate_thd`
**What:** Added a guard `if fundamental_mag == 0: return None` before the division.  
**Why:** When the signal is flat (DC input, wrong sample rate, or zero amplitude), `fundamental_mag` is 0. Python raises `ZeroDivisionError` which was silently swallowed by the caller's bare `except`, leaving the GUI with no THD value and no visible error to the user.

### Bug fix — harmonics detected past Nyquist in `detect_harmonics`
**What:** Added a `if target > nyquist: break` check before looking up each harmonic bin.  
**Why:** The function looked up bins for 2×f, 3×f … N×f with no limit. Above the Nyquist frequency (half the sample rate), `np.argmin` returns the last bin in the array — a completely wrong value. THD calculated from those spurious bins was silently incorrect.

### Bug fix — edge artefacts in `smooth_fft`
**What:** Replaced `np.convolve(..., mode='same')` with `scipy.signal.savgol_filter`.  
**Why:** `mode='same'` zero-pads both ends of the spectrum, creating fake humps over the first and last `window_size//2` samples. Peak detection near DC or near Nyquist would pick up these artefacts. `savgol_filter` fits a polynomial at each point and handles edges correctly.

### Refactor — deduplicate `detect_peak_frequency`
**What:** `detect_peak_frequency` now calls `detect_peak_marker` and discards the magnitude.  
**Why:** Both functions were copy-paste duplicates. Two copies of the same logic will silently diverge when one is changed.

### Style — removed excessive blank lines
**What:** Removed the blank line between every single statement.  
**Why:** The original style put a blank line before and after every statement, making a 15-line function appear as 60 lines. This is the most visible code quality issue to anyone reading the file.

### Added type hints
**What:** All public functions now have full argument and return type annotations.  
**Why:** Prevents unit confusion bugs (e.g. passing Hz where µs is expected) and enables IDE autocomplete across the codebase.

---

## save_module.py

### Bug fix — save paths relative to working directory
**What:** Introduced `BASE_DIR = Path(__file__).parent` and all file paths now use it.  
**Why:** The original code used bare relative paths like `"screenshots/"`, which resolved to wherever the user ran `python main_scope.py` from, not the project folder. Running the app from a different directory created folders in the wrong place or failed silently.

### Style — removed excessive blank lines, added type hints
**What:** Cleaned up the style to match the rest of the codebase.  
**Why:** Same reason as `fft_module.py` — every statement was surrounded by blank lines, making the file 3× longer than necessary.

---

## signal_conditioning_module.py

### Bug fix — edge artefacts in `moving_average`
**What:** Replaced `np.convolve(..., mode='same')` with `scipy.signal.savgol_filter`.  
**Why:** Same issue as `fft_module.smooth_fft` — zero-padding creates a false ramp at the start and end of every smoothed waveform trace.

### Performance fix — `low_pass_filter` Python loop replaced with scipy
**What:** Replaced the manual RC-filter `for` loop with `scipy.signal.butter` + `lfilter`.  
**Why:** The Python loop ran one iteration per sample. At 1200 samples refreshing at 20 fps, that is ~24 000 Python iterations per second inside the GUI thread. `scipy.signal.lfilter` does the same in C — orders of magnitude faster — and handles the filter initial conditions properly with no warm-up artefact at the start of each trace.

---

## acquisition_module.py

### Performance fix — `AcquisitionBuffer` now uses `collections.deque`
**What:** Changed `self.frames = []` with manual `pop(0)` to `deque(maxlen=self.max_frames)`.  
**Why:** `list.pop(0)` shifts every remaining element — it is O(n). At 20 fps with a 100-frame buffer this was 2 000 element copies per second. `deque` drops the oldest element automatically in O(1).

---

## arduino_serial_module.py

### Bug fix — replaced hardcoded 1.8 s boot delay with firmware token polling
**What:** Added `_wait_for_firmware_ready()` which reads serial lines until it sees the `"FW "` token the Arduino firmware sends on boot, with a 5 s timeout fallback.  
**Why:** The Arduino firmware already sends `"FW PGEE_ARDUINO_PULSE_ENGINE 1.0"` from `setup()` the moment it is ready. Python was ignoring this and sleeping a fixed 1.8 s. On slow bootloaders commands would arrive before the Arduino was ready and be dropped silently; on fast ones the 1.8 s was wasted every time the user reconnected.

---

## main_scope.py

### Architecture fix — hardware connection moved out of module scope
**What:** Removed `app = QApplication(sys.argv)` and `device = eyes17.eyes.open()` from the module top level. Moved them inside `if __name__ == "__main__":`. Passed `device` as a parameter to `UltraScope.__init__` and replaced all bare `device.xxx` calls with `self.device.xxx`.  
**Why:** When `device` was a module-level global, importing this file from a test, notebook, or IDE immediately tried to connect to hardware and called `sys.exit()` on failure. This made any unit testing of the GUI impossible and caused confusing crashes when the hardware was not plugged in during development.

---

## arduino_pulse_engine.ino

### Bug fix — replaced `String` with a fixed-size `char` buffer for serial parsing
**What:** Changed `String commandLine` to `char cmdBuf[128]` / `uint8_t cmdLen`. Serial characters are appended to the char array; a `String` is created once per complete command line to reuse the existing `handleCommand(String)` interface.  
**Why:** Arduino `String` performs heap allocation on every concatenation. On the UNO (2 KB SRAM total), repeated `String +=` over hours of experimentation causes heap fragmentation, which eventually leads to silent crashes or garbled commands arriving mid-experiment.

---

## requirements.txt

### All dependencies pinned to tested versions
**What:** Added exact version numbers for all five packages. Removed `eyes17` from the list. Added comments explaining why.  
**Why:** Unpinned deps install different versions on every fresh machine. A future PyQt5 or pyqtgraph minor release has previously broken oscilloscope layouts. `eyes17` is not on PyPI — listing it caused a confusing install failure on every new setup.

---

## Repository

### Added LICENSE (MIT)
**Why:** Without a LICENSE file, copyright defaults to "all rights reserved". Nobody can legally fork, cite, or build on the code even for academic research. MIT is the standard choice for university research projects.

### Added `.github/workflows/lint.yml`
**Why:** A `ruff` check on every push catches import errors, undefined names, and bare `except` blocks automatically before they land on main.

### Moved `arduinoC.py` → `legacy/arduinoC.py`
**Why:** This is an older standalone GUI that predates the current architecture. It is never imported by any current module but its presence at the root made the project look like it had two entry points, confusing new readers.

### Deleted `sample` file
**Why:** Empty leftover from the initial git commit. No content or purpose.

### Fixed README folder name (`waveform_exports/` → `waveform_data/`)
**Why:** The README listed `waveform_exports/` but the actual folder on disk is `waveform_data/`. Added a full installation section explaining how to install `eyes17` separately.
