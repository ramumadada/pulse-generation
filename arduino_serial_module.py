"""
Arduino serial module.

Arduino is the real-time pulse engine.  Python sends configuration commands and
monitors status; it does not perform microsecond pulse loops.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Dict, Optional

try:
    import serial
    import serial.tools.list_ports
except Exception:
    serial = None


@dataclass
class ArduinoPulsePacket:
    pin: int = 9
    high_time_us: int = 1000
    low_time_us: int = 1000
    pulse_count: int = 10
    packet_count: int = 1
    packet_delay_ms: int = 100


@dataclass
class ArduinoPWMConfig:
    pin: int = 9
    frequency_hz: float = 1000.0
    duty_percent: float = 50.0
    duration_ms: int = 0


@dataclass
class ArduinoFastBurstConfig:
    frequency_hz: float = 2_000_000.0
    duty_percent: float = 33.0
    cycles_per_burst: int = 100
    off_time_us: int = 500
    burst_count: int = 0


class ArduinoSerialController:
    """
    Small non-blocking serial controller for Arduino command synchronization.

    Expected Arduino command parser:
        PING TOKEN=<token>
        CONFIG_PULSE PIN=9 HIGH_US=1000 LOW_US=1000 COUNT=10 IDLE=0
        START_PULSE
        STOP_PULSE
        CONFIG_BURST PIN=9 HIGH_US=1000 LOW_US=1000 PULSES=10 PACKETS=5 DELAY_MS=100
        START_BURST
        STOP_BURST
        CONFIG_PWM PIN=9 FREQ_HZ=1000 DUTY=50 DURATION_MS=0
        START_PWM
        STOP_PWM
        CONFIG_FAST_BURST FREQ_HZ=2000000 DUTY=33 CYCLES=100 OFF_US=500 BURSTS=0
        START_FAST_BURST
        STOP_FAST_BURST
    """

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_handle = None
        self.last_line = ""
        self.last_error = ""
        self.last_command = ""
        self.connected = False
        self.ready_at = 0.0
        self.boot_timeout_seconds = 5.0  # max wait for firmware FW token

    def connect(self, port: Optional[str] = None, baudrate: Optional[int] = None) -> bool:
        try:
            if serial is None:
                self.last_error = "pyserial is not installed"
                print(self.last_error)
                return False

            self.disconnect()
            self.port = port or self.port
            self.baudrate = baudrate or self.baudrate

            if not self.port:
                self.last_error = "No Arduino serial port selected"
                print(self.last_error)
                return False

            self.serial_handle = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0.1,
                write_timeout=0.2,
            )
            try:
                self.serial_handle.reset_input_buffer()
                self.serial_handle.reset_output_buffer()
            except Exception:
                pass
            self.connected = True
            self._wait_for_firmware_ready()
            return True

        except Exception as exc:
            self.last_error = str(exc)
            print("Arduino Connect Error")
            print(exc)
            self.connected = False
            return False

    def _wait_for_firmware_ready(self) -> None:
        """Poll for the firmware's FW token instead of sleeping a fixed delay.

        WHY CHANGED: the original code slept 1.8 s regardless of the actual
        boot time. The Arduino firmware sends "FW PGEE_ARDUINO_PULSE_ENGINE 1.0"
        from setup() the moment it is ready. Polling for that token makes
        reconnection fast on quick bootloaders and reliable on slow ones.
        Falls back to a 5 s timeout if the token never arrives (older firmware).
        """
        deadline = time.monotonic() + self.boot_timeout_seconds
        while time.monotonic() < deadline:
            try:
                raw = self.serial_handle.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if line.startswith("FW "):
                    self.ready_at = time.monotonic()
                    return
            except Exception:
                break
        # Firmware token not seen — set ready now as a safe fallback
        self.ready_at = time.monotonic()

    def disconnect(self):
        try:
            if self.serial_handle is not None and self.serial_handle.is_open:
                self.serial_handle.close()
        except Exception as exc:
            print("Arduino Disconnect Error")
            print(exc)
        finally:
            self.serial_handle = None
            self.connected = False
            self.ready_at = 0.0

    def is_connected(self) -> bool:
        try:
            return bool(self.serial_handle is not None and self.serial_handle.is_open)
        except Exception:
            return False

    def is_ready(self) -> bool:
        return self.is_connected() and time.monotonic() >= self.ready_at

    def seconds_until_ready(self) -> float:
        if not self.is_connected():
            return 0.0
        return max(0.0, self.ready_at - time.monotonic())

    def send_command(self, command: str) -> bool:
        try:
            if not self.is_connected():
                self.last_error = "Arduino is not connected"
                print(self.last_error)
                return False

            if not self.is_ready():
                wait_time = self.seconds_until_ready()
                self.last_error = f"Arduino is still booting, wait {wait_time:.1f}s"
                print(self.last_error)
                return False

            self.last_command = command.strip()
            self.serial_handle.write((self.last_command + "\n").encode("ascii"))
            self.serial_handle.flush()
            return True

        except Exception as exc:
            self.last_error = str(exc)
            print("Arduino Write Error")
            print(exc)
            return False

    def read_available_lines(self):
        lines = []
        try:
            if not self.is_connected():
                return lines

            while self.serial_handle.in_waiting:
                raw = self.serial_handle.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    self.last_line = line
                    lines.append(line)
            return lines

        except Exception as exc:
            self.last_error = str(exc)
            print("Arduino Read Error")
            print(exc)
            return lines

    def configure_pulse(self, packet: ArduinoPulsePacket) -> bool:
        command = (
            "CONFIG_PULSE "
            f"PIN={int(packet.pin)} "
            f"HIGH_US={int(packet.high_time_us)} "
            f"LOW_US={int(packet.low_time_us)} "
            f"COUNT={int(packet.pulse_count)} "
            "IDLE=0"
        )
        return self.send_command(command)

    def start_pulse(self) -> bool:
        return self.send_command("START_PULSE")

    def stop_pulse(self) -> bool:
        return self.send_command("STOP_PULSE")

    def configure_burst(self, packet: ArduinoPulsePacket) -> bool:
        command = (
            "CONFIG_BURST "
            f"PIN={int(packet.pin)} "
            f"HIGH_US={int(packet.high_time_us)} "
            f"LOW_US={int(packet.low_time_us)} "
            f"PULSES={int(packet.pulse_count)} "
            f"PACKETS={int(packet.packet_count)} "
            f"DELAY_MS={int(packet.packet_delay_ms)}"
        )
        return self.send_command(command)

    def start_burst(self) -> bool:
        return self.send_command("START_BURST")

    def stop_burst(self) -> bool:
        return self.send_command("STOP_BURST")

    def configure_pwm(self, config: ArduinoPWMConfig) -> bool:
        command = (
            "CONFIG_PWM "
            f"PIN={int(config.pin)} "
            f"FREQ_HZ={float(config.frequency_hz)} "
            f"DUTY={float(config.duty_percent)} "
            f"DURATION_MS={int(config.duration_ms)}"
        )
        return self.send_command(command)

    def start_pwm(self) -> bool:
        return self.send_command("START_PWM")

    def stop_pwm(self) -> bool:
        return self.send_command("STOP_PWM")

    def ping(self, token: str = "PGEE") -> bool:
        return self.send_command(f"PING TOKEN={token}")

    def configure_fast_burst(self, config: ArduinoFastBurstConfig) -> bool:
        command = (
            "CONFIG_FAST_BURST "
            f"FREQ_HZ={float(config.frequency_hz)} "
            f"DUTY={float(config.duty_percent)} "
            f"CYCLES={int(config.cycles_per_burst)} "
            f"OFF_US={int(config.off_time_us)} "
            f"BURSTS={int(config.burst_count)}"
        )
        return self.send_command(command)

    def start_fast_burst(self) -> bool:
        return self.send_command("START_FAST_BURST")

    def stop_fast_burst(self) -> bool:
        return self.send_command("STOP_FAST_BURST")


def list_serial_ports() -> Dict[str, str]:
    if serial is None:
        return {}

    try:
        return {
            port.device: port.description
            for port in serial.tools.list_ports.comports()
        }
    except Exception:
        return {}
