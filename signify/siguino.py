
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
import math
import enum
import queue
import logging

from ctypes import c_wchar
from datetime import datetime as dt

from pySerialTransfer import pySerialTransfer as txfer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ArduinoState(enum.Enum):
    run = 1
    pause = 2
    paused = 3
    close = 4
    closed = 5


class SerialPacket(object):
    command = ''
    value = 0
    duration = 0


class Siguino:   
    def __init__(self, config:dict) -> None:
        self.enabled = config['enabled']
        self.active = False
        self.state = ArduinoState.run
        self.link = None
        self.start_delay = config['start_delay']
        self.tx_time = time.time_ns() // 1_000_000
        self.tx_period = config['send_period']
        self.rx_packet = SerialPacket
        self.brightness = 0
        self.callback_list = None
        self.send_q = queue.Queue(maxsize=10)
        

    def callback_tick(self) -> SerialPacket:
        self.rx_packet = None
        if self.active:
            self.link.tick()
            return self.rx_packet


    def send_packet(self, command: c_wchar, value: int, duration: int) -> bool:
        """Send the Arduino a command via serial, including a value,\
        and duration for the command to run for."""
        # https://github.com/PowerBroker2/pySerialTransfer/blob/master/examples/data/Python/tx_data.py
        sendSize = 0
        value = int(value)
        sendSize = self.link.tx_obj(command, start_pos=sendSize)
        sendSize = self.link.tx_obj(value, start_pos=sendSize)
        sendSize = self.link.tx_obj(duration, start_pos=sendSize)
        success = self.link.send(sendSize)
        return success
    
    
    def brightness_wave(self):
        """Simple sine wave modulation over all LED brightness."""
        if (current_ms := time.time_ns() // 1_000_000)\
                > self.tx_time + self.tx_period:
            self.tx_time = current_ms

            dur = int(self.tx_period)
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
            self.brightness = int(((
                math.sin(time.time()*2) + 1) / 2) * 255)
            self.send_packet('B', self.brightness, dur)


    def send_brightness(self, bright=None, duration=None):
        """Extremely simple modulation of all LED brightness.\n
        Sends when receiving the following 'ready' message from\
        the Arduino once it has been `tx_limit:(ms)` after the
        last brightness tx."""
        if (current_ms := time.time_ns() // 1_000_000)\
                > self.tx_time + self.tx_period:
            self.tx_time = current_ms
            self.brightness = bright if bright is not None else self.brightness
            dur = duration if duration is not None else int(self.tx_period)
            self.send_packet('B', self.brightness, dur)
            print(f'{dt.now()}    SEND TO ARDUINO: "B" '
                f'{self.brightness} {dur}')


    def set_brightness_norm(self, bright:float):
        """Simply scales the supplied bright argument from 0-1 to 0-255
        and sets the value to the Arduino object's self.brightness."""
        self.brightness = int(max(0, min(255, bright * 255)))


    def receive_packet(self):
        """Called when `arduino.tick()` receives a serial message from the\
        Arduino, automatically parsing the serial packets for processing (i.e.\
        using the `arduino.rx_obj()` function).\n Depending on the message\
        received, this function may or may not execute additional commands."""
        if self.active:
            self.rx_packet = SerialPacket
            recSize = 0
            self.rx_packet.command = self.link.rx_obj(
                obj_type='c', start_pos=recSize)
            self.rx_packet.command = self.rx_packet.command.decode("utf-8")
            recSize += txfer.STRUCT_FORMAT_LENGTHS['c']
            self.rx_packet.value = self.link.rx_obj(
                obj_type='l', start_pos=recSize)
            recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
            self.rx_packet.duration = self.link.rx_obj(
                obj_type='l', start_pos=recSize)
            recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
            
            if self.rx_packet.command == 'r':
                if self.state == ArduinoState.run:
                    self.brightness_wave()
                    # self.send_brightness()
                elif self.state == ArduinoState.pause:
                    print()
                    print()
                    logger.debug(f'Arduino gave ready message, and is "{self.state.name}".')
                    print()
                    print()
                    self.send_packet('B', 0, 500)
                    self.state = ArduinoState.paused
                elif self.state == ArduinoState.close:
                    self.close_serial()


    def set_state(self, state:ArduinoState):
        logger.debug(f'Arduino state set to "{state.name}"')
        self.state = state


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

        
    def open_serial(self) -> bool:
        """TODO will populate with checks and timeouts for Arduino serial\
        connection.\n If reaches timeout before connection, will disable\
        Arduino/LED portion of the Signifier code."""
        if self.enabled is True:
            self.link = txfer.SerialTransfer('/dev/ttyACM0', baud=38400)
            self.callback_list = [self.receive_packet]
            self.link.set_callbacks(self.callback_list)
            logger.debug(f'({len(self.link.callbacks)}) Arduino callback(s) ready.')
            self.link.open()
            self.wait_for_ready()
            self.active = True
        logger.info(f'Arduino connection active: {self.active}')
        print()


    def close_serial(self):
        if self.active:
            logger.debug('Closing Arduino serial connection...')
            self.state = ArduinoState.closed
            self.send_packet('B', 0, 900)
            time.sleep(1)
            self.link.close()
            self.active = False