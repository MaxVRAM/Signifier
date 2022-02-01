
#     _____            .___    .__               
#    /  _  \_______  __| _/_ __|__| ____   ____  
#   /  /_\  \_  __ \/ __ |  |  \  |/    \ /  _ \ 
#  /    |    \  | \/ /_/ |  |  /  |   |  (  <_> )
#  \____|__  /__|  \____ |____/|__|___|  /\____/ 
#          \/           \/             \/        

"""
Signifier module to manage communication with the Arduino LED system.
"""

from __future__ import annotations

import time
import enum
import logging
import multiprocessing as mp
from queue import Empty, Full

from pySerialTransfer import pySerialTransfer as txfer

from prometheus_client import Gauge
from serial import SerialException

from signify.utils import scale
from signify.utils import plural

logger = logging.getLogger(__name__)


class Leds():
    """
    Arduino serial communications manager module.
    """
    def __init__(self, name:str, config:dict, *args, **kwargs) -> None:
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        self.start_delay = self.config.get('start_delay', 2)
        self.process = None
        # Process management
        self.state_q = mp.Queue(maxsize=1)
        self.destination_in, self.destination_out = mp.Pipe()
        self.registry = kwargs.get('prom_registry', None)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Arduino LED processes.
        """
        logger.info(f'Updating LED module configuration...')
        if self.enabled:
            self.config = config[self.module_name]
            if self.config.get('enabled', False) is False:
                self.stop()
            else:
                self.stop()
                self.initialise()
                self.start()
        else:
            self.config = config[self.module_name]
            if self.config.get('enabled', False) is True:
                self.start()
            else:
                pass


    def initialise(self):
        """
        Creates a new LED process for Arduino communications.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.ArduinoProcess(self)
                logger.info(f'LED module initialised.')
            else:
                logger.warning(f'LED module already initialised!')
        else:
            logger.warning(f'Cannot create LED process, module not enabled!')


    def start(self):
        """
        Creating a multi-core LED process and starts the routine.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    logger.info(f'LED process started.')
                    if self.start_delay > 0:
                        logger.debug(f'Pausing for {self.start_delay} '
                                     f'second{plural(self.start_delay)}...')
                else:
                    logger.warning(f'Cannot start LED process, already running!')
            else:
                logger.warning(f'Trying to start LED process but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start LED process, module is not enabled.')


    def stop(self):
        """
        Asks the Arduino link to close and shuts down the processing thread.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'LED process shutting down...')
                self.set_state('close', timeout=2)
                #self.arduino_process.event.set()
                self.process.join(timeout=1)
                self.process = None
                logger.info(f'LED process stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop LED process, not running.')
        else:
            logger.debug(f'Ignoring request to stop LED process, module is not enabled.')


    def set_state(self, state:str, timeout=0.5):
        """
        Sends a new `state=(str)` to LED process via a queue.
        """
        if self.process is not None:
            try:
                logger.debug(f'Trying to send LED thread "{state}" state.')
                self.state_q.put(state, timeout=timeout)
                logger.debug(f'Sent state "{state}" to LED thread.')
                return True
            except Full:
                logger.warning(f'Timed out sending "{state}" state to LED thread!')
                return False
        return False


    class ArduinoProcess(mp.Process):
        """
        Multiprocessing Process to handle threaded serial communication
        with the Arduino.
        """
        def __init__(self, parent:Leds) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.parent = parent
            self.event = mp.Event()
            self.destination_out = parent.destination_out
            self.state_q = parent.state_q
            # Serial communication
            self.link = None
            self.state = ArduinoState.idle
            self.port = parent.config.get('port', '/dev/ttyACM0')
            self.baud = parent.config.get('baud', 38400)
            self.rx_packet = ReceivePacket
            self.update_ms = parent.config.get('update_ms', 30)
            self.duration_multiplier = parent.config.get('duration_multiplier', 3)
            self.commands = {}
            for k, v in parent.config['destinations'].items():
                self.commands.update({k:LedValue(f'{self.parent.module_name}_{k}',
                                                 v, self.update_ms,
                                                 self.duration_multiplier,
                                                 registry=parent.registry)})


        def run(self):
            """
            Begin executing Arudino communication thread to control LEDs.
            """
            logger.debug(f'Arduino commands: {[c for c in self.commands.keys()]}')
            self.event.clear()
            self.open_connection()
            self.start_time = time.time()
            # Loop to process queue/pipe updates and serial packets
            while self.state != ArduinoState.closed:
                # Prioritise apply a new state if one is in the queue
                try:
                    #state = self.control_q.recv()
                    state = self.state_q.get_nowait()
                    self.set_state(ArduinoState[state])
                except Empty:
                    pass
                # Snap up the input value pipe dict, update new values
                if self.state not in [ArduinoState.close, ArduinoState.closed]:
                    if self.destination_out.poll():
                        dest_values = self.destination_out.recv()
                        for k in dest_values.keys():
                            #print(dest_values[k])
                            if k in self.commands:
                                self.commands[k].set_value(**dest_values[k])
                # Check for any available serial packets from the Arduino
                try:
                    if self.link.available():
                        recSize = 0
                        self.rx_packet.command = self.link.rx_obj(
                            obj_type='c', start_pos=recSize)
                        recSize += txfer.STRUCT_FORMAT_LENGTHS['c']
                        self.rx_packet.valA = self.link.rx_obj(
                            obj_type='l', start_pos=recSize)
                        recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
                        self.rx_packet.valB = self.link.rx_obj(
                            obj_type='l', start_pos=recSize)
                        recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
                        self.process_packet()
                    else:
                        # If not, check for serial link errors
                        if self.link.status < 0:
                            if self.link.status == txfer.CRC_ERROR:
                                logger.error('Arduino: CRC_ERROR')
                            elif self.link.status == txfer.PAYLOAD_ERROR:
                                logger.error('Arduino: PAYLOAD_ERROR')
                            elif self.link.status == txfer.STOP_BYTE_ERROR:
                                logger.error('Arduino: STOP_BYTE_ERROR')
                            else:
                                logger.error('ERROR: {}'.format(self.link.status))
                except SerialException as exception:
                    logger.critical(f'Fatal error communicating with Arduino. '
                                    f'A restart may be required! {exception}')
                    logger.warning(f'Due to error, LED/Arduino moduel will now '
                                   f'be disabled for this session.')
                    break
                    
                # Push updated values to Prometheus push gateway

            # Close everything off just in case something got missed
            self.state = ArduinoState.closed
            self.link.close()
            self.event.set()


        def process_packet(self):
            """
            Called by the run thread to process the received serial packet
            """
            # Waits for `r` "ready" message before sending packets.
            # The LEDs require precise timing, so inturrupting an LED write
            # sequence would cause issues with the LED output.
            cmd = self.rx_packet.command.decode("utf-8")
            run_time = round((time.time() - self.start_time) * 1000)
            if cmd == 'r':
                # Wait for first Arduino "ready" message before sending LED values
                if self.state == ArduinoState.starting:
                    self.set_state(ArduinoState.running)
                # Send any updated LED values if module is "running"
                if self.state == ArduinoState.running:
                    self.update_values()
                # Pause LED activity
                elif self.state == ArduinoState.pause:
                    self.set_paused()
                # If attempting to close the Arduino but it's still open:
                elif self.state == ArduinoState.close:
                    self.set_closed()
                elif self.state == ArduinoState.closed:
                    logger.debug(f'Arduino connection is {self.state.name}')
                    # self.link.close()
                    self.event.set()


        def set_state(self, state:ArduinoState):
            self.state = state
            logger.debug(f'Arduino state now "{self.state.name}"')
            if self.state in [ArduinoState.close, ArduinoState.closed]:
                self.set_closed()


        def update_values(self):
            for k, v in self.commands.items():
                v.send(self.send_packet)


        def set_paused(self) -> bool:
            logger.debug(f'Attempting LED fade out and pause Arduino comms...')
            timeout_start = time.time()
            while time.time() < timeout_start + 1:
                if self.send_packet(SendPacket('B', 0, 500)) is not None:
                    self.set_state(ArduinoState.paused)
                    logger.debug(f'Arduino connection now {self.state.name}')
                    return True
                time.sleep(0.01)
            logger.error(f'Could not set LED state to "paused"!')
            return False


        def set_closed(self) -> bool:
            logger.debug(f'Trying to fade out LEDs and close serial port...')
            timeout_start = time.time()
            while time.time() < timeout_start + 1:
                if self.link.available():
                    if self.send_packet(SendPacket('B', 0, 1000)) is None:
                        logger.debug(f'Arduino received shutdown request.')
                        self.state = ArduinoState.closed
                        self.link.close()
                        logger.debug(f'Arduino connection terminated.')
                        self.event.set()
                        timeout_start = 0
                        return True
                else:
                    time.sleep(0.01)
            self.set_state(ArduinoState.closed)
            logger.error(f'Could not gracefully shutdown Arduino. '
                        f'Forced {self.state.name} state')
            self.link.close()
            self.event.set()
            return False


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
                logger.warn(f'Arduino refused packet: {packet}.')
                return packet
            return None


        def open_connection(self) -> bool:
            """
            TODO will populate with checks and timeouts for Arduino serial\
            connection.\n If reaches timeout before connection, will disable\
            Arduino/LED portion of the Signifier code.
            """
            self.set_state(ArduinoState.starting)
            self.link = txfer.SerialTransfer(self.port, baud=self.baud)
            self.link.open()


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


class LedValue():
    """
    Generic class for holding and managing LED parameter states for the Arduino.
    """
    def __init__(self, name:str, config:dict, update_ms:float, multiplier:int, registry=None) -> None:
        self.name = name
        self.command = config['command']
        self.min = config.get('min', 0)
        self.max = config.get('max', 255)
        self.default = config.get('default', 0)
        self.smooth = config.get('smooth', 0)
        self.description = config.get('description', 'Description not defined.')
        self.duration = update_ms * multiplier
        self.packet = SendPacket(self.command, self.default, self.duration)
        self.updated = True
        self.gauge = Gauge(self.name, self.description, registry=registry)


    def __str__(self) -> str:
        return f'"{self.command}"'


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
        Returns the serial packet command for the Arduino process to send.
        """
        if self.packet is None:
            return False
        if 'force' in args or self.updated:
            if send_function(self.packet) is None:
                self.gauge.set(self.packet.value)
                self.updated = False
                return True
        return False
