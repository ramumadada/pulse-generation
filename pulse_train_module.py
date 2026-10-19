# ==========================================================
# pulse_train_module.py
# ==========================================================
#
# Arduino owns real-time pulse timing.  This module prepares pulse packets and
# sends commands to arduino_serial_module.  It intentionally avoids repeated
# software toggling of SEELab SQ1/SQ2 in Python loops.

from __future__ import annotations

from arduino_serial_module import ArduinoPulsePacket


def frequency_duty_to_timing_us(frequency, duty):
    try:
        safe_frequency = max(0.1, float(frequency))
        safe_duty = min(max(float(duty), 0.1), 99.9)

        period_us = 1_000_000.0 / safe_frequency
        high_time_us = max(1, int(period_us * safe_duty / 100.0))
        low_time_us = max(1, int(period_us - high_time_us))

        return high_time_us, low_time_us

    except Exception as exc:
        print("Pulse Timing Conversion Error")
        print(exc)
        return 1000, 1000


def identical_pulses(
    pin="SQ1",
    frequency=1000,
    duty=50,
    pulse_count=10,
    pulse_delay=0.01,
    arduino_controller=None,
    arduino_pin=9,
):
    """Generate identical pulses through Arduino."""

    try:
        if arduino_controller is None:
            print("Arduino controller required for safe identical pulse timing")
            return False

        high_time_us, low_time_us = frequency_duty_to_timing_us(frequency, duty)

        packet = ArduinoPulsePacket(
            pin=arduino_pin,
            high_time_us=high_time_us,
            low_time_us=low_time_us,
            pulse_count=int(pulse_count),
            packet_delay_ms=max(0, int(float(pulse_delay) * 1000)),
        )

        if not arduino_controller.configure_pulse(packet):
            return False

        return arduino_controller.start_pulse()

    except Exception as exc:
        print("Identical Pulse Error")
        print(exc)
        return False


def incremental_amplitude_pulses(
    start_voltage=0.5,
    stop_voltage=3.0,
    voltage_step=0.1,
    pulse_delay=0.05,
    arduino_controller=None,
    arduino_pin=9,
    pulse_width_us=1000,
):
    """Configure an incremental-amplitude pulse skeleton.

    Voltage stepping is handled by the GUI layer calling
    arduino_controller.set_voltage_pwm() between packets.
    WHY CHANGED: removed device (SEELab) parameter — voltage bias is now
    provided by Arduino PWM output via set_voltage_pwm().
    """
    try:
        if arduino_controller is None:
            print("Arduino controller required for safe incremental pulse timing")
            return False

        packet = ArduinoPulsePacket(
            pin=arduino_pin,
            high_time_us=max(1, int(pulse_width_us)),
            low_time_us=max(1, int(float(pulse_delay) * 1_000_000)),
            pulse_count=1,
        )

        if not arduino_controller.configure_pulse(packet):
            return False

        return arduino_controller.start_pulse()

    except Exception as exc:
        print("Incremental Pulse Error")
        print(exc)
        return False


def burst_pulses(
    burst_count=5,
    pulses_per_burst=10,
    frequency=1000,
    duty=50,
    burst_delay=0.5,
    arduino_controller=None,
    arduino_pin=9,
):
    """Generate pulse bursts through Arduino packet mode."""

    try:
        if arduino_controller is None:
            print("Arduino controller required for safe burst pulse timing")
            return False

        high_time_us, low_time_us = frequency_duty_to_timing_us(frequency, duty)

        packet = ArduinoPulsePacket(
            pin=arduino_pin,
            high_time_us=high_time_us,
            low_time_us=low_time_us,
            pulse_count=int(pulses_per_burst),
            packet_count=int(burst_count),
            packet_delay_ms=max(0, int(float(burst_delay) * 1000)),
        )

        if not arduino_controller.configure_burst(packet):
            return False

        return arduino_controller.start_burst()

    except Exception as exc:
        print("Burst Pulse Error")
        print(exc)
        return False
