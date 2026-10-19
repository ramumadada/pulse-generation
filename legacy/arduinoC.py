import sys
import serial
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QGridLayout,
    QLCDNumber,
    QMessageBox,
    QComboBox
)
from PyQt5.QtCore import Qt

# ==========================================================
# SERIAL SETTINGS
# ==========================================================

BAUD_RATE = 115200

# ==========================================================
# MAIN WINDOW
# ==========================================================

class PulseControlPanel(QWidget):

    def __init__(self):

        super().__init__()

        self.serial_port = None

        self.init_ui()

    # ======================================================
    # UI
    # ======================================================

    def init_ui(self):

        self.setWindowTitle(
            "Arduino Pulse Control Panel"
        )

        self.resize(700, 500)

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
            }

            QPushButton:hover{
                background:#404040;
            }

        """)

        main_layout = QVBoxLayout()

        grid = QGridLayout()

        # ==================================================
        # COM PORT
        # ==================================================

        self.port_box = QComboBox()

        self.port_box.addItems([
            "COM3",
            "COM4",
            "COM5",
            "COM6"
        ])

        self.connect_btn = QPushButton(
            "CONNECT"
        )

        self.connect_btn.clicked.connect(
            self.connect_arduino
        )

        # ==================================================
        # FREQUENCY
        # ==================================================

        self.freq_slider = QSlider(Qt.Horizontal)

        self.freq_slider.setMinimum(100)

        self.freq_slider.setMaximum(2000000)

        self.freq_slider.setValue(50000)

        self.freq_display = QLCDNumber()

        self.freq_display.display(50000)

        self.freq_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # START DUTY
        # ==================================================

        self.start_slider = QSlider(Qt.Horizontal)

        self.start_slider.setMinimum(1)

        self.start_slider.setMaximum(95)

        self.start_slider.setValue(5)

        self.start_display = QLCDNumber()

        self.start_display.display(5)

        self.start_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # STOP DUTY
        # ==================================================

        self.stop_slider = QSlider(Qt.Horizontal)

        self.stop_slider.setMinimum(1)

        self.stop_slider.setMaximum(95)

        self.stop_slider.setValue(95)

        self.stop_display = QLCDNumber()

        self.stop_display.display(95)

        self.stop_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # STEP
        # ==================================================

        self.step_slider = QSlider(Qt.Horizontal)

        self.step_slider.setMinimum(1)

        self.step_slider.setMaximum(20)

        self.step_slider.setValue(5)

        self.step_display = QLCDNumber()

        self.step_display.display(5)

        self.step_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # BURST
        # ==================================================

        self.burst_slider = QSlider(Qt.Horizontal)

        self.burst_slider.setMinimum(1)

        self.burst_slider.setMaximum(10000)

        self.burst_slider.setValue(50)

        self.burst_display = QLCDNumber()

        self.burst_display.display(50)

        self.burst_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # OFF TIME
        # ==================================================

        self.off_slider = QSlider(Qt.Horizontal)

        self.off_slider.setMinimum(1)

        self.off_slider.setMaximum(5000)

        self.off_slider.setValue(500)

        self.off_display = QLCDNumber()

        self.off_display.display(500)

        self.off_slider.valueChanged.connect(
            self.update_displays
        )

        # ==================================================
        # SEND BUTTON
        # ==================================================

        self.send_btn = QPushButton(
            "SEND TO ARDUINO"
        )

        self.send_btn.clicked.connect(
            self.send_command
        )

        # ==================================================
        # STATUS
        # ==================================================

        self.status_label = QLabel(
            "DISCONNECTED"
        )

        self.status_label.setStyleSheet(
            "color:red;"
        )

        # ==================================================
        # ADD GRID
        # ==================================================

        grid.addWidget(
            QLabel("COM PORT"),0,0
        )

        grid.addWidget(
            self.port_box,0,1
        )

        grid.addWidget(
            self.connect_btn,0,2
        )

        grid.addWidget(
            QLabel("Frequency"),1,0
        )

        grid.addWidget(
            self.freq_slider,1,1
        )

        grid.addWidget(
            self.freq_display,1,2
        )

        grid.addWidget(
            QLabel("Start Duty"),2,0
        )

        grid.addWidget(
            self.start_slider,2,1
        )

        grid.addWidget(
            self.start_display,2,2
        )

        grid.addWidget(
            QLabel("Stop Duty"),3,0
        )

        grid.addWidget(
            self.stop_slider,3,1
        )

        grid.addWidget(
            self.stop_display,3,2
        )

        grid.addWidget(
            QLabel("Duty Step"),4,0
        )

        grid.addWidget(
            self.step_slider,4,1
        )

        grid.addWidget(
            self.step_display,4,2
        )

        grid.addWidget(
            QLabel("Burst Cycles"),5,0
        )

        grid.addWidget(
            self.burst_slider,5,1
        )

        grid.addWidget(
            self.burst_display,5,2
        )

        grid.addWidget(
            QLabel("OFF Time ms"),6,0
        )

        grid.addWidget(
            self.off_slider,6,1
        )

        grid.addWidget(
            self.off_display,6,2
        )

        grid.addWidget(
            self.send_btn,7,1
        )

        grid.addWidget(
            self.status_label,8,1
        )

        main_layout.addLayout(grid)

        self.setLayout(main_layout)

    # ======================================================
    # UPDATE LCD
    # ======================================================

    def update_displays(self):

        self.freq_display.display(
            self.freq_slider.value()
        )

        self.start_display.display(
            self.start_slider.value()
        )

        self.stop_display.display(
            self.stop_slider.value()
        )

        self.step_display.display(
            self.step_slider.value()
        )

        self.burst_display.display(
            self.burst_slider.value()
        )

        self.off_display.display(
            self.off_slider.value()
        )

    # ======================================================
    # CONNECT
    # ======================================================

    def connect_arduino(self):

        try:

            port = self.port_box.currentText()

            self.serial_port = serial.Serial(
                port,
                BAUD_RATE,
                timeout=1
            )

            self.status_label.setText(
                f"CONNECTED : {port}"
            )

            self.status_label.setStyleSheet(
                "color:lime;"
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Connection Error",
                str(e)
            )

    # ======================================================
    # SEND COMMAND
    # ======================================================

    def send_command(self):

        if self.serial_port is None:

            QMessageBox.warning(
                self,
                "Error",
                "Arduino Not Connected"
            )

            return

        try:

            command = (
                f"FREQ={self.freq_slider.value()},"
                f"START={self.start_slider.value()},"
                f"STOP={self.stop_slider.value()},"
                f"STEP={self.step_slider.value()},"
                f"BURST={self.burst_slider.value()},"
                f"OFF={self.off_slider.value()}\n"
            )

            self.serial_port.write(
                command.encode()
            )

            print("Sent:", command)

            self.status_label.setText(
                "COMMAND SENT"
            )

            self.status_label.setStyleSheet(
                "color:yellow;"
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Serial Error",
                str(e)
            )

# ==========================================================
# MAIN
# ==========================================================

app = QApplication(sys.argv)

window = PulseControlPanel()

window.show()

sys.exit(app.exec_())