import sys

# ==========================================================
# QApplication MUST BE FIRST
# ==========================================================

from PyQt5.QtWidgets import QApplication

# ==========================================================
# IMPORTS
# ==========================================================

import pyqtgraph as pg

import arduino_serial_module
import memristor_module
import pulse_train_module
import save_module
import trigger_module

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
    QFrame,
    QTabWidget,
    QGroupBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QPlainTextEdit,
    QScrollArea,
)

from PyQt5.QtCore import Qt, QTimer

# ==========================================================
# SEELAB OUTPUT LIMITS
# ==========================================================

PIN_LIMITS = {

    "SQ1": {
        "freq_min": 1,
        "freq_max": 100000,
        "amp_min": 0,
        "amp_max": 5000,
        "duty_min": 1,
        "duty_max": 99,
    },

    "SQ2": {
        "freq_min": 1,
        "freq_max": 100000,
        "amp_min": 0,
        "amp_max": 5000,
        "duty_min": 1,
        "duty_max": 99,
    },

    "WG": {
        "freq_min": 1,
        "freq_max": 5000,
        "amp_min": 0,
        "amp_max": 3000,
        "duty_min": 50,
        "duty_max": 50,
    },
}


# ==========================================================
# MAIN WINDOW
# ==========================================================

class UltraScope(QWidget):

    def __init__(self, device):
        """
        WHY CHANGED: device (the eyes17 SEELab object) was a module-level
        global, which meant importing this file triggered hardware connection
        and sys.exit() on failure. Passing device as a parameter keeps
        hardware setup in __main__ where it belongs and allows the class to
        be instantiated in tests without real hardware.
        """
        super().__init__()
        self.device = device

        self.setWindowTitle(
            "PROFESSIONAL HYBRID ELECTRONIC INSTRUMENTATION PLATFORM"
        )

        self.resize(1900, 1000)

        self.freeze_display = False
        self.SAMPLES = 1200
        self.TIME_GAP = 4
        self.scope_speed = 50
        self.sense_resistor_ohm = 100.0

        self.trigger_enabled = False
        self.trigger_source = "A1"
        self.trigger_edge = "Rising"
        self.trigger_level_volts = 0.0

        self.arduino = arduino_serial_module.ArduinoSerialController()
        self.incremental_running = False
        self.incremental_sequence = []
        self.incremental_index = 0

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

            QComboBox, QSpinBox, QDoubleSpinBox{
                background:#202020;
                color:white;
                border:1px solid #404040;
                padding:5px;
            }

            QGroupBox{
                border:1px solid #303030;
                border-radius:6px;
                margin-top:10px;
                padding-top:10px;
            }

            QGroupBox::title{
                color:cyan;
                subcontrol-origin:margin;
                left:10px;
                padding:0 5px;
            }

            QTabWidget::pane{
                border:1px solid #303030;
            }

            QTabBar::tab{
                background:#151515;
                border:1px solid #303030;
                padding:9px 16px;
            }

            QTabBar::tab:selected{
                background:#303030;
                color:cyan;
            }

            QPlainTextEdit{
                background:#050505;
                color:#a8ffb0;
                border:1px solid #303030;
            }
        """)

        self.build_ui()
        self.start_timers()
        self.refresh_arduino_ports()
        self.update_pin_constraints()
        self.update_trigger_settings()
        self.update_arduino_timing_from_freq()

    # ======================================================
    # UI BUILD
    # ======================================================

    def build_ui(self):

        main_layout = QVBoxLayout()

        self.warning_label = QLabel(
            "SAFE OPERATION | Arduino generates pulses | SEELab measures A1/A2"
        )

        self.warning_label.setStyleSheet(
            "color:lime; padding:6px;"
        )

        self.tabs = QTabWidget()

        self.tabs.addTab(
            self.build_scope_page(),
            "Oscilloscope"
        )

        self.tabs.addTab(
            self.build_seelab_page(),
            "SEELab Outputs"
        )

        self.tabs.addTab(
            self.build_trigger_page(),
            "Trigger / Display"
        )

        self.tabs.addTab(
            self.build_arduino_page(),
            "Arduino Pulse Engine"
        )

        content_layout = QHBoxLayout()
        content_layout.addWidget(self.tabs, 4)
        content_layout.addWidget(self.build_pip_scope(), 1)

        main_layout.addWidget(self.warning_label)
        main_layout.addLayout(content_layout, 1)

        self.setLayout(main_layout)

    # ======================================================
    # OSCILLOSCOPE PAGE
    # ======================================================

    def build_scope_page(self):

        page = QWidget()
        layout = QVBoxLayout()

        top_bar = QHBoxLayout()

        self.freeze_btn = QPushButton(
            "Freeze"
        )

        self.freeze_btn.clicked.connect(
            self.freeze_scope
        )

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(10)
        self.speed_slider.setMaximum(200)
        self.speed_slider.setValue(50)
        self.speed_slider.valueChanged.connect(
            self.update_speed
        )

        self.speed_display = QLCDNumber()
        self.speed_display.display(50)

        self.save_trace_btn = QPushButton(
            "Save Trace"
        )

        self.save_trace_btn.clicked.connect(
            self.save_trace
        )

        self.save_waveform_btn = QPushButton(
            "Save Waveform CSV"
        )

        self.save_waveform_btn.clicked.connect(
            self.save_waveform
        )

        self.save_fft_btn = QPushButton(
            "Save FFT CSV"
        )

        self.save_fft_btn.clicked.connect(
            self.save_fft
        )

        self.save_log_btn = QPushButton(
            "Save Experiment"
        )

        self.save_log_btn.clicked.connect(
            self.save_experiment
        )

        top_bar.addWidget(QLabel("Scope Speed"))
        top_bar.addWidget(self.speed_slider, 3)
        top_bar.addWidget(self.speed_display)
        top_bar.addWidget(self.freeze_btn)
        top_bar.addStretch(1)
        top_bar.addWidget(self.save_trace_btn)
        top_bar.addWidget(self.save_waveform_btn)
        top_bar.addWidget(self.save_fft_btn)
        top_bar.addWidget(self.save_log_btn)

        center_layout = QHBoxLayout()

        left_panel = QFrame()
        left_panel.setStyleSheet(
            "background:#111111;"
        )

        left_layout = QVBoxLayout()

        self.vpp_label = QLabel("Vpp : 0 V")
        self.rms_label = QLabel("RMS : 0 V")
        self.peak_label = QLabel("Peak : 0 V")
        self.current_label = QLabel("Current : 0 mA")
        self.freq_label = QLabel("Freq : 0 Hz")

        left_layout.addWidget(QLabel("Measurements"))
        left_layout.addWidget(self.vpp_label)
        left_layout.addWidget(self.rms_label)
        left_layout.addWidget(self.peak_label)
        left_layout.addWidget(self.current_label)
        left_layout.addWidget(self.freq_label)
        left_layout.addStretch(1)

        left_panel.setLayout(left_layout)

        self.cro_plot = pg.PlotWidget()
        self.cro_plot.setBackground('k')
        self.cro_plot.showGrid(
            x=True,
            y=True
        )
        self.cro_plot.addLegend()

        self.cro_curve = self.cro_plot.plot(
            pen=pg.mkPen('y', width=2),
            name="A1"
        )

        self.cro_curve_a2 = self.cro_plot.plot(
            pen=pg.mkPen('c', width=2),
            name="A2"
        )

        self.cro_curve_diff = self.cro_plot.plot(
            pen=pg.mkPen('g', width=2),
            name="A1-A2"
        )

        self.fft_plot = pg.PlotWidget()
        self.fft_plot.setBackground('k')
        self.fft_plot.showGrid(
            x=True,
            y=True
        )

        self.fft_curve = self.fft_plot.plot(
            pen=pg.mkPen('c', width=2)
        )

        self.fft_peak_marker = pg.ScatterPlotItem(
            size=12,
            brush='r'
        )

        self.fft_plot.addItem(
            self.fft_peak_marker
        )

        center_layout.addWidget(left_panel, 1)
        center_layout.addWidget(self.cro_plot, 4)
        center_layout.addWidget(self.fft_plot, 4)

        layout.addLayout(top_bar)
        layout.addLayout(center_layout)

        page.setLayout(layout)
        return page

    # ======================================================
    # PERSISTENT MINI SCOPE
    # ======================================================

    def build_pip_scope(self):

        group = QGroupBox("Live Oscilloscope PiP")
        group.setMinimumWidth(360)
        group.setMaximumWidth(460)
        layout = QVBoxLayout()

        self.pip_scope_plot = pg.PlotWidget()
        self.pip_scope_plot.setBackground('k')
        self.pip_scope_plot.setMinimumHeight(220)
        self.pip_scope_plot.showGrid(
            x=True,
            y=True
        )

        self.pip_curve_a1 = self.pip_scope_plot.plot(
            pen=pg.mkPen('y', width=1),
            name="A1"
        )

        self.pip_curve_a2 = self.pip_scope_plot.plot(
            pen=pg.mkPen('c', width=1),
            name="A2"
        )

        self.pip_curve_diff = self.pip_scope_plot.plot(
            pen=pg.mkPen('g', width=1),
            name="A1-A2"
        )

        self.pip_status_label = QLabel(
            "PiP follows live SEELab A1/A2 acquisition"
        )
        self.pip_status_label.setStyleSheet("color:cyan;")

        layout.addWidget(self.pip_scope_plot)
        layout.addWidget(self.pip_status_label)
        group.setLayout(layout)
        return group

    # ======================================================
    # SEELAB OUTPUT PAGE
    # ======================================================

    def build_seelab_page(self):

        page = QWidget()
        layout = QGridLayout()

        self.pin_select = QComboBox()
        self.pin_select.addItems([
            "SQ1",
            "SQ2",
            "WG"
        ])
        self.pin_select.currentIndexChanged.connect(
            self.update_pin_constraints
        )

        self.freq_slider = QSlider(Qt.Horizontal)
        self.freq_display = QLCDNumber()
        self.freq_slider.valueChanged.connect(
            self.update_generator
        )

        self.duty_slider = QSlider(Qt.Horizontal)
        self.duty_display = QLCDNumber()
        self.duty_slider.valueChanged.connect(
            self.update_generator
        )

        self.amp_slider = QSlider(Qt.Horizontal)
        self.amp_display = QLCDNumber()
        self.amp_slider.valueChanged.connect(
            self.update_generator
        )

        self.pv1_slider = QSlider(Qt.Horizontal)
        self.pv1_slider.setMinimum(0)
        self.pv1_slider.setMaximum(5000)
        self.pv1_slider.valueChanged.connect(
            self.update_pv_outputs
        )
        self.pv1_display = QLCDNumber()

        self.pv2_slider = QSlider(Qt.Horizontal)
        self.pv2_slider.setMinimum(-3300)
        self.pv2_slider.setMaximum(3300)
        self.pv2_slider.valueChanged.connect(
            self.update_pv_outputs
        )
        self.pv2_display = QLCDNumber()

        self.pin_info = QLabel(
            "SEELab outputs are for signal generation and safe PV bias only."
        )

        self.pin_info.setStyleSheet(
            "color:cyan;"
        )

        layout.addWidget(QLabel("Output"), 0, 0)
        layout.addWidget(self.pin_select, 0, 1)
        layout.addWidget(self.pin_info, 0, 2)

        layout.addWidget(QLabel("Frequency"), 1, 0)
        layout.addWidget(self.freq_slider, 1, 1)
        layout.addWidget(self.freq_display, 1, 2)

        layout.addWidget(QLabel("Duty"), 2, 0)
        layout.addWidget(self.duty_slider, 2, 1)
        layout.addWidget(self.duty_display, 2, 2)

        layout.addWidget(QLabel("Amplitude"), 3, 0)
        layout.addWidget(self.amp_slider, 3, 1)
        layout.addWidget(self.amp_display, 3, 2)

        layout.addWidget(QLabel("PV1 0 to 5 V"), 4, 0)
        layout.addWidget(self.pv1_slider, 4, 1)
        layout.addWidget(self.pv1_display, 4, 2)

        layout.addWidget(QLabel("PV2 -3.3 to 3.3 V"), 5, 0)
        layout.addWidget(self.pv2_slider, 5, 1)
        layout.addWidget(self.pv2_display, 5, 2)

        layout.setRowStretch(6, 1)

        page.setLayout(layout)
        return page

    # ======================================================
    # TRIGGER PAGE
    # ======================================================

    def build_trigger_page(self):

        page = QWidget()
        layout = QGridLayout()

        self.show_a1_checkbox = QCheckBox("Show A1")
        self.show_a1_checkbox.setChecked(True)
        self.show_a1_checkbox.stateChanged.connect(
            self.update_trigger_settings
        )

        self.show_a2_checkbox = QCheckBox("Show A2")
        self.show_a2_checkbox.setChecked(True)
        self.show_a2_checkbox.stateChanged.connect(
            self.update_trigger_settings
        )

        self.show_diff_checkbox = QCheckBox("Show A1-A2")
        self.show_diff_checkbox.setChecked(True)
        self.show_diff_checkbox.stateChanged.connect(
            self.update_trigger_settings
        )

        self.scope_display_mode = QComboBox()
        self.scope_display_mode.addItems([
            "Overlay",
            "A1 Only",
            "A2 Only",
            "Differential",
        ])
        self.scope_display_mode.currentIndexChanged.connect(
            self.update_trigger_settings
        )

        self.trigger_enable_checkbox = QCheckBox("Enable Display Trigger")
        self.trigger_enable_checkbox.stateChanged.connect(
            self.update_trigger_settings
        )

        self.trigger_source_select = QComboBox()
        self.trigger_source_select.addItems([
            "A1",
            "A2",
            "DIFF",
        ])
        self.trigger_source_select.currentIndexChanged.connect(
            self.update_trigger_settings
        )

        self.trigger_edge_select = QComboBox()
        self.trigger_edge_select.addItems([
            "Rising",
            "Falling",
        ])
        self.trigger_edge_select.currentIndexChanged.connect(
            self.update_trigger_settings
        )

        self.trigger_level_slider = QSlider(Qt.Horizontal)
        self.trigger_level_slider.setMinimum(-5000)
        self.trigger_level_slider.setMaximum(5000)
        self.trigger_level_slider.setValue(0)
        self.trigger_level_slider.valueChanged.connect(
            self.update_trigger_settings
        )

        self.trigger_level_display = QLCDNumber()
        self.trigger_level_display.display(0.0)

        layout.addWidget(QLabel("Display Mode"), 0, 0)
        layout.addWidget(self.scope_display_mode, 0, 1)

        layout.addWidget(self.show_a1_checkbox, 1, 0)
        layout.addWidget(self.show_a2_checkbox, 1, 1)
        layout.addWidget(self.show_diff_checkbox, 1, 2)

        layout.addWidget(self.trigger_enable_checkbox, 2, 0)
        layout.addWidget(QLabel("Trigger Source"), 3, 0)
        layout.addWidget(self.trigger_source_select, 3, 1)
        layout.addWidget(QLabel("Edge"), 4, 0)
        layout.addWidget(self.trigger_edge_select, 4, 1)
        layout.addWidget(QLabel("Level"), 5, 0)
        layout.addWidget(self.trigger_level_slider, 5, 1)
        layout.addWidget(self.trigger_level_display, 5, 2)

        note = QLabel(
            "Trigger alignment is display-only. Arduino still handles real pulse timing."
        )
        note.setStyleSheet("color:yellow;")
        layout.addWidget(note, 6, 0, 1, 3)
        layout.setRowStretch(7, 1)

        page.setLayout(layout)
        return page

    # ======================================================
    # ARDUINO PAGE
    # ======================================================

    def build_arduino_page(self):

        page = QWidget()
        page_layout = QVBoxLayout()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        layout = QVBoxLayout()

        connection_group = QGroupBox("Arduino Connection")
        connection_layout = QGridLayout()

        self.arduino_port_select = QComboBox()

        self.refresh_arduino_btn = QPushButton(
            "Refresh Ports"
        )
        self.refresh_arduino_btn.clicked.connect(
            self.refresh_arduino_ports
        )

        self.connect_arduino_btn = QPushButton(
            "Connect"
        )
        self.connect_arduino_btn.clicked.connect(
            self.connect_arduino
        )

        self.disconnect_arduino_btn = QPushButton(
            "Disconnect"
        )
        self.disconnect_arduino_btn.clicked.connect(
            self.disconnect_arduino
        )

        self.arduino_status_btn = QPushButton(
            "Status"
        )
        self.arduino_status_btn.clicked.connect(
            self.request_arduino_status
        )

        self.arduino_status_label = QLabel(
            "Arduino: Not Connected"
        )
        self.arduino_status_label.setStyleSheet(
            "color:orange;"
        )

        connection_layout.addWidget(QLabel("Port"), 0, 0)
        connection_layout.addWidget(self.arduino_port_select, 0, 1)
        connection_layout.addWidget(self.refresh_arduino_btn, 0, 2)
        connection_layout.addWidget(self.connect_arduino_btn, 1, 0)
        connection_layout.addWidget(self.disconnect_arduino_btn, 1, 1)
        connection_layout.addWidget(self.arduino_status_btn, 1, 2)
        connection_layout.addWidget(self.arduino_status_label, 2, 0, 1, 3)

        connection_group.setLayout(connection_layout)

        pulse_group = QGroupBox("Pulse Train")
        pulse_layout = QGridLayout()

        self.arduino_pin_spin = self.make_int_spin(2, 13, 9)
        self.pulse_frequency_spin = self.make_double_spin(0.1, 100000.0, 1000.0, " Hz")
        self.pulse_duty_spin = self.make_double_spin(0.1, 99.9, 50.0, " %")
        self.pulse_high_us_spin = self.make_int_spin(1, 10000000, 500)
        self.pulse_low_us_spin = self.make_int_spin(1, 10000000, 500)
        self.pulse_count_spin = self.make_int_spin(1, 1000000, 20)
        self.pulse_delay_ms_spin = self.make_int_spin(0, 60000, 50)

        self.pulse_frequency_spin.valueChanged.connect(
            self.update_arduino_timing_from_freq
        )
        self.pulse_duty_spin.valueChanged.connect(
            self.update_arduino_timing_from_freq
        )

        self.configure_pulse_btn = QPushButton("Load Train")
        self.configure_pulse_btn.clicked.connect(
            self.configure_arduino_pulse
        )

        self.start_pulse_btn = QPushButton("Run Pulse Train")
        self.start_pulse_btn.clicked.connect(
            self.start_arduino_pulse
        )

        self.stop_pulse_btn = QPushButton("Stop Train")
        self.stop_pulse_btn.clicked.connect(
            self.stop_arduino_pulse
        )

        pulse_layout.addWidget(QLabel("Arduino Pin"), 0, 0)
        pulse_layout.addWidget(self.arduino_pin_spin, 0, 1)
        pulse_layout.addWidget(QLabel("Frequency"), 1, 0)
        pulse_layout.addWidget(self.pulse_frequency_spin, 1, 1)
        pulse_layout.addWidget(QLabel("Duty"), 2, 0)
        pulse_layout.addWidget(self.pulse_duty_spin, 2, 1)
        pulse_layout.addWidget(QLabel("High us"), 3, 0)
        pulse_layout.addWidget(self.pulse_high_us_spin, 3, 1)
        pulse_layout.addWidget(QLabel("Low us"), 4, 0)
        pulse_layout.addWidget(self.pulse_low_us_spin, 4, 1)
        pulse_layout.addWidget(QLabel("Pulse Count"), 5, 0)
        pulse_layout.addWidget(self.pulse_count_spin, 5, 1)
        pulse_layout.addWidget(QLabel("Delay ms"), 6, 0)
        pulse_layout.addWidget(self.pulse_delay_ms_spin, 6, 1)
        pulse_layout.addWidget(self.configure_pulse_btn, 7, 0)
        pulse_layout.addWidget(self.start_pulse_btn, 7, 1)
        pulse_layout.addWidget(self.stop_pulse_btn, 7, 2)

        pulse_group.setLayout(pulse_layout)

        burst_group = QGroupBox("Burst Packets")
        burst_layout = QGridLayout()

        self.burst_count_spin = self.make_int_spin(1, 100000, 5)
        self.pulses_per_burst_spin = self.make_int_spin(1, 100000, 10)
        self.burst_delay_ms_spin = self.make_int_spin(0, 3600000, 500)

        self.configure_burst_btn = QPushButton("Load Burst")
        self.configure_burst_btn.clicked.connect(
            self.configure_arduino_burst
        )

        self.start_burst_btn = QPushButton("Run Burst")
        self.start_burst_btn.clicked.connect(
            self.start_arduino_burst
        )

        self.stop_burst_btn = QPushButton("Stop Burst")
        self.stop_burst_btn.clicked.connect(
            self.stop_arduino_burst
        )

        burst_layout.addWidget(QLabel("Burst Count"), 0, 0)
        burst_layout.addWidget(self.burst_count_spin, 0, 1)
        burst_layout.addWidget(QLabel("Pulses / Burst"), 1, 0)
        burst_layout.addWidget(self.pulses_per_burst_spin, 1, 1)
        burst_layout.addWidget(QLabel("Burst Delay ms"), 2, 0)
        burst_layout.addWidget(self.burst_delay_ms_spin, 2, 1)
        burst_layout.addWidget(self.configure_burst_btn, 3, 0)
        burst_layout.addWidget(self.start_burst_btn, 3, 1)
        burst_layout.addWidget(self.stop_burst_btn, 3, 2)

        burst_group.setLayout(burst_layout)

        pwm_group = QGroupBox("PWM")
        pwm_layout = QGridLayout()

        self.pwm_pin_spin = self.make_int_spin(2, 13, 9)
        self.pwm_frequency_spin = self.make_double_spin(0.1, 100000.0, 1000.0, " Hz")
        self.pwm_duty_spin = self.make_double_spin(0.0, 100.0, 50.0, " %")
        self.pwm_duration_ms_spin = self.make_int_spin(0, 3600000, 0)

        self.configure_pwm_btn = QPushButton("Configure PWM")
        self.configure_pwm_btn.clicked.connect(
            self.configure_arduino_pwm
        )

        self.start_pwm_btn = QPushButton("Start PWM")
        self.start_pwm_btn.clicked.connect(
            self.start_arduino_pwm
        )

        self.stop_pwm_btn = QPushButton("Stop PWM")
        self.stop_pwm_btn.clicked.connect(
            self.stop_arduino_pwm
        )

        pwm_layout.addWidget(QLabel("PWM Pin"), 0, 0)
        pwm_layout.addWidget(self.pwm_pin_spin, 0, 1)
        pwm_layout.addWidget(QLabel("Frequency"), 1, 0)
        pwm_layout.addWidget(self.pwm_frequency_spin, 1, 1)
        pwm_layout.addWidget(QLabel("Duty"), 2, 0)
        pwm_layout.addWidget(self.pwm_duty_spin, 2, 1)
        pwm_layout.addWidget(QLabel("Duration ms"), 3, 0)
        pwm_layout.addWidget(self.pwm_duration_ms_spin, 3, 1)
        pwm_layout.addWidget(self.configure_pwm_btn, 4, 0)
        pwm_layout.addWidget(self.start_pwm_btn, 4, 1)
        pwm_layout.addWidget(self.stop_pwm_btn, 4, 2)

        pwm_group.setLayout(pwm_layout)

        fast_burst_group = QGroupBox("Fast Timer1 Burst on Pin 9")
        fast_burst_layout = QGridLayout()

        self.fast_burst_frequency_spin = self.make_double_spin(
            1.0,
            2000000.0,
            2000000.0,
            " Hz"
        )
        self.fast_burst_duty_spin = self.make_double_spin(
            1.0,
            99.0,
            33.0,
            " %"
        )
        self.fast_burst_cycles_spin = self.make_int_spin(
            1,
            1000000,
            100
        )
        self.fast_burst_off_us_spin = self.make_int_spin(
            1,
            10000000,
            500
        )
        self.fast_burst_count_spin = self.make_int_spin(
            0,
            1000000,
            0
        )

        self.configure_fast_burst_btn = QPushButton("Load Fast Burst")
        self.configure_fast_burst_btn.clicked.connect(
            self.configure_fast_burst
        )

        self.start_fast_burst_btn = QPushButton("Run Fast Burst")
        self.start_fast_burst_btn.clicked.connect(
            self.start_fast_burst
        )

        self.stop_fast_burst_btn = QPushButton("Stop Fast Burst")
        self.stop_fast_burst_btn.clicked.connect(
            self.stop_fast_burst
        )

        fast_burst_layout.addWidget(QLabel("Fixed Output Pin"), 0, 0)
        fast_burst_layout.addWidget(QLabel("D9 / OC1A"), 0, 1)
        fast_burst_layout.addWidget(QLabel("Frequency"), 1, 0)
        fast_burst_layout.addWidget(self.fast_burst_frequency_spin, 1, 1)
        fast_burst_layout.addWidget(QLabel("Duty"), 2, 0)
        fast_burst_layout.addWidget(self.fast_burst_duty_spin, 2, 1)
        fast_burst_layout.addWidget(QLabel("PWM Cycles / Burst"), 3, 0)
        fast_burst_layout.addWidget(self.fast_burst_cycles_spin, 3, 1)
        fast_burst_layout.addWidget(QLabel("Off Time us"), 4, 0)
        fast_burst_layout.addWidget(self.fast_burst_off_us_spin, 4, 1)
        fast_burst_layout.addWidget(QLabel("Burst Count 0=Loop"), 5, 0)
        fast_burst_layout.addWidget(self.fast_burst_count_spin, 5, 1)
        fast_burst_layout.addWidget(self.configure_fast_burst_btn, 6, 0)
        fast_burst_layout.addWidget(self.start_fast_burst_btn, 6, 1)
        fast_burst_layout.addWidget(self.stop_fast_burst_btn, 6, 2)

        fast_burst_group.setLayout(fast_burst_layout)

        incremental_group = QGroupBox("Incremental PV1 Amplitude Pulses")
        incremental_layout = QGridLayout()

        self.increment_start_v_spin = self.make_double_spin(
            0.0,
            5.0,
            0.5,
            " V"
        )
        self.increment_stop_v_spin = self.make_double_spin(
            0.0,
            5.0,
            3.0,
            " V"
        )
        self.increment_step_v_spin = self.make_double_spin(
            0.001,
            5.0,
            0.5,
            " V"
        )
        self.increment_width_us_spin = self.make_int_spin(
            1,
            10000000,
            1000
        )
        self.increment_off_us_spin = self.make_int_spin(
            1,
            10000000,
            1000
        )

        self.start_increment_btn = QPushButton("Run Incremental PV1 Pulses")
        self.start_increment_btn.clicked.connect(
            self.start_incremental_amplitude_train
        )

        self.stop_increment_btn = QPushButton("Stop Incremental")
        self.stop_increment_btn.clicked.connect(
            self.stop_incremental_amplitude_train
        )

        incremental_layout.addWidget(QLabel("Start PV1"), 0, 0)
        incremental_layout.addWidget(self.increment_start_v_spin, 0, 1)
        incremental_layout.addWidget(QLabel("Stop PV1"), 1, 0)
        incremental_layout.addWidget(self.increment_stop_v_spin, 1, 1)
        incremental_layout.addWidget(QLabel("Step"), 2, 0)
        incremental_layout.addWidget(self.increment_step_v_spin, 2, 1)
        incremental_layout.addWidget(QLabel("Pulse Width us"), 3, 0)
        incremental_layout.addWidget(self.increment_width_us_spin, 3, 1)
        incremental_layout.addWidget(QLabel("Off Time us"), 4, 0)
        incremental_layout.addWidget(self.increment_off_us_spin, 4, 1)
        incremental_layout.addWidget(self.start_increment_btn, 5, 0)
        incremental_layout.addWidget(self.stop_increment_btn, 5, 1)

        note = QLabel(
            "PV1 sets true amplitude. Arduino D9/Timer1 controls MOSFET gate timing."
        )
        note.setStyleSheet("color:yellow;")
        incremental_layout.addWidget(note, 6, 0, 1, 2)

        incremental_group.setLayout(incremental_layout)

        self.arduino_log = QPlainTextEdit()
        self.arduino_log.setReadOnly(True)
        self.arduino_log.setMaximumBlockCount(500)

        pulse_burst_row = QHBoxLayout()
        pulse_burst_row.addWidget(pulse_group)
        pulse_burst_row.addWidget(burst_group)

        pwm_fast_row = QHBoxLayout()
        pwm_fast_row.addWidget(pwm_group)
        pwm_fast_row.addWidget(fast_burst_group)

        layout.addWidget(connection_group)
        layout.addLayout(pulse_burst_row)
        layout.addLayout(pwm_fast_row)
        layout.addWidget(incremental_group)
        layout.addWidget(QLabel("Arduino Serial Log"))
        layout.addWidget(self.arduino_log, 1)

        scroll_content.setLayout(layout)
        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area)
        page.setLayout(page_layout)
        return page

    # ======================================================
    # WIDGET HELPERS
    # ======================================================

    def make_int_spin(self, minimum, maximum, value):

        spin = QSpinBox()
        spin.setMinimum(minimum)
        spin.setMaximum(maximum)
        spin.setValue(value)
        spin.setKeyboardTracking(False)
        return spin

    def make_double_spin(self, minimum, maximum, value, suffix=""):

        spin = QDoubleSpinBox()
        spin.setMinimum(minimum)
        spin.setMaximum(maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.setDecimals(3)
        spin.setKeyboardTracking(False)
        return spin

    # ======================================================
    # TIMERS
    # ======================================================

    def start_timers(self):

        self.timer = QTimer()
        self.timer.timeout.connect(
            self.update_scope
        )
        self.timer.start(
            self.scope_speed
        )

        self.arduino_timer = QTimer()
        self.arduino_timer.timeout.connect(
            self.poll_arduino
        )
        self.arduino_timer.start(
            100
        )

    # ======================================================
    # PIN CONSTRAINTS
    # ======================================================

    def update_pin_constraints(self):

        try:

            pin = self.pin_select.currentText()
            limits = PIN_LIMITS[pin]

            self.freq_slider.blockSignals(True)
            self.duty_slider.blockSignals(True)
            self.amp_slider.blockSignals(True)

            self.freq_slider.setMinimum(
                limits["freq_min"]
            )
            self.freq_slider.setMaximum(
                limits["freq_max"]
            )
            self.freq_slider.setValue(
                limits["freq_min"]
            )

            self.duty_slider.setMinimum(
                limits["duty_min"]
            )
            self.duty_slider.setMaximum(
                limits["duty_max"]
            )
            self.duty_slider.setValue(
                min(max(50, limits["duty_min"]), limits["duty_max"])
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

            self.freq_slider.blockSignals(False)
            self.duty_slider.blockSignals(False)
            self.amp_slider.blockSignals(False)

            self.update_generator()

            self.pin_info.setText(
                "Arduino handles pulse timing | SEELab measures A1/A2"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # TRIGGER SETTINGS
    # ======================================================

    def update_trigger_settings(self):

        try:

            self.trigger_enabled = self.trigger_enable_checkbox.isChecked()
            self.trigger_source = self.trigger_source_select.currentText()
            self.trigger_edge = self.trigger_edge_select.currentText()
            self.trigger_level_volts = self.trigger_level_slider.value() / 1000

            self.trigger_level_display.display(
                self.trigger_level_volts
            )

        except Exception as e:

            print(e)

    # ======================================================
    # ARDUINO PORTS
    # ======================================================

    def refresh_arduino_ports(self):

        try:

            self.arduino_port_select.clear()

            ports = arduino_serial_module.list_serial_ports()

            if not ports:

                self.arduino_port_select.addItem(
                    "No Arduino Port",
                    ""
                )

                return

            for port, description in ports.items():

                self.arduino_port_select.addItem(
                    f"{port} - {description}",
                    port
                )

        except Exception as e:

            print(e)

    # ======================================================
    # CONNECT / DISCONNECT ARDUINO
    # ======================================================

    def connect_arduino(self):

        try:

            port = self.arduino_port_select.currentData()

            if not port:

                self.set_arduino_status(
                    "Arduino: No Port Selected",
                    "red"
                )
                return

            connected = self.arduino.connect(
                port
            )

            if connected:

                self.set_arduino_status(
                    f"Arduino: Connected {port}, booting...",
                    "yellow"
                )

                self.log_arduino(
                    f"CONNECTED {port}"
                )

                QTimer.singleShot(
                    1900,
                    self.sync_arduino
                )

            else:

                self.set_arduino_status(
                    "Arduino: Connection Failed",
                    "red"
                )

        except Exception as e:

            print(e)

    def disconnect_arduino(self):

        try:

            self.arduino.disconnect()

            self.set_arduino_status(
                "Arduino: Disconnected",
                "orange"
            )

            self.log_arduino(
                "DISCONNECTED"
            )

        except Exception as e:

            print(e)

    def sync_arduino(self):

        try:

            if not self.arduino.is_connected():
                return

            if not self.arduino.is_ready():

                wait_time = self.arduino.seconds_until_ready()

                self.set_arduino_status(
                    f"Arduino: Booting {wait_time:.1f}s",
                    "yellow"
                )

                QTimer.singleShot(
                    300,
                    self.sync_arduino
                )

                return

            success = self.arduino.ping(
                "PGEE"
            )

            self.log_arduino(
                "TX  PING TOKEN=PGEE"
            )

            self.set_arduino_status(
                "Arduino: Ready" if success else "Arduino: Ready, ping not sent",
                "lime" if success else "orange"
            )

        except Exception as e:

            print(e)

    def request_arduino_status(self):

        try:

            if not self.ensure_arduino_ready():
                return

            success = self.arduino.send_command(
                "STATUS"
            )

            self.log_arduino(
                "TX  STATUS"
            )

            self.set_arduino_status(
                "Arduino: Status Requested" if success else "Arduino: Status Failed",
                "lime" if success else "red"
            )

        except Exception as e:

            print(e)

    def set_arduino_status(self, text, color):

        self.arduino_status_label.setText(
            text
        )

        self.arduino_status_label.setStyleSheet(
            f"color:{color};"
        )

    def log_arduino(self, text):

        try:

            self.arduino_log.appendPlainText(
                text
            )

        except Exception:

            pass

    def ensure_arduino_ready(self):

        try:

            if not self.arduino.is_connected():

                self.set_arduino_status(
                    "Arduino: Not Connected",
                    "red"
                )

                self.log_arduino(
                    "ERROR Arduino is not connected"
                )

                return False

            if not self.arduino.is_ready():

                wait_time = self.arduino.seconds_until_ready()

                self.set_arduino_status(
                    f"Arduino: Wait {wait_time:.1f}s",
                    "yellow"
                )

                self.log_arduino(
                    f"WAIT Arduino booting {wait_time:.1f}s"
                )

                return False

            return True

        except Exception as e:

            print(e)
            return False

    # ======================================================
    # POLL ARDUINO
    # ======================================================

    def poll_arduino(self):

        try:

            lines = self.arduino.read_available_lines()

            for line in lines:

                self.log_arduino(
                    f"RX  {line}"
                )

                self.set_arduino_status(
                    f"Arduino: {line}",
                    "lime"
                )

        except Exception as e:

            print(e)

    # ======================================================
    # ARDUINO TIMING
    # ======================================================

    def update_arduino_timing_from_freq(self, *args):

        try:

            high_us, low_us = pulse_train_module.frequency_duty_to_timing_us(
                self.pulse_frequency_spin.value(),
                self.pulse_duty_spin.value()
            )

            self.pulse_high_us_spin.blockSignals(True)
            self.pulse_low_us_spin.blockSignals(True)

            self.pulse_high_us_spin.setValue(
                high_us
            )
            self.pulse_low_us_spin.setValue(
                low_us
            )

            self.pulse_high_us_spin.blockSignals(False)
            self.pulse_low_us_spin.blockSignals(False)

        except Exception as e:

            print(e)

    def current_pulse_packet(self):

        return arduino_serial_module.ArduinoPulsePacket(
            pin=self.arduino_pin_spin.value(),
            high_time_us=self.pulse_high_us_spin.value(),
            low_time_us=self.pulse_low_us_spin.value(),
            pulse_count=self.pulse_count_spin.value(),
            packet_count=self.burst_count_spin.value(),
            packet_delay_ms=self.burst_delay_ms_spin.value(),
        )

    def current_timer1_config(self, cycles_per_burst, burst_count, off_time_us):

        high_us = max(
            1,
            self.pulse_high_us_spin.value()
        )

        low_us = max(
            1,
            self.pulse_low_us_spin.value()
        )

        period_us = high_us + low_us
        frequency_hz = 1000000.0 / period_us
        duty_percent = (high_us / period_us) * 100.0

        return arduino_serial_module.ArduinoFastBurstConfig(
            frequency_hz=frequency_hz,
            duty_percent=duty_percent,
            cycles_per_burst=cycles_per_burst,
            off_time_us=max(1, int(off_time_us)),
            burst_count=burst_count,
        )

    # ======================================================
    # ARDUINO PULSE CONTROLS
    # ======================================================

    def configure_arduino_pulse(self):

        try:

            if not self.ensure_arduino_ready():
                return False

            if self.arduino_pin_spin.value() == 9:

                config = self.current_timer1_config(
                    cycles_per_burst=self.pulse_count_spin.value(),
                    burst_count=1,
                    off_time_us=max(1, self.pulse_delay_ms_spin.value() * 1000)
                )

                success = self.arduino.configure_fast_burst(config)

                self.log_arduino(
                    f"TX  CONFIG_FAST_BURST FREQ_HZ={config.frequency_hz} DUTY={config.duty_percent} CYCLES={config.cycles_per_burst} BURSTS=1"
                )

                self.set_arduino_status(
                    "Arduino: Timer1 Train Loaded" if success else "Arduino: Timer1 Train Load Failed",
                    "lime" if success else "red"
                )

                return success

            packet = self.current_pulse_packet()
            success = self.arduino.configure_pulse(packet)

            self.log_arduino(
                f"TX  CONFIG_PULSE PIN={packet.pin} HIGH_US={packet.high_time_us} LOW_US={packet.low_time_us} COUNT={packet.pulse_count}"
            )

            self.set_arduino_status(
                "Arduino: Pulse Configured" if success else "Arduino: Pulse Configure Failed",
                "lime" if success else "red"
            )

            return success

        except Exception as e:

            print(e)
            return False

    def start_arduino_pulse(self):

        try:

            if not self.configure_arduino_pulse():
                return

            if self.arduino_pin_spin.value() == 9:

                success = self.arduino.start_fast_burst()

                self.log_arduino(
                    "TX  START_FAST_BURST"
                )

            else:

                success = self.arduino.start_pulse()

                self.log_arduino(
                    "TX  START_PULSE"
                )


            self.set_arduino_status(
                "Arduino: Pulse Train Started" if success else "Arduino: Pulse Train Start Failed",
                "lime" if success else "red"
            )

        except Exception as e:

            print(e)

    def stop_arduino_pulse(self):

        try:

            if not self.ensure_arduino_ready():
                return

            if self.arduino_pin_spin.value() == 9:

                success = self.arduino.stop_fast_burst()

                self.log_arduino(
                    "TX  STOP_FAST_BURST"
                )

            else:

                success = self.arduino.stop_pulse()

                self.log_arduino(
                    "TX  STOP_PULSE"
                )


            self.set_arduino_status(
                "Arduino: Pulse Train Stopped" if success else "Arduino: Pulse Train Stop Failed",
                "yellow" if success else "red"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # ARDUINO BURST CONTROLS
    # ======================================================

    def configure_arduino_burst(self):

        try:

            if not self.ensure_arduino_ready():
                return False

            if self.arduino_pin_spin.value() == 9:

                config = self.current_timer1_config(
                    cycles_per_burst=self.pulses_per_burst_spin.value(),
                    burst_count=self.burst_count_spin.value(),
                    off_time_us=max(1, self.burst_delay_ms_spin.value() * 1000)
                )

                success = self.arduino.configure_fast_burst(config)

                self.log_arduino(
                    f"TX  CONFIG_FAST_BURST FREQ_HZ={config.frequency_hz} DUTY={config.duty_percent} CYCLES={config.cycles_per_burst} OFF_US={config.off_time_us} BURSTS={config.burst_count}"
                )

                self.set_arduino_status(
                    "Arduino: Timer1 Burst Loaded" if success else "Arduino: Timer1 Burst Load Failed",
                    "lime" if success else "red"
                )

                return success

            packet = arduino_serial_module.ArduinoPulsePacket(
                pin=self.arduino_pin_spin.value(),
                high_time_us=self.pulse_high_us_spin.value(),
                low_time_us=self.pulse_low_us_spin.value(),
                pulse_count=self.pulses_per_burst_spin.value(),
                packet_count=self.burst_count_spin.value(),
                packet_delay_ms=self.burst_delay_ms_spin.value(),
            )

            success = self.arduino.configure_burst(packet)

            self.log_arduino(
                f"TX  CONFIG_BURST PIN={packet.pin} PULSES={packet.pulse_count} PACKETS={packet.packet_count}"
            )

            self.set_arduino_status(
                "Arduino: Burst Configured" if success else "Arduino: Burst Configure Failed",
                "lime" if success else "red"
            )

            return success

        except Exception as e:

            print(e)
            return False

    def start_arduino_burst(self):

        try:

            if not self.configure_arduino_burst():
                return

            if self.arduino_pin_spin.value() == 9:

                success = self.arduino.start_fast_burst()

                self.log_arduino(
                    "TX  START_FAST_BURST"
                )

            else:

                success = self.arduino.start_burst()

                self.log_arduino(
                    "TX  START_BURST"
                )


            self.set_arduino_status(
                "Arduino: Burst Started" if success else "Arduino: Burst Start Failed",
                "lime" if success else "red"
            )

        except Exception as e:

            print(e)

    def stop_arduino_burst(self):

        try:

            if not self.ensure_arduino_ready():
                return

            if self.arduino_pin_spin.value() == 9:

                success = self.arduino.stop_fast_burst()

                self.log_arduino(
                    "TX  STOP_FAST_BURST"
                )

            else:

                success = self.arduino.stop_burst()

                self.log_arduino(
                    "TX  STOP_BURST"
                )


            self.set_arduino_status(
                "Arduino: Burst Stopped" if success else "Arduino: Burst Stop Failed",
                "yellow" if success else "red"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # ARDUINO PWM CONTROLS
    # ======================================================

    def configure_arduino_pwm(self):

        try:

            if not self.ensure_arduino_ready():
                return False

            config = arduino_serial_module.ArduinoPWMConfig(
                pin=self.pwm_pin_spin.value(),
                frequency_hz=self.pwm_frequency_spin.value(),
                duty_percent=self.pwm_duty_spin.value(),
                duration_ms=self.pwm_duration_ms_spin.value(),
            )

            success = self.arduino.configure_pwm(config)

            self.log_arduino(
                f"TX  CONFIG_PWM PIN={config.pin} FREQ_HZ={config.frequency_hz} DUTY={config.duty_percent}"
            )

            self.set_arduino_status(
                "Arduino: PWM Configured" if success else "Arduino: PWM Configure Failed",
                "lime" if success else "red"
            )

            return success

        except Exception as e:

            print(e)
            return False

    def start_arduino_pwm(self):

        try:

            if not self.configure_arduino_pwm():
                return

            success = self.arduino.start_pwm()

            self.log_arduino(
                "TX  START_PWM"
            )

            self.set_arduino_status(
                "Arduino: PWM Started" if success else "Arduino: PWM Start Failed",
                "lime" if success else "red"
            )

        except Exception as e:

            print(e)

    def stop_arduino_pwm(self):

        try:

            if not self.ensure_arduino_ready():
                return

            success = self.arduino.stop_pwm()

            self.log_arduino(
                "TX  STOP_PWM"
            )

            self.set_arduino_status(
                "Arduino: PWM Stopped" if success else "Arduino: PWM Stop Failed",
                "yellow" if success else "red"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # FAST TIMER1 BURST CONTROLS
    # ======================================================

    def configure_fast_burst(self):

        try:

            if not self.ensure_arduino_ready():
                return False

            config = arduino_serial_module.ArduinoFastBurstConfig(
                frequency_hz=self.fast_burst_frequency_spin.value(),
                duty_percent=self.fast_burst_duty_spin.value(),
                cycles_per_burst=self.fast_burst_cycles_spin.value(),
                off_time_us=self.fast_burst_off_us_spin.value(),
                burst_count=self.fast_burst_count_spin.value(),
            )

            success = self.arduino.configure_fast_burst(config)

            self.log_arduino(
                f"TX  CONFIG_FAST_BURST FREQ_HZ={config.frequency_hz} DUTY={config.duty_percent} CYCLES={config.cycles_per_burst} OFF_US={config.off_time_us} BURSTS={config.burst_count}"
            )

            self.set_arduino_status(
                "Arduino: Fast Burst Configured" if success else "Arduino: Fast Burst Configure Failed",
                "lime" if success else "red"
            )

            return success

        except Exception as e:

            print(e)
            return False

    def start_fast_burst(self):

        try:

            if not self.configure_fast_burst():
                return

            success = self.arduino.start_fast_burst()

            self.log_arduino(
                "TX  START_FAST_BURST"
            )

            self.set_arduino_status(
                "Arduino: Fast Burst Running" if success else "Arduino: Fast Burst Start Failed",
                "lime" if success else "red"
            )

        except Exception as e:

            print(e)

    def stop_fast_burst(self):

        try:

            if not self.ensure_arduino_ready():
                return

            success = self.arduino.stop_fast_burst()

            self.log_arduino(
                "TX  STOP_FAST_BURST"
            )

            self.set_arduino_status(
                "Arduino: Fast Burst Stopped" if success else "Arduino: Fast Burst Stop Failed",
                "yellow" if success else "red"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # INCREMENTAL PV1 AMPLITUDE PULSES
    # ======================================================

    def start_incremental_amplitude_train(self):

        try:

            if not self.ensure_arduino_ready():
                return

            self.incremental_sequence = memristor_module.build_linear_amplitude_sequence(
                self.increment_start_v_spin.value(),
                self.increment_stop_v_spin.value(),
                self.increment_step_v_spin.value()
            )

            if not self.incremental_sequence:

                self.warning_label.setText(
                    "Incremental sequence is empty"
                )

                self.warning_label.setStyleSheet(
                    "color:red;"
                )

                return

            self.incremental_running = True
            self.incremental_index = 0

            self.log_arduino(
                f"INCREMENTAL START steps={len(self.incremental_sequence)}"
            )

            self.run_next_incremental_step()

        except Exception as e:

            print(e)

    def stop_incremental_amplitude_train(self):

        try:

            self.incremental_running = False

            try:
                self.device.set_pv1(0)
            except Exception:
                pass

            if self.arduino.is_connected() and self.arduino.is_ready():
                self.arduino.stop_fast_burst()

            self.warning_label.setText(
                "Incremental PV1 pulse train stopped"
            )

            self.warning_label.setStyleSheet(
                "color:red;"
            )

            self.log_arduino(
                "INCREMENTAL STOP PV1=0"
            )

        except Exception as e:

            print(e)

    def run_next_incremental_step(self):

        try:

            if not self.incremental_running:
                return

            if self.incremental_index >= len(self.incremental_sequence):

                self.incremental_running = False

                try:
                    self.device.set_pv1(0)
                except Exception:
                    pass

                self.warning_label.setText(
                    "Incremental PV1 pulse train complete"
                )

                self.warning_label.setStyleSheet(
                    "color:lime;"
                )

                self.log_arduino(
                    "INCREMENTAL COMPLETE PV1=0"
                )

                return

            amplitude = self.incremental_sequence[self.incremental_index]

            self.device.set_pv1(
                amplitude
            )

            width_us = max(
                1,
                self.increment_width_us_spin.value()
            )

            off_us = max(
                1,
                self.increment_off_us_spin.value()
            )

            period_us = width_us + off_us
            frequency_hz = 1000000.0 / period_us
            duty_percent = (width_us / period_us) * 100.0

            config = arduino_serial_module.ArduinoFastBurstConfig(
                frequency_hz=frequency_hz,
                duty_percent=duty_percent,
                cycles_per_burst=1,
                off_time_us=off_us,
                burst_count=1,
            )

            if not self.arduino.configure_fast_burst(config):

                self.stop_incremental_amplitude_train()
                return

            if not self.arduino.start_fast_burst():

                self.stop_incremental_amplitude_train()
                return

            self.incremental_index += 1

            self.warning_label.setText(
                f"Incremental pulse {self.incremental_index}/{len(self.incremental_sequence)} | PV1={amplitude:.3f} V"
            )

            self.warning_label.setStyleSheet(
                "color:cyan;"
            )

            self.log_arduino(
                f"PV1={amplitude:.3f}V TIMER1_PULSE FREQ={frequency_hz:.3f} DUTY={duty_percent:.3f}"
            )

            wait_ms = max(
                2,
                int((period_us + off_us) / 1000) + 5
            )

            QTimer.singleShot(
                wait_ms,
                self.run_next_incremental_step
            )

        except Exception as e:

            print(e)
            self.stop_incremental_amplitude_train()

    # ======================================================
    # SPEED
    # ======================================================

    def update_speed(self):

        self.scope_speed = self.speed_slider.value()

        self.speed_display.display(
            self.scope_speed
        )

        if hasattr(self, "timer"):

            self.timer.start(
                self.scope_speed
            )

    # ======================================================
    # FREEZE
    # ======================================================

    def freeze_scope(self):

        self.freeze_display = not self.freeze_display

        if self.freeze_display:

            self.freeze_btn.setText(
                "Resume"
            )

        else:

            self.freeze_btn.setText(
                "Freeze"
            )

    # ======================================================
    # SEELAB GENERATOR
    # ======================================================

    def update_generator(self):

        try:

            pin = self.pin_select.currentText()
            freq = self.freq_slider.value()
            duty = self.duty_slider.value()
            amplitude = self.amp_slider.value() / 1000

            self.freq_display.display(freq)
            self.duty_display.display(duty)
            self.amp_display.display(amplitude)

            if pin == "SQ1":

                self.device.set_sqr1(freq, duty)

            elif pin == "SQ2":

                self.device.set_sqr2(freq, duty)

            elif pin == "WG":

                self.device.set_wave(freq)

        except Exception as e:

            print(e)

    # ======================================================
    # PV OUTPUTS
    # ======================================================

    def update_pv_outputs(self):

        try:

            pv1_voltage = self.pv1_slider.value() / 1000
            pv2_voltage = self.pv2_slider.value() / 1000

            self.device.set_pv1(
                pv1_voltage
            )

            self.device.set_pv2(
                pv2_voltage
            )

            self.pv1_display.display(
                pv1_voltage
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

        trigger_module.update_scope_engine(
            self,
            self.device
        )

    # ======================================================
    # SAVE TRACE
    # ======================================================

    def save_trace(self):

        try:

            save_module.save_cro_image(
                self.cro_plot
            )

            save_module.save_fft_image(
                self.fft_plot
            )

            self.warning_label.setText(
                "Trace Saved"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # SAVE WAVEFORM
    # ======================================================

    def save_waveform(self):

        try:

            if not hasattr(self, "last_x"):
                return

            if hasattr(self, "last_a2") and self.last_a2 is not None:

                save_module.save_dual_waveform_csv(
                    self.last_x,
                    self.last_a1,
                    self.last_a2,
                    self.last_diff
                )

            else:

                save_module.save_waveform_csv(
                    self.last_x,
                    self.last_y
                )

            self.warning_label.setText(
                "Waveform CSV Saved"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # SAVE FFT
    # ======================================================

    def save_fft(self):

        try:

            if not hasattr(self, "last_fft_x"):
                return

            save_module.save_fft_csv(
                self.last_fft_x,
                self.last_fft_y
            )

            self.warning_label.setText(
                "FFT CSV Saved"
            )

        except Exception as e:

            print(e)

    # ======================================================
    # SAVE EXPERIMENT
    # ======================================================

    def save_experiment(self):

        try:

            pin = self.pin_select.currentText()
            frequency = self.freq_slider.value()
            duty = self.duty_slider.value()
            amplitude = self.amp_slider.value() / 1000
            thd = 0

            save_module.save_experiment_log(
                pin,
                frequency,
                duty,
                amplitude,
                thd
            )

            self.warning_label.setText(
                "Experiment Saved"
            )

        except Exception as e:

            print(e)


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    # WHY: QApplication and hardware connection live here so that importing
    # this module from a test or notebook does not immediately try to connect
    # hardware and call sys.exit() on failure.
    app = QApplication(sys.argv)

    try:
        import eyes17.eyes
        device = eyes17.eyes.open()
        print("SEELab Connected Successfully")
    except Exception as e:
        print(f"SEELab Connection Error: {e}")
        sys.exit(1)

    window = UltraScope(device)
    window.showMaximized()
    sys.exit(app.exec_())
