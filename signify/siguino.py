
#    _________.__             .__               
#   /   _____/|__| ____  __ __|__| ____   ____  
#   \_____  \ |  |/ ___\|  |  \  |/    \ /  _ \ 
#   /        \|  / /_/  >  |  /  |   |  (  <_> )
#  /_______  /|__\___  /|____/|__|___|  /\____/ 
#          \/   /_____/               \/        

"""
A module for the Signify system to control the LED system hosted on a
connected Arduino Nano Every.
"""

from __future__ import annotations
import time
import enum
import logging
from queue import Empty, Full
from multiprocessing import Process, Queue, Event
import multiprocessing as mp

from pySerialTransfer import pySerialTransfer as txfer

from signify.utils import scale as scale

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ArduinoState(enum.Enum):
    starting = 1
    running = 2
    idle = 3
    pause = 4
    paused = 5
    close = 6
    closed = 7


class ReceivePacket(object):
    command = ''
    valA = 0.0
    valB = 0.0


class SendPacket():
    def __init__(self, command:str, val:int, dur:int) -> None:
        self.command = command
        self.value = val
        self.duration = dur
    def __str__(self) -> str:
        return f'Serial Send Packet | "{self.command}", value: ({self.value}), duration ({self.duration})ms.'


class LedValue:
    def __init__(self, config:dict, tx_period:int) -> None:
        self.command = config['command']
        self.min = config.get('min', 0)
        self.max = config.get('max', 255)
        self.default = config.get('default', 0)
        self.smooth = config.get('smooth', 1)
        self.update_ms = tx_period
        self.tx_time = time.time_ns() // 1_000_000
        self.duration = int(config.get('dur', self.update_ms)) * 2
        self.packet = SendPacket(self.command, self.default, self.duration)
        self.updated = True


    def __str__(self) -> str:
        return f'"{self.command}", min/max: ({self.min}/{self.max}), default: ({self.default})'


    def set_value(self, value, duration=None):
        dur = duration if duration is not None else self.duration
        value = int(scale(value, (0, 1), (self.min, self.max), 'clamp'))
        self.packet = SendPacket(self.command, value, dur)
        self.updated = True


    def send(self, send_function, *args) -> bool:
        if self.packet is None:
            return False
        if 'force' in args or (self.updated and (
            current_ms := time.time_ns() // 1_000_000)\
                > self.tx_time + self.update_ms):
            if send_function(self.packet) is None:
                self.tx_time = current_ms
                self.updated = False
                return True
        return False


class Siguino(Process):
    def __init__(self, 
            return_q:mp.Queue, control_q:mp.Queue, value_pipe,
            config:dict, args=(), kwargs=None) -> None:
        super().__init__()
        self.daemon = True
        self.config = config
        self.baud = self.config.get('baud', 38400)
        self.start_delay = self.config['start_delay']
        # Thread/state management
        self.state = ArduinoState.idle
        self.event = Event()
        self.return_q = return_q
        self.control_q = control_q
        self.value_pipe = value_pipe
        # Serial communication
        self.link = None
        self.values = {}
        self.rx_packet = ReceivePacket
        self.update_ms = self.config['update_ms']
        for k, v in self.config['values'].items():
            self.values.update({k:LedValue(v, self.update_ms)})


    def run(self):
        """
        Begin executing Arudino communication thread to control LEDs.
        """
        logger.debug('Starting Arduino comms thread...')
        for k in self.values.keys():
            logger.debug(f' - Arduino values available: {self.values[k]}')
        self.event.clear()
        self.open_connection()
        self.start_time = time.time()
        # Loop while we wait for serial packets from the Arduino
        while self.state != ArduinoState.closed:
            # Prioritise apply a new state if one is in the queue
            try:
                #state = self.control_q.recv()
                state = self.control_q.get_nowait()
                self.set_state(ArduinoState[state])
            except Empty:
                pass
            # Quickly snap up the value queue
            if self.state != ArduinoState.close:
                if self.value_pipe.poll():
                    v = self.value_pipe.recv()
                    print(v)
                    if (value := self.values.get(v[0])) is not None:
                        value.set_value(v[1], None)
            # Next, check for any available serial packets from the Arduino
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


        # Close everything off just in case something got missed
        self.link.close()
        self.event.set()
        self.state = ArduinoState.closed
        logger.info('Arduino comms closed.')


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
                #print(f'arduino update time send success: {self.send_packet(SendPacket("l", self.update_ms, 0))}')
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
        else:        
            print(f'{run_time} Got "{cmd}" from Arduino with {self.rx_packet.valA}, {self.rx_packet.valB}')


    def update_values(self):
        for k, v in self.values.items():
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
        logger.error(f'Could not set Arduino state to "paused"!')
        return False


    def set_closed(self) -> bool:
        logger.debug(f'Trying to fade out LEDs and close serial port...')
        timeout_start = time.time()
        while time.time() < timeout_start + 1:
            if self.link.available():
                if self.send_packet(SendPacket('B', 0, 1000)) is None:
                    logger.debug(f'Arduino received shutdown request, terminating connection.')
                    self.state = ArduinoState.closed
                    self.link.close()
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


    def set_state(self, state:ArduinoState):
        self.state = state
        logger.debug(f'Arduino state now "{self.state.name}"')
        if self.state == ArduinoState.closed:
            self.set_closed()


    def wait_for_ready(self):
        """
        Sleep after initialisation to make sure Arduino and\
        RPi start at the same time.
        """
        # TODO: Replace with a serial message callback for Arduino ready.
        print()
        logger.info(f'Signifier ready! Delaying start to make sure Arduino '
                    f'is ready. Starting in ({self.start_delay}) seconds...')
        time.sleep(1)
        for i in range(1, self.start_delay):
            print(f'...{self.start_delay-i}')
            time.sleep(1)
        print()


    def open_connection(self) -> bool:
        """
        TODO will populate with checks and timeouts for Arduino serial\
        connection.\n If reaches timeout before connection, will disable\
        Arduino/LED portion of the Signifier code.
        """
        self.set_state(ArduinoState.starting)
        self.link = txfer.SerialTransfer('/dev/ttyACM0', baud=self.baud)
        self.link.open()
        print()


    def wave(self):
        """
        Simple sine wave modulation for generating patterns.
        """
        # Flash
        # if brightness_value == 0:
        #     brightness_value = 1
        # else:
        #     brightness_value = 0
        #
        # Random
        # brightness_value = random.triangular(0.0, 1.0, 0.5)
        #
        # Slow sine pulse
        #self.brightness = (math.sin(time.time()*2) + 1) / 2
        return None