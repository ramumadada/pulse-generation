# ==========================================================
# QApplication MUST BE FIRST
# ==========================================================

import sys

from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)

# ==========================================================
# IMPORTS
# ==========================================================

import time
import threading
import numpy as np
import pyqtgraph as pg

from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLCDNumber
)

from PyQt5.QtCore import Qt, QTimer

# ==========================================================
# EYES17
# ==========================================================

import eyes17.eyes

# ==========================================================
# CONNECT DEVICE
# ==========================================================

try:

    device = eyes17.eyes.open()

    print("SEELab Connected")

except Exception as e:

    print("Device opening Error")

    print(e)

    sys.exit()

# ==========================================================
# MAIN WINDOW
# ==========================================================

class IVPulseAnalyzer(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "MEMRISTOR IV PULSE ANALYZER"
        )

        self.resize(1600, 900)

        self.running = False

        self.SAMPLES = 1000

        self.TIME_GAP = 4

        self.iv_voltage_data = []

        self.iv_current_data = []

        # ==================================================
        # STYLE
        # ==================================================

        self.setStyleSheet("""

            QWidget{
                background:#0b0b0b;
                color:white;
                font-size:13px;
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

        """)

        # ==================================================
        # MAIN LAYOUT
        # ==================================================

        main_layout = QVBoxLayout()

        controls = QGridLayout()

        # ==================================================
        # START VOLTAGE
        # ==================================================

        self.start_slider = QSlider(Qt.Horizontal)

        self.start_slider.setMinimum(0)

        self.start_slider.setMaximum(5000)

        self.start_slider.setValue(500)

        self.start_display = QLCDNumber()

        self.start_display.display(0.5)

        self.start_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # STOP VOLTAGE
        # ==================================================

        self.stop_slider = QSlider(Qt.Horizontal)

        self.stop_slider.setMinimum(0)

        self.stop_slider.setMaximum(5000)

        self.stop_slider.setValue(3000)

        self.stop_display = QLCDNumber()

        self.stop_display.display(3.0)

        self.stop_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # STEP VOLTAGE
        # ==================================================

        self.step_slider = QSlider(Qt.Horizontal)

        self.step_slider.setMinimum(10)

        self.step_slider.setMaximum(1000)

        self.step_slider.setValue(100)

        self.step_display = QLCDNumber()

        self.step_display.display(0.1)

        self.step_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # PULSE WIDTH
        # ==================================================

        self.width_slider = QSlider(Qt.Horizontal)

        self.width_slider.setMinimum(1)

        self.width_slider.setMaximum(1000)

        self.width_slider.setValue(50)

        self.width_display = QLCDNumber()

        self.width_display.display(50)

        self.width_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # START BUTTON
        # ==================================================

        self.start_btn = QPushButton(
            "START IV SWEEP"
        )

        self.start_btn.clicked.connect(
            self.start_iv
        )

        # ==================================================
        # STOP BUTTON
        # ==================================================

        self.stop_btn = QPushButton(
            "STOP"
        )

        self.stop_btn.clicked.connect(
            self.stop_iv
        )

        # ==================================================
        # STATUS
        # ==================================================

        self.status_label = QLabel(
            "READY"
        )

        self.status_label.setStyleSheet(
            "color:lime;"
        )

        # ==================================================
        # ADD CONTROLS
        # ==================================================

        controls.addWidget(
            QLabel("Start Voltage"),0,0
        )

        controls.addWidget(
            self.start_slider,0,1
        )

        controls.addWidget(
            self.start_display,0,2
        )

        controls.addWidget(
            QLabel("Stop Voltage"),1,0
        )

        controls.addWidget(
            self.stop_slider,1,1
        )

        controls.addWidget(
            self.stop_display,1,2
        )

        controls.addWidget(
            QLabel("Voltage Step"),2,0
        )

        controls.addWidget(
            self.step_slider,2,1
        )

        controls.addWidget(
            self.step_display,2,2
        )

        controls.addWidget(
            QLabel("Pulse Width ms"),3,0
        )

        controls.addWidget(
            self.width_slider,3,1
        )

        controls.addWidget(
            self.width_display,3,2
        )

        controls.addWidget(
            self.start_btn,4,0
        )

        controls.addWidget(
            self.stop_btn,4,1
        )

        controls.addWidget(
            self.status_label,4,2
        )

        # ==================================================
        # SCOPE PLOT
        # ==================================================

        self.scope_plot = pg.PlotWidget()

        self.scope_plot.setBackground('k')

        self.scope_plot.showGrid(
            x=True,
            y=True
        )

        self.scope_curve = self.scope_plot.plot(
            pen=pg.mkPen('y', width=2)
        )

        # ==================================================
        # IV GRAPH
        # ==================================================

        self.iv_plot = pg.PlotWidget()

        self.iv_plot.setBackground('k')

        self.iv_plot.showGrid(
            x=True,
            y=True
        )

        self.iv_curve = self.iv_plot.plot(
            pen=pg.mkPen('c', width=2),
            symbol='o'
        )

        # ==================================================
        # ADD LAYOUT
        # ==================================================

        main_layout.addLayout(
            controls
        )

        graph_layout = QHBoxLayout()

        graph_layout.addWidget(
            self.scope_plot
        )

        graph_layout.addWidget(
            self.iv_plot
        )

        main_layout.addLayout(
            graph_layout
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

        self.timer.start(50)

    # ======================================================
    # UPDATE LCDS
    # ======================================================

    def update_displays(self):

        self.start_display.display(
            self.start_slider.value() / 1000
        )

        self.stop_display.display(
            self.stop_slider.value() / 1000
        )

        self.step_display.display(
            self.step_slider.value() / 1000
        )

        self.width_display.display(
            self.width_slider.value()
        )

    # ======================================================
    # IV WORKER
    # ======================================================

    def iv_worker(self):

        try:

            self.iv_voltage_data.clear()

            self.iv_current_data.clear()

            start_v = self.start_slider.value() / 1000

            stop_v = self.stop_slider.value() / 1000

            step_v = self.step_slider.value() / 1000

            pulse_width = self.width_slider.value() / 1000

            voltage = start_v

            while voltage <= stop_v and self.running:

                # ==========================================
                # APPLY VOLTAGE
                # ==========================================

                device.set_pv1(
                    voltage
                )

                # ==========================================
                # ENABLE PULSE
                # ==========================================

                device.set_sqr1(
                    1000,
                    50
                )

                time.sleep(
                    pulse_width
                )

                # ==========================================
                # MEASURE
                # ==========================================

                mem_voltage = device.get_voltage(
                    'A1'
                )

                sense_voltage = device.get_voltage(
                    'A2'
                )

                # ==========================================
                # CURRENT
                # ==========================================

                current = sense_voltage / 100

                self.iv_voltage_data.append(
                    mem_voltage
                )

                self.iv_current_data.append(
                    current
                )

                # ==========================================
                # UPDATE GRAPH
                # ==========================================

                self.iv_curve.setData(
                    self.iv_voltage_data,
                    self.iv_current_data
                )

                # ==========================================
                # DISABLE PULSE
                # ==========================================

                device.set_state(
                    SQR1=0
                )

                time.sleep(
                    0.05
                )

                voltage += step_v

            self.status_label.setText(
                "IV SWEEP COMPLETE"
            )

            self.status_label.setStyleSheet(
                "color:lime;"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # START IV
    # ======================================================

    def start_iv(self):

        if self.running:

            return

        self.running = True

        self.status_label.setText(
            "IV SWEEP RUNNING"
        )

        self.status_label.setStyleSheet(
            "color:yellow;"
        )

        threading.Thread(

            target=self.iv_worker,

            daemon=True

        ).start()

    # ======================================================
    # STOP IV
    # ======================================================

    def stop_iv(self):

        self.running = False

        try:

            device.set_state(
                SQR1=0
            )

        except:
            pass

        self.status_label.setText(
            "STOPPED"
        )

        self.status_label.setStyleSheet(
            "color:red;"
        )

    # ======================================================
    # UPDATE SCOPE
    # ======================================================

    def update_scope(self):

        try:

            x, y = device.capture1(

                'A1',

                self.SAMPLES,

                self.TIME_GAP

            )

            if x is None or y is None:

                return

            self.scope_curve.setData(
                x,
                y
            )

            self.scope_plot.enableAutoRange(
                axis='y'
            )

        except Exception as e:

            print(e)

# ==========================================================
# RUN
# ==========================================================

window = IVPulseAnalyzer()

window.show()

sys.exit(app.exec_())