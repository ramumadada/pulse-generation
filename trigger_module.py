import numpy as np

import acquisition_module
import fft_module
import signal_conditioning_module


# ==========================================================
# DISPLAY TRIGGER ALIGNMENT
# ==========================================================

def apply_display_trigger(self, x, y, y2, y_diff):

    try:

        if not getattr(self, "trigger_enabled", False):
            return x, y, y2, y_diff

        source_name = getattr(self, "trigger_source", "A1")
        level = getattr(self, "trigger_level_volts", 0.0)
        edge = getattr(self, "trigger_edge", "Rising")

        if source_name == "A2" and y2 is not None:
            source = y2
        elif source_name == "DIFF" and y_diff is not None:
            source = y_diff
        else:
            source = y

        if source is None or len(source) < 4:
            return x, y, y2, y_diff

        if edge == "Falling":
            crossings = np.where(
                (source[:-1] > level) & (source[1:] <= level)
            )[0]
        else:
            crossings = np.where(
                (source[:-1] < level) & (source[1:] >= level)
            )[0]

        if len(crossings) == 0:
            return x, y, y2, y_diff

        target_index = int(len(source) * 0.25)
        shift = target_index - int(crossings[0])

        y = np.roll(y, shift)

        if y2 is not None:
            y2 = np.roll(y2, shift)

        if y_diff is not None:
            y_diff = np.roll(y_diff, shift)

        return x, y, y2, y_diff

    except Exception as exc:

        print("Display Trigger Error")
        print(exc)
        return x, y, y2, y_diff


# ==========================================================
# CRO VISIBILITY
# ==========================================================

def update_cro_display(self, x, y, y2, y_diff):

    try:

        mode = "Overlay"

        if hasattr(self, "scope_display_mode"):
            mode = self.scope_display_mode.currentText()

        show_a1 = getattr(self, "show_a1_checkbox", None)
        show_a2 = getattr(self, "show_a2_checkbox", None)
        show_diff = getattr(self, "show_diff_checkbox", None)

        show_a1 = True if show_a1 is None else show_a1.isChecked()
        show_a2 = True if show_a2 is None else show_a2.isChecked()
        show_diff = True if show_diff is None else show_diff.isChecked()

        if mode == "A1 Only":
            show_a1 = True
            show_a2 = False
            show_diff = False
        elif mode == "A2 Only":
            show_a1 = False
            show_a2 = True
            show_diff = False
        elif mode == "Differential":
            show_a1 = False
            show_a2 = False
            show_diff = True

        self.cro_curve.setData(
            x if show_a1 else [],
            y if show_a1 else []
        )

        if hasattr(self, "cro_curve_a2"):
            self.cro_curve_a2.setData(
                x if show_a2 and y2 is not None else [],
                y2 if show_a2 and y2 is not None else []
            )

        if hasattr(self, "cro_curve_diff"):
            self.cro_curve_diff.setData(
                x if show_diff and y_diff is not None else [],
                y_diff if show_diff and y_diff is not None else []
            )

    except Exception as exc:

        print("CRO Display Error")
        print(exc)


# ==========================================================
# MINI PIP SCOPE
# ==========================================================

def update_pip_scope(self, x, y, y2, y_diff):

    try:

        if not hasattr(self, "pip_curve_a1"):
            return

        self.pip_curve_a1.setData(
            x,
            y
        )

        if hasattr(self, "pip_curve_a2"):
            self.pip_curve_a2.setData(
                x if y2 is not None else [],
                y2 if y2 is not None else []
            )

        if hasattr(self, "pip_curve_diff"):
            self.pip_curve_diff.setData(
                x if y_diff is not None else [],
                y_diff if y_diff is not None else []
            )

        if hasattr(self, "pip_status_label"):
            self.pip_status_label.setText(
                "PiP live: A1 / A2 / A1-A2"
            )

    except Exception as exc:

        print("PiP Scope Error")
        print(exc)


# ==========================================================
# UPDATE SCOPE ENGINE
# ==========================================================

