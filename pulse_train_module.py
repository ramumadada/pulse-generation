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
    device=None,
    pin="SQ1",
    frequency=1000,
    duty=50,
    pulse_count=10,
    pulse_delay=0.01,
    arduino_controller=None,
    arduino_pin=9,
):
    """
    Generate identical pulses through Arduino.

    The device argument is preserved for compatibility with old GUI calls, but
    it is not used for pulse timing.
    """

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
    device=None,
    start_voltage=0.5,
    stop_voltage=3.0,
    voltage_step=0.1,
    pulse_delay=0.05,
    arduino_controller=None,
    arduino_pin=9,
    pulse_width_us=1000,
):
    """
    Configure a safe incremental-amplitude experiment skeleton.

    PV1 amplitude stepping is not timing-critical, but the pulse itself must be
    executed by Arduino.  The GUI/automation layer should step PV1 between
    Arduino pulse packets.
    """

    try:
        if arduino_controller is None:
            print("Arduino controller required for safe incremental pulse timing")
            return False

        if device is not None:
            safe_voltage = min(max(float(start_voltage), 0.0), 5.0)
            device.set_pv1(safe_voltage)

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
    device=None,
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
