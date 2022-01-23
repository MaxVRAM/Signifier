
#    _________.__             .__               
#   /   _____/|__| ____  __ __|__| ____   ____  
#   \_____  \ |  |/ ___\|  |  \  |/    \ /  _ \ 
#   /        \|  / /_/  >  |  /  |   |  (  <_> )
#  /_______  /|__\___  /|____/|__|___|  /\____/ 
#          \/   /_____/               \/        

"""A module for the Signify system to control the LED system hosted on a
connected Arduino Nano Every."""

from __future__ import annotations
import time
import enum
import queue
import logging
import threading

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


class ReceivePacket():
    def __init__(self, command=None, valA=None, valB=None) -> None:
        self.command = command
        self.valA = valA
        self.valB = valB
    def __str__(self) -> str:
        return f'Serial Receive Packet | "{self.command}", values: ({self.valA}) and ({self.valB}).'


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
        self.smooth = config.get('smooth', 0)
        self.tx_period = tx_period
        self.tx_time = time.time_ns() // 1_000_000
        self.duration = int(config.get('dur', self.tx_period))
        self.packet = SendPacket(self.command, config.get('default', 0), self.duration)
        self.updated = True


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
                > self.tx_time + self.tx_period):
            if send_function(self.packet) is not None:
                self.tx_time = current_ms
                self.updated = False
                return True
        return False


class Siguino(threading.Thread):   
    def __init__(
            self, return_q, control_q, value_q,
            config:dict, args=(), kwargs=None) -> None:
        super().__init__()
        self.config = config
        self.start_delay = config['start_delay']
        self.event = threading.Event()
        self.return_q = return_q
        self.control_q = control_q
        self.value_q = value_q
        self.state = None
        self.link = None
        self.tx_period = config['update_ms']
        self.force_command = None
        self.values = {}
        # Build all the LED value commands listed in the `config.json`
        # These are updated via the arduino_value_q
        for k, v in self.config['values'].items():
            self.values.update({k:LedValue(v, self.tx_period)})
        print(f'Arduino LED values available:\n{self.values}')


    def run(self):
        """Begin executing Arudino communication thread to control LEDs."""
        logger.debug('Starting Arduino comms thread...')
        self.open_connection()
        self.event.clear()
        while self.state != ArduinoState.closed or not self.event.is_set():
            # Loop while we wait for serial packets from the Arduino
            while not self.link.available():
                # Apply a new state if one is in the queue
                try:
                    state = self.control_q.get_nowait()
                    print(state.name)
                    self.set_state(state)
                except queue.Empty:
                    pass
                # Assign any value updates from the value queue
                if self.state == ArduinoState.running:
                    try:
                        message = self.value_q.get_noswait()
                        print(message)
                        if (value := self.values.get(message[0])) is not None:
                            value.set_value(message[1], None)
                    except queue.Empty:
                        pass
                # Now check for serial link errors
                if self.link.status < 0:
                    if self.link.status == txfer.CRC_ERROR:
                        logger.error('Arduino: CRC_ERROR')
                    elif self.link.status == txfer.PAYLOAD_ERROR:
                        logger.error('Arduino: PAYLOAD_ERROR')
                    elif self.link.status == txfer.STOP_BYTE_ERROR:
                        logger.error('Arduino: STOP_BYTE_ERROR')
                    else:
                        logger.error('ERROR: {}'.format(self.link.status))
            # Only continues once received a packet...
            rx_packet = ReceivePacket()
            recSize = 0
            rx_packet.command = self.link.rx_obj(
                obj_type='c', start_pos=recSize)
            rx_packet.command = rx_packet.command.decode("utf-8")
            recSize += txfer.STRUCT_FORMAT_LENGTHS['c']
            rx_packet.valA = self.link.rx_obj(
                obj_type='l', start_pos=recSize)
            recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
            rx_packet.valB = self.link.rx_obj(
                obj_type='l', start_pos=recSize)
            recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
            self.process_packet(rx_packet)
        # Close everything off if the event has been triggerd
        self.state = ArduinoState.closed
        logger.info('Arduino comms closed.')


    def process_packet(self, rx_packet:ReceivePacket):
        """Called by the run thread to process the received serial packet"""
        # We can send packets once we get a `r` "ready" message.
        # The LEDs require precise timing, so inturrupting a write
        # sequence would cause issues with the LED output.
        if rx_packet.command == 'r':
            if self.state == ArduinoState.starting:
                self.set_state(ArduinoState.running)
            # Regular running state to update LED values when Arduino is ready:
            if self.state == ArduinoState.running:
                for k, v in self.values.items():
                    v.send(self.send_packet)
            # If attempting to pause the LED activity:
            elif self.state == ArduinoState.pause:
                if self.send_packet(SendPacket('B', 0, 500)) is not None:
                    self.set_state(ArduinoState.paused)
                    logger.debug(f'Arduino connection now {self.state.name}')
            # If attempting to close the Arduino but it's still open:
            elif self.state == ArduinoState.close:
                print(self.link.state)
                print('sending arduino off stuff')
                if self.send_packet(SendPacket('B', 0, 1000)) is not None:
                    print('OKAY IT SENT!!!')
                    self.set_state(ArduinoState.closed)
            if self.state == ArduinoState.closed:
                self.event.set()
                self.link.close()
                logger.debug(f'Arduino connection now {self.state.name}')


    def send_packet(self, packet:SendPacket) -> SendPacket:
        """Send the Arduino a command via serial, including a value,\
        and duration for the command to run for. Returns the attempted\
        serial packet should the send fail."""
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
        self.return_q.put(state)
        logger.debug(f'Arduino state now "{self.state.name}"')


    def wait_for_ready(self):
        """Sleep after initialisation to make sure Arduino and\
        RPi start at the same time."""
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
        """TODO will populate with checks and timeouts for Arduino serial\
        connection.\n If reaches timeout before connection, will disable\
        Arduino/LED portion of the Signifier code."""
        self.set_state(ArduinoState.starting)
        self.link = txfer.SerialTransfer('/dev/ttyACM0', baud=38400)
        # self.callback_list = [self.receive_packet]
        # self.link.set_callbacks(self.callback_list)
        # logger.debug(f'({len(self.link.callbacks)}) Arduino callback(s) ready.')
        self.link.open()
        # self.wait_for_ready()
        print()


    def wave(self):
        """Simple sine wave modulation over all LED brightness."""
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