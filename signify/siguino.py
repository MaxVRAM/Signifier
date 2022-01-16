
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
import logging

from ctypes import c_wchar
from datetime import datetime as dt

from pySerialTransfer import pySerialTransfer as txfer

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class serialPacket(object):
    command = ''
    value = 0
    duration = 0


class Siguino:   
    def __init__(self, config:dict) -> None:
        self.active = False
        self.link = None
        self.start_delay = config['start_delay']
        self.tx_time = time.time_ns() // 1_000_000
        self.tx_period = config['send_period'] = 20
        self.rx_packet = serialPacket
        self.brightness = 0
        self.callback_list = None
        

    def callback_tick(self) -> serialPacket:
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


    def receive_packet(self):
        """Called when `arduino.tick()` receives a serial message from the\
        Arduino, automatically parsing the serial packets for processing (i.e.\
        using the `arduino.rx_obj()` function).\n Depending on the message\
        received, this function may or may not execute additional commands."""
        if self.active:
            self.rx_packet = serialPacket
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
                # Test message for checking Arduino Tx/Rx and LED control
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
                    brightness_value = int(((
                        math.sin(time.time()*3) + 1) / 2) * 255)
                    self.send_packet('B', brightness_value, dur)
                    # print(f'{dt.now()}    SEND TO ARDUINO: "B" '
                    #     f'{brightness_value} {dur}')


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
        if self.active is not True:
            self.link = txfer.SerialTransfer('/dev/ttyACM0', baud=38400)
            self.callback_list = [self.receive_packet]
            self.link.set_callbacks(self.callback_list)
            logger.debug(f'({len(self.link.callbacks)})\
                Arduino callback(s) set.')
            self.link.open()
            self.wait_for_ready()
            self.active = True
        logger.info(f'Arduino connection active: {self.active}')
        print()


    def close_serial(self):
        if self.active:
            self.send_packet('B', 0, 2000)
            time.sleep(1)
            self.link.close()
            self.active = False