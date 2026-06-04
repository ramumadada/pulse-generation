import sys

# ==========================================================
# QApplication MUST BE FIRST
# ==========================================================

from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)

# ==========================================================
# IMPORTS
# ==========================================================

import numpy as np
import pyqtgraph as pg

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QSlider,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLCDNumber,
    QFrame
)

from PyQt5.QtCore import Qt, QTimer

from scipy.fft import fft, fftfreq

# ==========================================================
# IMPORT EYES17 AFTER QApplication
# ==========================================================

try:

    import eyes17.eyes

except Exception as e:

    print("eyes17 Import Error")
    print(e)

    sys.exit()

# ==========================================================
# CONNECT SEELAB
# ==========================================================

try:

    device = eyes17.eyes.open()

    print("SEELab Connected Successfully")

except Exception as e:

    print("SEELab Connection Error")
    print(e)

    sys.exit()

# ==========================================================
# PIN LIMITS
# ==========================================================

PIN_LIMITS = {

    "SQ1": {

        "freq_min": 1,
        "freq_max": 100000,

        "amp_min": 0,
        "amp_max": 5000,

        "duty_min": 1,
        "duty_max": 99,

        "description":
        "Digital Square Pulse Output"
    },

    "SQ2": {

        "freq_min": 1,
        "freq_max": 100000,

        "amp_min": 0,
        "amp_max": 5000,

        "duty_min": 1,
        "duty_max": 99,

        "description":
        "Secondary Square Pulse Output"
    },

    "WG": {

        "freq_min": 1,
        "freq_max": 5000,

        "amp_min": 0,
        "amp_max": 3000,

        "duty_min": 50,
        "duty_max": 50,

        "description":
        "Analog Wave Generator"
    }
}

# ==========================================================
# MAIN WINDOW
# ==========================================================

