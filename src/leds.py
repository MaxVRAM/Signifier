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
from asyncio.log import logger

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

        time.sleep(0.5)

        if not self.open_connection(self.port):
            self.logger.error(f'Port [{self.port}] invalid. Trying backup '
                              f'port [{self.backup_port}]...'
            )
            if not self.open_connection(self.backup_port):
                self.failed(f"Unable to open serial port. "
                            f"Terminating [{self.module_name}].")
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

    def process_packet(self):
        """
        Called by the run thread to process received serial packets
        """
        cmd = self.rx_packet.command.decode("utf-8")
        if cmd == "r":
            self.update_values()
            self.metrics_pusher.update(
                f"{self.module_name}_loop_duration",
                self.rx_packet.valA)
            self.metrics_pusher.update(
                f"{self.module_name}_serial_rx_window",
                self.rx_packet.valB)
        else:
            for c in self.destinations.values():
                if cmd == c.command:
                    c.confirm(self.rx_packet)

    def update_values(self):
        """
        Updates LED commands and sends each to Arduino via serial connection.
        """
        for v in self.destinations.values():
            v.send(self.send_packet)

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
        fade_out_time = 1
        start_time = time.time()
        while time.time() < start_time + fade_out_time:
            if self.link is not None and self.link.available():
                if self.send_packet(SendPacket("Z", 0, fade_out_time * 1000)) is None:
                    self.logger.debug('Successfully sent shutdown request command to Arduino.')
                    self.poll_control(block_for = fade_out_time)
                    self.link.close()
                    self.logger.debug(f"Arduino connection terminated.")
                    self.event.set()
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
        self.confirmed = False

    def __repr__(self) -> str:
        return (
            f'{self.packet}'
        )

    def set_default(self):
        self.packet = SendPacket(self.command, self.default, self.duration)
        self.updated = True

    def set_value(self, *args, **kwargs):
        """
        Updates the LED parameter and prepares a serial packet to send.
        """
        value = kwargs.get("value", self.default)
        value = int(scale(value, (0, 1), (self.min, self.max), "clamp"))
        duration = kwargs.get("duration", self.duration)
        if value != self.packet.value:
                self.packet = SendPacket(self.command, value, duration)
                self.updated = True
        
    def send(self, send_function, *args) -> bool:
        """
        Returns the serial packet command for the Arduino process to send
        and updates the value in the metrics pusher.
        """
        if self.packet is None:
            return False
        if "force" in args or self.updated or not self.confirmed:
            bounced_packet = send_function(self.packet)
            if bounced_packet is None:
                self.metrics_pusher.update(self.name, self.packet.value)
                self.updated = False
                self.confirmed = False
                return True
        return False

    def confirm(self, rx):
        if (self.command == rx.command.decode("utf-8") and
                self.packet.value == rx.valA and self.packet.duration == rx.valB):
            self.confirmed = True
            self.metrics_pusher.update(self.name, self.packet.value)
        return None
        


class ReceivePacket(object):
    """
    Simple base static class for reading serial packets from Arduino.
    """

    command = ""
    valA = 0.0
    valB = 0.0

    def __repr__(self) -> str:
        return (
            f'Arduino received packet | "{self.command}", '
            f'value: ({self.valA}), '
            f"duration ({self.valB})ms."
        )

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
            f'Arduino send packet | "{self.command}", value: ({self.value}), '
            f"duration ({self.duration})ms."
        )
