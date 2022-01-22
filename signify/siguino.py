
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


class ReceivePacket(object):
    command = ''
    value = 0
    duration = 0


class SendPacket():
    def __init__(self, cmd:str, val:int, dur:int) -> None:
        self.command = cmd
        self.value = val
        self.duration = dur
    def __str__(self) -> str:
        return f'Serial Send Packet | "{self.command}", value: ({self.value}), duration ({self.duration})ms.'


class LedValue:
    def __init__(self, config:dict, tx_period:int) -> None:
        self.cmd = config['cmd']
        self.min = config.get('min') or 0
        self.max = config.get('max') or 255
        self.smooth = config.get('smooth') or 0
        self.tx_period = tx_period
        self.duration = int(config.get('dur') or tx_period)
        self.tx_time = time.time_ns() // 1_000_000
        self.updated = False
        self.packet = None


    def set_value(self, value):
        value = int(scale(value, (0, 1), (self.min, self.max), 'clamp'))
        self.packet = SendPacket(self.cmd, value, self.duration)
        self.updated = True


    def get_packet(self) -> SendPacket:
        if self.packet is not None:
            if self.updated and (
                current_ms := time.time_ns() // 1_000_000)\
                    > self.tx_time + self.tx_period:
                self.tx_time = current_ms
                self.updated = False
                return self.packet
            else:
                return None
        else:
            return None



def scale(value, source_range, dest_range, *args):
        """
        Scale the given value from the scale of src to the scale of dst.\
        Send argument `clamp` to limit output to destination range as well.
        """
        s_range = source_range[1] - source_range[0]
        d_range = dest_range[1] - dest_range[0]
        scaled_value = ((value - source_range[0]) / s_range) * d_range + dest_range[0]
        if 'clamp' in args:
            return max(dest_range[0], min(dest_range[1], scaled_value))
        return scaled_value


class Siguino:   
    def __init__(self, config:dict) -> None:
        self.config = config
        self.start_delay = config['start_delay']
        self.enabled = config['enabled']
        self.callback_list = None
        self.rx_packet = ReceivePacket
        self.active = False
        self.state = ArduinoState.run
        self.link = None
        self.tx_period = config['update_ms']

        self.bright = LedValue(config['brightness'], self.tx_period)
        self.saturation = None
        self.hue = None


    def callback_tick(self) -> ReceivePacket:
        self.rx_packet = None
        if self.active:
            self.link.tick()
            return self.rx_packet


    def send_packet(self, cmd:str, val:int, dur:int):
        """Send the Arduino a command via serial, including a value,\
        and duration for the command to run for."""
        # https://github.com/PowerBroker2/pySerialTransfer/blob/master/examples/data/Python/tx_data.py
        sendSize = 0
        sendSize = self.link.tx_obj(cmd, start_pos=sendSize)
        sendSize = self.link.tx_obj(val, start_pos=sendSize)
        sendSize = self.link.tx_obj(dur, start_pos=sendSize)
        success = self.link.send(sendSize)
        if not success:
            logger.warn(f'Ardiuno did not accept my packet "{cmd}" with value ({val}) over ({dur})ms.')
        return None
    

    
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


    def receive_packet(self):
        """Called when `arduino.tick()` receives a serial message from the\
        Arduino, automatically parsing the serial packets for processing (i.e.\
        using the `arduino.rx_obj()` function).\n Depending on the message\
        received, this function may or may not execute additional commands."""
        if self.active:
            self.rx_packet = ReceivePacket
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
                    # Get new packets if there's been any updates
                    # Send them to the Arduino
                    bright = self.bright.get_packet()
                    if bright is not None:
                        self.send_packet(bright.command,bright.value,bright.duration)

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
            self.rx_packet = None


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