class UltraScope(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "ADVANCED DIGITAL PROCESSING OSCILLOSCOPE"
        )

        self.resize(1900, 1000)

        self.setStyleSheet("""

            QWidget{
                background:#0b0b0b;
                color:white;
                font-size:13px;
            }

            QLabel{
                color:white;
                font-weight:bold;
            }

            QPushButton{
                background:#202020;
                border:1px solid #404040;
                padding:8px;
                border-radius:5px;
            }

            QPushButton:hover{
                background:#404040;
            }

            QComboBox{
                background:#202020;
                padding:5px;
            }

        """)

        self.freeze_display = False

        # ==================================================
        # SAFE VALUES FOR SEELAB
        # ==================================================

        self.SAMPLES = 300

        self.TIME_GAP = 20

        self.scope_speed = 150

        # ==================================================
        # MAIN LAYOUT
        # ==================================================

        main_layout = QVBoxLayout()

        # ==================================================
        # TOP CONTROLS
        # ==================================================

        top_layout = QGridLayout()

        # ==================================================
        # PIN SELECT
        # ==================================================

        self.pin_select = QComboBox()

        self.pin_select.addItems([
            "SQ1",
            "SQ2",
            "WG"
        ])

        self.pin_select.currentIndexChanged.connect(
            self.update_pin_constraints
        )

        # ==================================================
        # FREQUENCY
        # ==================================================

        self.freq_slider = QSlider(
            Qt.Horizontal
        )

        self.freq_display = QLCDNumber()

        self.freq_display.setDigitCount(8)

        self.freq_slider.valueChanged.connect(
            self.update_generator
        )

        # ==================================================
        # DUTY
        # ==================================================

        self.duty_slider = QSlider(
            Qt.Horizontal
        )

        self.duty_display = QLCDNumber()

        self.duty_slider.valueChanged.connect(
            self.update_generator
        )

        # ==================================================
        # AMPLITUDE
        # ==================================================

        self.amp_slider = QSlider(
            Qt.Horizontal
        )

        self.amp_display = QLCDNumber()

        self.amp_slider.valueChanged.connect(
            self.update_generator
        )

        # ==================================================
        # SPEED
        # ==================================================

        self.speed_slider = QSlider(
            Qt.Horizontal
        )

        self.speed_slider.setMinimum(50)

        self.speed_slider.setMaximum(500)

        self.speed_slider.setValue(150)

        self.speed_slider.valueChanged.connect(
            self.update_speed
        )

        self.speed_display = QLCDNumber()

        self.speed_display.display(150)

        # ==================================================
        # FREEZE
        # ==================================================

        self.freeze_btn = QPushButton(
            "Freeze"
        )

        self.freeze_btn.clicked.connect(
            self.freeze_scope
        )

        # ==================================================
        # WARNING LABEL
        # ==================================================

        self.warning_label = QLabel(
            "SAFE OPERATION"
        )

        self.warning_label.setStyleSheet(
            "color:lime;"
        )

        # ==================================================
        # PIN INFO
        # ==================================================

        self.pin_info = QLabel()

        self.pin_info.setStyleSheet(
            "color:cyan;"
        )

        # ==================================================
        # PV1 CONTROL
        # ==================================================

        self.pv1_slider = QSlider(Qt.Horizontal)

        self.pv1_slider.setMinimum(0)

        self.pv1_slider.setMaximum(5000)

        self.pv1_slider.setValue(0)

        self.pv1_display = QLCDNumber()

        self.pv1_display.display(0)

        self.pv1_slider.valueChanged.connect(
            self.update_pv_outputs
        )

        # ==================================================
        # PV2 CONTROL
        # ==================================================

        self.pv2_slider = QSlider(Qt.Horizontal)

        self.pv2_slider.setMinimum(-3300)

        self.pv2_slider.setMaximum(3300)

        self.pv2_slider.setValue(0)

        self.pv2_display = QLCDNumber()

        self.pv2_display.display(0)

        self.pv2_slider.valueChanged.connect(
            self.update_pv_outputs
        )

        # ==================================================
        # ADD CONTROLS
        # ==================================================

        top_layout.addWidget(QLabel("Pin"),0,0)
        top_layout.addWidget(self.pin_select,0,1)

        top_layout.addWidget(QLabel("Frequency"),1,0)
        top_layout.addWidget(self.freq_slider,1,1)
        top_layout.addWidget(self.freq_display,1,2)

        top_layout.addWidget(QLabel("Duty"),2,0)
        top_layout.addWidget(self.duty_slider,2,1)
        top_layout.addWidget(self.duty_display,2,2)

        top_layout.addWidget(QLabel("Amplitude"),3,0)
        top_layout.addWidget(self.amp_slider,3,1)
        top_layout.addWidget(self.amp_display,3,2)

        top_layout.addWidget(QLabel("Scope Speed"),4,0)
        top_layout.addWidget(self.speed_slider,4,1)
        top_layout.addWidget(self.speed_display,4,2)

        top_layout.addWidget(self.warning_label,5,0)
        top_layout.addWidget(self.pin_info,5,1)
        top_layout.addWidget(self.freeze_btn,5,2)

        top_layout.addWidget(QLabel("PV1 Voltage"),6,0)
        top_layout.addWidget(self.pv1_slider,6,1)
        top_layout.addWidget(self.pv1_display,6,2)

        top_layout.addWidget(QLabel("PV2 Voltage"),7,0)
        top_layout.addWidget(self.pv2_slider,7,1)
        top_layout.addWidget(self.pv2_display,7,2)

        # ==================================================
        # CENTER AREA
        # ==================================================

        center_layout = QHBoxLayout()

        # ==================================================
        # LEFT PANEL
        # ==================================================

        left_panel = QFrame()

        left_panel.setStyleSheet(
            "background:#111111;"
        )

        left_layout = QVBoxLayout()

        self.vpp_label = QLabel("Vpp : 0 V")
        self.vpp_label.setStyleSheet(
            "color:yellow;font-size:26px;"
        )

        self.rms_label = QLabel("RMS : 0 V")
        self.rms_label.setStyleSheet(
            "color:yellow;font-size:26px;"
        )

        self.peak_label = QLabel("Peak : 0 V")
        self.peak_label.setStyleSheet(
            "color:yellow;font-size:26px;"
        )

        self.current_label = QLabel("Current : 0 mA")
        self.current_label.setStyleSheet(
            "color:cyan;font-size:26px;"
        )

        self.freq_label = QLabel("Freq : 0 Hz")
        self.freq_label.setStyleSheet(
            "color:lime;font-size:26px;"
        )

        left_layout.addWidget(self.vpp_label)
        left_layout.addSpacing(30)

        left_layout.addWidget(self.rms_label)
        left_layout.addSpacing(30)

        left_layout.addWidget(self.peak_label)
        left_layout.addSpacing(30)

        left_layout.addWidget(self.current_label)
        left_layout.addSpacing(30)

        left_layout.addWidget(self.freq_label)

        left_panel.setLayout(left_layout)

        # ==================================================
        # CRO
        # ==================================================

        self.cro_plot = pg.PlotWidget()

        self.cro_plot.setBackground('k')

        self.cro_plot.showGrid(
            x=True,
            y=True
        )

        self.cro_plot.setTitle(
            "REAL TIME CRO"
        )

        self.cro_plot.setLabel(
            'left',
            'Voltage (V)'
        )

        self.cro_plot.setLabel(
            'bottom',
            'Time (us)'
        )

        self.cro_curve = self.cro_plot.plot(
            pen=pg.mkPen(
                'y',
                width=2
            )
        )

        # ==================================================
        # FFT
        # ==================================================

        self.fft_plot = pg.PlotWidget()

        self.fft_plot.setBackground('k')

        self.fft_plot.showGrid(
            x=True,
            y=True
        )

        self.fft_plot.setTitle(
            "FFT SPECTRUM ANALYZER"
        )

        self.fft_plot.setLabel(
            'left',
            'Magnitude'
        )

        self.fft_plot.setLabel(
            'bottom',
            'Frequency (Hz)'
        )

        self.fft_curve = self.fft_plot.plot(
            pen=pg.mkPen(
                'c',
                width=2
            )
        )

        # ==================================================
        # ADD CENTER
        # ==================================================

        center_layout.addWidget(
            left_panel,
            1
        )

        center_layout.addWidget(
            self.cro_plot,
            4
        )

        center_layout.addWidget(
            self.fft_plot,
            4
        )

        # ==================================================
        # MAIN ADD
        # ==================================================

        main_layout.addLayout(
            top_layout
        )

        main_layout.addLayout(
            center_layout
        )

        self.setLayout(
            main_layout
        )

        # ==================================================
        # TIMER
        # ==================================================

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_scope
        )

        self.timer.start(
            self.scope_speed
        )

        # ==================================================
        # INITIALIZE
        # ==================================================

        self.update_pin_constraints()

    # ======================================================
    # PIN CONSTRAINTS
    # ======================================================

    def update_pin_constraints(self):

        try:

            pin = self.pin_select.currentText()

            limits = PIN_LIMITS[pin]

            self.freq_slider.setMinimum(
                limits["freq_min"]
            )

            self.freq_slider.setMaximum(
                limits["freq_max"]
            )

            self.freq_slider.setValue(
                limits["freq_min"]
            )

            self.amp_slider.setMinimum(
                limits["amp_min"]
            )

            self.amp_slider.setMaximum(
                limits["amp_max"]
            )

            self.amp_slider.setValue(
                int(limits["amp_max"] / 2)
            )

            self.duty_slider.setMinimum(
                limits["duty_min"]
            )

            self.duty_slider.setMaximum(
                limits["duty_max"]
            )

            self.duty_slider.setValue(50)

            self.pin_info.setText(

                f"{pin} | "
                f"Max Frequency : "
                f"{limits['freq_max']} Hz | "
                f"Max Amplitude : "
                f"{limits['amp_max']/1000:.2f} V"

            )

            self.update_generator()

        except Exception as e:

            print(e)

    # ======================================================
    # SPEED UPDATE
    # ======================================================

    def update_speed(self):

        self.scope_speed = (
            self.speed_slider.value()
        )

        self.speed_display.display(
            self.scope_speed
        )

        self.timer.start(
            self.scope_speed
        )

    # ======================================================
    # FREEZE
    # ======================================================

    def freeze_scope(self):

        self.freeze_display = (
            not self.freeze_display
        )

        if self.freeze_display:

            self.freeze_btn.setText(
                "Resume"
            )

        else:

            self.freeze_btn.setText(
                "Freeze"
            )

    # ======================================================
    # GENERATOR UPDATE
    # ======================================================

    def update_generator(self):

        try:

            pin = self.pin_select.currentText()

            freq = self.freq_slider.value()

            duty = self.duty_slider.value()

            amp_mv = self.amp_slider.value()

            amplitude = amp_mv / 1000

            self.freq_display.display(freq)

            self.duty_display.display(duty)

            self.amp_display.display(amplitude)

            if pin == "SQ1":

                device.set_sqr1(
                    freq,
                    duty
                )

            elif pin == "SQ2":

                device.set_sqr2(
                    freq,
                    duty
                )

            elif pin == "WG":

                device.set_wave(freq)

            self.warning_label.setText(
                f"{pin} ACTIVE"
            )

            self.warning_label.setStyleSheet(
                "color:lime;"
            )

        except Exception as e:

            print(e)

            self.warning_label.setText(
                "Generator Error"
            )

            self.warning_label.setStyleSheet(
                "color:red;"
            )

    # ======================================================
    # PV OUTPUT UPDATE
    # ======================================================

    def update_pv_outputs(self):

        try:

            pv1_voltage = (
                self.pv1_slider.value() / 1000
            )

            if pv1_voltage > 5:
                pv1_voltage = 5

            device.set_pv1(
                pv1_voltage
            )

            self.pv1_display.display(
                pv1_voltage
            )

            pv2_voltage = (
                self.pv2_slider.value() / 1000
            )

            if pv2_voltage > 3.3:
                pv2_voltage = 3.3

            if pv2_voltage < -3.3:
                pv2_voltage = -3.3

            device.set_pv2(
                pv2_voltage
            )

            self.pv2_display.display(
                pv2_voltage
            )

        except Exception as e:

            print(e)

    # ======================================================
    # UPDATE SCOPE
    # ======================================================

    def update_scope(self):

        if self.freeze_display:
            return

        try:

            # ==========================================
            # SAFE CAPTURE
            # ==========================================

            result = device.capture1(
                'A1',
                self.SAMPLES,
                self.TIME_GAP
            )

            # ==========================================
            # INVALID CAPTURE CHECK
            # ==========================================

            if result is None:

                self.warning_label.setText(
                    "Capture Failed"
                )

                self.warning_label.setStyleSheet(
                    "color:red;"
                )

                return

            if len(result) != 2:

                self.warning_label.setText(
                    "Invalid Capture"
                )

                self.warning_label.setStyleSheet(
                    "color:red;"
                )

                return

            x, y = result

            if len(x) == 0 or len(y) == 0:
                return

            # ==========================================
            # CRO DISPLAY
            # ==========================================

            self.cro_curve.setData(
                x,
                y
            )

            self.cro_plot.setYRange(
                -6,
                6
            )

            # ==========================================
            # FFT
            # ==========================================

            N = len(y)

            yf = fft(y)

            xf = fftfreq(
                N,
                self.TIME_GAP * 1e-6
            )

            positive = xf >= 0

            xf = xf[positive]

            yf = np.abs(
                yf[positive]
            )

            self.fft_curve.setData(
                xf,
                yf
            )

            # ==========================================
            # MEASUREMENTS
            # ==========================================

            vpp = np.max(y) - np.min(y)

            rms = np.sqrt(
                np.mean(y ** 2)
            )

            peak = np.max(y)

            current_ma = peak

            peak_freq = 0

            if len(yf) > 1:

                peak_index = np.argmax(
                    yf[1:]
                ) + 1

                peak_freq = xf[
                    peak_index
                ]

            # ==========================================
            # UPDATE LABELS
            # ==========================================

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

            self.warning_label.setText(
                "Scope Running"
            )

            self.warning_label.setStyleSheet(
                "color:lime;"
            )

        except Exception as e:

            print("Scope Error")
            print(e)

            self.warning_label.setText(
                "SEELab Communication Error"
            )

            self.warning_label.setStyleSheet(
                "color:red;"
            )

    # ======================================================
    # CLOSE EVENT
    # ======================================================

    def closeEvent(self, event):

        try:

            self.timer.stop()

        except:
            pass

        event.accept()

# ==========================================================
# RUN
# ==========================================================

try:

    window = UltraScope()

    window.show()

    sys.exit(app.exec_())

except Exception as e:

    print("Application Error")
    print(e)