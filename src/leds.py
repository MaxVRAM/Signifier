#  .____     ___________________
#  |    |    \_   _____/\______ \   ______
#  |    |     |    __)_  |    |  \ /  ___/
#  |    |___  |        \ |    `   \\___ \
#  |_______ \/_______  //_______  /____  >
#          \/        \/         \/     \/

"""
Signifier module to manage communication with the Arduino LED system.
"""

from __future__ import annotations

import time

import multiprocessing as mp
from serial import SerialException
from pySerialTransfer import pySerialTransfer as Arduino

from src.utils import scale
from src.sigmodule import SigModule
from src.sigprocess import ModuleProcess


class Leds(SigModule):
    """
    Arduino serial communications manager module.
    """

    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)

    def create_process(self):
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        self.process = LedsProcess(self)


class LedsProcess(ModuleProcess, mp.Process):
    """
    Process to handle threaded duplex serial communication with the Arduino.
    """

    def __init__(self, parent: Leds) -> None:
        super().__init__(parent)
        # Serial communication
        self.link = None
        self.port = self.config.get("port", "/dev/ttyACM0")
        self.backup_port = self.config.get("backup_port", "/dev/ttyACM1")
        self.baud = self.config.get("baud", 38400)
        self.update_ms = self.config.get("update_ms", 30)
        self.dur_multiplier = self.config.get("duration_multiplier", 3)
        self.rx_packet = ReceivePacket

        if not self.open_connection(self.port):
            self.logger.error(f'Port [{self.port}] invalid. Trying backup '
                              f'port [{self.backup_port}]...'
            )
            if not self.open_connection(self.backup_port):
                self.failed(
                    f"Unable to open serial port. " f"Terminating [{self.module_name}]."
                )
        else:
            for k, v in self.module_values["destinations"].items():
                self.destinations[k] = LedValue(k, v, self)
            if self.parent_pipe.writable:
                self.parent_pipe.send("initialised")

    def pre_run(self) -> bool:
        """
        Module-specific Process run preparation.
        """
        self.start_time = time.time()
        for d in self.destinations.values():
            d.set_default()
        return True

    def mid_run(self):
        """
        Module-specific Process run commands. Where the bulk of the module's
        computation occurs.
        """
        for k in self.dest_values.keys():
            if k in self.destinations:
                self.destinations[k].set_value(**self.dest_values[k])
        try:
            if self.link.available():
                recSize = 0
                self.rx_packet.command = self.link.rx_obj(
                    obj_type="c", start_pos=recSize
                )
                recSize += Arduino.STRUCT_FORMAT_LENGTHS["c"]
                self.rx_packet.valA = self.link.rx_obj(obj_type="l", start_pos=recSize)
                recSize += Arduino.STRUCT_FORMAT_LENGTHS["l"]
                self.rx_packet.valB = self.link.rx_obj(obj_type="l", start_pos=recSize)
                recSize += Arduino.STRUCT_FORMAT_LENGTHS["l"]
                self.process_packet()
            else:
                # If not, check for serial link errors
                if self.link.status < 0:
                    if self.link.status == Arduino.CRC_ERROR:
                        self.logger.error(f'Arduino: CRC_ERROR')
                    elif self.link.status == Arduino.PAYLOAD_ERROR:
                        self.logger.error(f'Arduino: PAYLOAD_ERROR')
                    elif self.link.status == Arduino.STOP_BYTE_ERROR:
                        self.logger.error(f'Arduino: STOP_BYTE_ERROR')
                    else:
                        self.logger.error(f'{self.link.status}')
        except SerialException as exception:
            self.failed(exception)

    def update_values(self):
        """
        Updates LED commands and sends each to Arduino via serial connection.
        """
        for v in self.destinations.values():
            v.send(self.send_packet)

    def process_packet(self):
        """
        Called by the run thread to process received serial packets
        """
        cmd = self.rx_packet.command.decode("utf-8")
        # `r` = "ready to receive packets" - Arduino
        if cmd == "r":
            self.metrics_pusher.update(
                f"{self.module_name}_loop_duration", self.rx_packet.valA
            )
            self.metrics_pusher.update(
                f"{self.module_name}_serial_rx_window", self.rx_packet.valB
            )
            self.update_values()

    def send_packet(self, packet: SendPacket) -> SendPacket:
        """
        Send the Arduino a command via serial, including a value,\
        and duration for the command to run for. Returns the attempted\
        serial packet should the send fail.
        """
        # https://github.com/PowerBroker2/pySerialTransfer/blob/master/examples/data/Python/tx_data.py
        sendSize = 0
        sendSize = self.link.tx_obj(packet.command, start_pos=sendSize)
        sendSize = self.link.tx_obj(packet.value, start_pos=sendSize)
        sendSize = self.link.tx_obj(packet.duration, start_pos=sendSize)
        success = self.link.send(sendSize)
        if not success:
            self.logger.warning(f'Arduino refused packet: {packet}.')
            return packet
        return None

    def open_connection(self, port) -> bool:
        """
        Attempts to open a connection with Arduino on the supplied serial port.
        Returns `False` if port is unavailable, otherwise opens the connection
        and returns `True`.
        """
        try:
            self.link = Arduino.SerialTransfer(port, baud=self.baud)
            self.link.open()
            self.logger.debug(f"Arduino serial connection opened.")
            return True
        except Arduino.InvalidSerialPort:
            return False

    def pre_shutdown(self):
        """
        Module-specific shutdown preparation.
        """
        self.logger.debug(f"Trying to fade out LEDs and close serial port...")
        timeout_start = time.time()
        while time.time() < timeout_start + 0.5:
            if self.link is not None and self.link.available():
                if self.send_packet(SendPacket("Z", 0, 500)) is None:
                    self.logger.debug(f"Arduino received shutdown request.")
                    self.link.close()
                    self.logger.debug(f"Arduino connection terminated.")
                    self.event.set()
                    timeout_start = 0
                    return None
                else:
                    time.sleep(0.001)
        self.logger.error(f"LEDs could not be shutdown gracefully.")