def update_scope_engine(self, device):

    try:

        # ==================================================
        # FREEZE CHECK
        # ==================================================

        if self.freeze_display:
            return

        # ==================================================
        # DUAL-CHANNEL CAPTURE
        # ==================================================

        frame = acquisition_module.capture_a1_a2(
            device,
            acquisition_module.AcquisitionConfig(
                samples=self.SAMPLES,
                time_gap_us=self.TIME_GAP,
            )
        )

        if frame is not None:

            x = frame.time

            y = frame.channels.get("A1")

            y2 = frame.channels.get("A2")

            y_diff = frame.differential

        else:

            x, y = acquisition_module.capture_single_channel(
                device,
                "A1",
                self.SAMPLES,
                self.TIME_GAP
            )

            y2 = None

            y_diff = None

        # ==================================================
        # INVALID DATA CHECK
        # ==================================================

        if x is None or y is None:
            return

        if len(x) == 0 or len(y) == 0:
            return

        # ==================================================
        # OPTIONAL CONDITIONING
        # ==================================================

        sample_rate_hz = 1_000_000 / max(1, self.TIME_GAP)

        y = signal_conditioning_module.condition_waveform(
            y,
            sample_rate_hz,
            remove_offset=False,
            baseline=False,
            moving_average_window=0,
            low_pass_cutoff_hz=0,
            noise_compensation=False,
        )

        if y2 is not None:

            y2 = signal_conditioning_module.condition_waveform(
                y2,
                sample_rate_hz,
                remove_offset=False,
                baseline=False,
                moving_average_window=0,
                low_pass_cutoff_hz=0,
                noise_compensation=False,
            )

            y_diff = y - y2

        x, y, y2, y_diff = apply_display_trigger(
            self,
            x,
            y,
            y2,
            y_diff
        )

        # ==================================================
        # STORE WAVEFORM DATA
        # ==================================================

        self.last_x = x
        self.last_y = y
        self.last_a1 = y
        self.last_a2 = y2
        self.last_diff = y_diff

        # ==================================================
        # CRO DISPLAY
        # ==================================================

        update_cro_display(
            self,
            x,
            y,
            y2,
            y_diff
        )

        update_pip_scope(
            self,
            x,
            y,
            y2,
            y_diff
        )

        self.cro_plot.enableAutoRange(
            axis='y'
        )

        # ==================================================
        # FFT CALCULATION
        # ==================================================

        xf, yf = fft_module.calculate_fft(

            y,

            self.TIME_GAP,

            window_type="hanning",

            smooth=True

        )

        # ==================================================
        # INVALID FFT CHECK
        # ==================================================

        if xf is None or yf is None:
            return

        if len(xf) < 2 or len(yf) < 2:
            return

        # ==================================================
        # STORE FFT DATA
        # ==================================================

        self.last_fft_x = xf
        self.last_fft_y = yf

        # ==================================================
        # FFT DISPLAY
        # ==================================================

        self.fft_curve.setData(
            xf,
            yf
        )

        self.fft_plot.setXRange(

            0,

            max(
                1000,
                self.freq_slider.value() * 5
            )

        )

        self.fft_plot.enableAutoRange(
            axis='y'
        )

        # ==================================================
        # PEAK DETECTION
        # ==================================================

        peak_freq = fft_module.detect_peak_frequency(
            xf,
            yf
        )

        peak_x, peak_y = fft_module.detect_peak_marker(
            xf,
            yf
        )

        self.fft_peak_marker.setData(
            [peak_x],
            [peak_y]
        )

        # ==================================================
        # THD
        # ==================================================

        thd = fft_module.calculate_thd(

            xf,

            yf,

            peak_freq,

            harmonics=5

        )

        # ==================================================
        # MEASUREMENTS
        # ==================================================

        measurements = acquisition_module.calculate_measurements(
            x,
            y
        )

        vpp = measurements.get("vpp", 0.0)

        rms = measurements.get("rms", 0.0)

        peak = measurements.get("peak", 0.0)

        if y2 is not None:

            current = acquisition_module.calculate_current_from_sense(
                y2,
                getattr(self, "sense_resistor_ohm", 100.0)
            )

            current_ma = float(np.max(np.abs(current)) * 1000) if len(current) else 0.0

        else:

            current_ma = 0.0

        # ==================================================
        # UPDATE LABELS
        # ==================================================

        self.vpp_label.setText(
            f"Vpp : {vpp:.2f} V"
        )

        self.rms_label.setText(
            f"RMS : {rms:.2f} V"
        )

        self.peak_label.setText(
            f"Peak : {peak:.2f} V"
        )

        self.current_label.setText(
            f"Current : {current_ma:.2f} mA"
        )

        self.freq_label.setText(
            f"Freq : {peak_freq:.2f} Hz"
        )

        # ==================================================
        # STATUS LABEL
        # ==================================================

        self.warning_label.setText(
            f"Scope Running | THD : {thd:.2f}%"
        )

        self.warning_label.setStyleSheet(
            "color:lime;"
        )

    except Exception as e:

        print("Trigger Module Error")

        print(e)

        self.warning_label.setText(
            str(e)
        )

        self.warning_label.setStyleSheet(
            "color:red;"
        )
