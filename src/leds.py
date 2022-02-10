
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
import enum
import logging
from queue import Full

from pySerialTransfer import pySerialTransfer as Arduino

from serial import SerialException

from src.utils import scale
from src.sigmodule import SigModule, ModuleProcess

logger = logging.getLogger(__name__)


class Leds(SigModule):
    """
    Arduino serial communications manager module.
    """
    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)


    def create_process(self) -> ModuleProcess:
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        new_led = LedsProcess(self)
        if new_led.is_valid():
            return LedsProcess(self)
        else:
            return None


class LedsProcess(ModuleProcess):
    """
    Process to handle threaded duplex serial communication with the Arduino.
    """
    def __init__(self, parent:Leds) -> None:
        super().__init__(parent)
        # Serial communication
        self.link = None
        self.rx_packet = ReceivePacket
        self.state = ArduinoState.idle
        self.port = self.config.get('port', '/dev/ttyACM0')
        self.baud = self.config.get('baud', 38400)
        self.update_ms = self.config.get('update_ms', 30)
        self.dur_multiplier = self.config.get('duration_multiplier', 3)

        if self.open_connection():
            self.is_valid = False
        else:
            for k, v in self.config['destinations'].items():
                self.destinations[k] = self.LedValue(k, v, self)
            logger.debug(f'Arduino commands: {[c for c in self.destinations.keys()]}')


    def run(self):
        """
        Begin executing Arduino communication thread to control LEDs.
        """
        self.start_time = time.time()

        while not self.event.is_set():
            if self.dest_out.poll():
                dest_values = self.dest_out.recv()
                for k in dest_values.keys():
                    if k in self.destinations:
                        self.destinations[k].set_value(**dest_values[k])
            try:
                if self.link.available():
                    recSize = 0
                    self.rx_packet.command = self.link.rx_obj(
                        obj_type='c', start_pos=recSize)
                    recSize += Arduino.STRUCT_FORMAT_LENGTHS['c']
                    self.rx_packet.valA = self.link.rx_obj(
                        obj_type='l', start_pos=recSize)
                    recSize += Arduino.STRUCT_FORMAT_LENGTHS['l']
                    self.rx_packet.valB = self.link.rx_obj(
                        obj_type='l', start_pos=recSize)
                    recSize += Arduino.STRUCT_FORMAT_LENGTHS['l']
                    self.process_packet()
                else:
                    # If not, check for serial link errors
                    if self.link.status < 0:
                        if self.link.status == Arduino.CRC_ERROR:
                            logger.error('Arduino: CRC_ERROR')
                        elif self.link.status == Arduino.PAYLOAD_ERROR:
                            logger.error('Arduino: PAYLOAD_ERROR')
                        elif self.link.status == Arduino.STOP_BYTE_ERROR:
                            logger.error('Arduino: STOP_BYTE_ERROR')
                        else:
                            logger.error('ERROR: {}'.format(self.link.status))
                try:
                    self.source_in.send(self.source_values)
                except Full:
                    pass
                self.metrics.update_dict(self.source_values)
                self.metrics.queue()
                time.sleep(0.001)
                self.check_control_q()

            except SerialException as exception:
                logger.critical(f'Fatal error communicating with Arduino. '
                                f'A restart may be required! {exception}')
                logger.warning(f'Due to error, LED/Arduino module will now '
                                f'be disabled for this session.')
                self.event.set()

        return None


    def process_packet(self):
        """
        Called by the run thread to process received serial packets
        """
        cmd = self.rx_packet.command.decode("utf-8")
        # `r` = "ready to receive packets" - Arduino
        if cmd == 'r':
            self.metrics.update(
                f'{self.module_name}_loop_duration', self.rx_packet.valA)
            self.metrics.update(
                f'{self.module_name}_serial_rx_window', self.rx_packet.valB)
            self.update_values()


    def update_values(self):
        for k, v in self.destinations.items():
            v.send(self.send_packet)


    def set_closed(self) -> bool:
        logger.debug(f'Trying to fade out LEDs and close serial port...')
        timeout_start = time.time()
        if self.link.available():
            while time.time() < timeout_start + 1:
                if self.send_packet(SendPacket('B', 0, 1000)) is None:
                    logger.debug(f'Arduino received shutdown request.')
                    self.link.close()
                    logger.debug(f'Arduino connection terminated.')
                    self.event.set()
                    timeout_start = 0
                    return True
            else:
                time.sleep(0.001)
        logger.error(f'Could not gracefully shutdown Arduino. '
                    f'Forced [{self.state.name}] state')
        self.event.set()
        return False


    def pre_shutdown(self):
        """
        Module-specific shutdown preparation.
        """
        self.set_closed()


    def send_packet(self, packet:SendPacket) -> SendPacket:
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
            logger.warning(f'Arduino refused packet: {packet}.')
            return packet
        return None


    def open_connection(self) -> bool:
        """
        TODO will populate with checks and timeouts for Arduino serial\
        connection.\n If reaches timeout before connection, will disable\
        Arduino/LED portion of the Signifier code.
        """
        try:
            self.link = Arduino.SerialTransfer(self.port, baud=self.baud)
            self.link.open()
            return True
        except Arduino.InvalidSerialPort:
            logger.error('Invalid serial port. Run `arduino-cli board list` '
                            'and update `config.json`')
            self.return_q.put(['failed', self.module_name], timeout=0.1)
            self.event.set()
            return False



class LedValue():
    """
    Generic class for holding and managing LED parameter states for the Arduino.
    """
    def __init__(self, name:str, config:dict, parent) -> None:
        self.name = name
        self.metrics = parent.metrics
        self.command = config['command']
        self.min = config.get('min', 0)
        self.max = config.get('max', 255)
        self.default = config.get('default', 0)
        self.duration = parent.update_ms * parent.dur_multiplier
        self.packet = SendPacket(self.command, self.default, self.duration)
        self.updated = True


    def __str__(self) -> str:
        return f'"{self.name}"'


    def set_value(self, **kwargs):
        """
        Updates the LED parameter and prepares a serial packet to send.
        """
        value = kwargs.get('value', self.default)
        value = int(scale(value, (0, 1), (self.min, self.max), 'clamp'))
        duration = kwargs.get('duration', self.duration)
        if value != self.packet.value:
            self.packet = SendPacket(self.command, value, duration)
            self.updated = True


    def send(self, send_function, *args) -> bool:
        """
        Returns the serial packet command for the Arduino process to send
        and updates the value in the metrics queue dictionary.
        """
        if self.packet is None:
            return False
        if 'force' in args or self.updated:
            if send_function(self.packet) is None:
                self.metrics.update(self.name, self.packet.value)
                self.updated = False
                return True
        return False



class ArduinoState(enum.Enum):
    starting = 1
    running = 2
    idle = 3
    pause = 4
    paused = 5
    close = 6
    closed = 7


class ReceivePacket(object):
    """
    Simple base static class for reading serial packets from Arduino.
    """
    command = ''
    valA = 0.0
    valB = 0.0


class SendPacket():
    """
    Class to holding serial packets for sending to Arduino.
    """
    def __init__(self, command:str, val:int, dur:int) -> None:
        self.command = command
        self.value = val
        self.duration = dur
    def __str__(self) -> str:
        return f'Serial Send Packet | "{self.command}", value: ({self.value}), duration ({self.duration})ms.'

