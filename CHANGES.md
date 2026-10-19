# Changelog

All changes made in this improvement pass, with the file, what changed, and why.

---

## SEELab (eyes17) removal — Arduino-only architecture

**Summary:** The project previously used a SEELab (eyes17) USB lab instrument for ADC capture,
voltage generation (PV1/PV2), and signal generation (SQR1/SQR2/WG). That device has been
removed. All acquisition and voltage output now uses the Arduino's built-in hardware.

**Why removed:** The hardware in use is an Arduino UNO, not a SEELab. Keeping an eyes17
dependency that can never connect causes import errors, makes setup harder, and adds dead code.

### arduino_pulse_engine.ino — new ADC commands
**What:** Added three new serial command handlers: `SAMPLE`, `READ_ADC`, `SET_VOLTAGE`.  
`SAMPLE CH=A0,A1 COUNT=300 GAP_US=500` streams CSV rows of raw ADC values.  
`READ_ADC CH=A0` returns a single voltage reading.  
`SET_VOLTAGE PIN=5 DUTY=127` sets a PWM duty cycle (RC-filter to DC bias).  
Also added `parseAnalogPin()` helper and `doSample()` streaming function.  
**Why:** These are the primitives the Python layer needs. All acquisition and bias voltage
now goes through these commands instead of the SEELab protocol.

**Bug fix also included:** Changed `String commandLine` (global) to `char cmdBuf[128]` to
eliminate Arduino heap fragmentation caused by repeated `String` concatenation in the receive loop.

### arduino_serial_module.py — sample and voltage API
**What:** Added `ArduinoSampleConfig` dataclass and four new methods:
`request_sample()`, `read_sample_data()`, `read_adc_voltage()`, `set_voltage_pwm()`.
Also replaced the hardcoded `1.8 s` boot sleep with `_wait_for_firmware_ready()`,
which polls for the `FW PGEE_ARDUINO_PULSE_ENGINE 1.0` token.  
**Why:** These are the direct replacements for the SEELab `device.capture2()`,
`device.get_voltage()`, and `device.set_pv1()` calls. Boot polling is more reliable
than a fixed delay on slower machines.

### acquisition_module.py — full rewrite
**What:** Removed all `eyes17` imports. `capture_a1_a2()` and `capture_single_channel()`
now send the Arduino `SAMPLE` command and parse the streamed CSV back into NumPy arrays.
`AcquisitionBuffer` changed from `list.pop(0)` to `collections.deque` for O(1) eviction.  
**Why:** Was `device.capture2()` / `device.capture1()` — those no longer exist.

### trigger_module.py — rename device → arduino
**What:** `update_scope_engine(self, device)` renamed to `update_scope_engine(self, arduino)`.
Call sites inside the function updated to match.  
**Why:** The parameter is now an `ArduinoSerialController`, not a SEELab device object.

### pulse_train_module.py — removed device parameter
**What:** Removed `device=None` from `identical_pulses`, `incremental_amplitude_pulses`,
and `burst_pulses`. Removed the `device.set_pv1()` call in `incremental_amplitude_pulses`.  
**Why:** Voltage stepping is now done by the GUI layer via `arduino.set_voltage_pwm()`.

### main_scope.py — removed eyes17 import and device= arg
**What:** Removed `import eyes17.eyes` and `device = eyes17.eyes.open()`.
Removed `device=` parameter from `UltraScope.__init__`.
Voltage outputs changed from `device.set_pv1/pv2` to `arduino.set_voltage_pwm(pin, v)`.
Signal generation changed from `device.set_sqr1/sqr2/wave` to `ArduinoPWMConfig` on pin 9.
Scope timer changed from `trigger_module.update_scope_engine(self.device)` to `(self.arduino)`.  
**Why:** All references to the SEELab device removed; the Arduino controller handles everything.

### iv_module.py — full SEELab migration
**What:**
- Removed `import eyes17.eyes` and module-level `device = eyes17.eyes.open()`.
- Added `import arduino_serial_module` and `import acquisition_module`.
- `iv_worker`: replaced `device.set_pv1(v)` → `arduino.set_voltage_pwm(5, v)`;
  `device.set_sqr1(1000, 50)` → `arduino.configure_pulse()` + `start_pulse()`;
  `device.get_voltage('A1/A2')` → `arduino.read_adc_voltage('A0/A1')`;
  `device.set_state(SQR1=0)` → `arduino.stop_pwm()`.
- `stop_iv`: same `set_state` → `stop_pwm` replacement.
- `update_scope`: `device.capture1('A1', ...)` → `acquisition_module.capture_single_channel(arduino, 'A0', ...)`.
- Moved `QApplication(sys.argv)` and `window.show()` inside `if __name__ == "__main__":` guard.
- Reduced `SAMPLES` 1000 → 300, `TIME_GAP` 4 → 500 µs (Arduino serial reliable limit).  
**Why:** Module-level `device.xxx` calls caused `ImportError` at import time if eyes17 was absent.
The `__main__` guard prevents the window from launching when the module is imported by another widget.

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