class LedValue:
    """
    Generic class for holding and managing LED parameter states for the Arduino.
    """

    def __init__(self, name: str, config: dict, parent: LedsProcess) -> None:
        self.name = name
        self.command = config["command"]
        self.min = config.get("min", 0)
        self.max = config.get("max", 255)
        self.default = config.get("default", 0)
        self.duration = parent.update_ms * parent.dur_multiplier
        self.packet = SendPacket(self.command, self.default, self.duration)
        self.metrics_pusher = parent.metrics_pusher
        self.updated = True

    def set_value(self, **kwargs):
        """
        Updates the LED parameter and prepares a serial packet to send.
        """
        value = kwargs.get("value", self.default)
        value = int(scale(value, (0, 1), (self.min, self.max), "clamp"))
        duration = kwargs.get("duration", self.duration)
        if value != self.packet.value:
            self.packet = SendPacket(self.command, value, duration)
            self.updated = True

    def set_default(self):
        """
        Creates a new serial packet to send from default parameter values.
        """
        self.packet = SendPacket(self.command, self.default, self.duration)
        print(self.packet)
        self.updated = True
        
    def send(self, send_function, *args) -> bool:
        """
        Returns the serial packet command for the Arduino process to send
        and updates the value in the metrics pusher.
        """
        if self.packet is None:
            return False
        if "force" in args or self.updated:
            if send_function(self.packet) is None:
                self.metrics_pusher.update(self.name, self.packet.value)
                self.updated = False
                return True
        return False


class ReceivePacket(object):
    """
    Simple base static class for reading serial packets from Arduino.
    """

    command = ""
    valA = 0.0
    valB = 0.0


class SendPacket:
    """
    Class to holding serial packets for sending to Arduino.
    """

    def __init__(self, command: str, val: int, dur: int) -> None:
        self.command = command
        self.value = val
        self.duration = dur

    def __repr__(self) -> str:
        return (
            f'Serial Send Packet | "{self.command}", value: ({self.value}), '
            f"duration ({self.duration})ms."
        )
