
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
import logging

from pySerialTransfer import pySerialTransfer as txfer

from signify.utils import scale as scale

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
        self.is_listening = True


    def set_value(self, value, *args, duration=None):
        if 'force' in args:
            print(f'sending fadeout message to arduino: {value} / {duration}')
        if 'force' in args or self.is_listening:
            dur = duration if duration is not None else self.duration
            value = int(scale(value, (0, 1), (self.min, self.max), 'clamp'))
            self.packet = SendPacket(self.cmd, value, dur)
            self.updated = True


    def send(self, send_packet) -> bool:
        if self.packet is None:
            return False
        if self.updated and (
            current_ms := time.time_ns() // 1_000_000)\
                > self.tx_time + self.tx_period:
            if send_packet(self.packet) is not None:
                self.tx_time = current_ms
                self.updated = False
                return True
        return False


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
            
            # We can send packets once we get a `r` "ready" message.
            # The LEDs require precise timing, so inturrupting a write
            # sequence would cause issues with the LED output.
            if self.rx_packet.command == 'r':
                if self.state == ArduinoState.run:
                    self.bright.send(self.send_packet)
                elif self.state == ArduinoState.pause:
                    if self.bright.send(self.send_packet) is True:
                        self.set_state(ArduinoState.paused)
                        logger.debug(f'Arduino connection now {self.state.name}')
                elif self.state == ArduinoState.close:
                    if self.bright.send(self.send_packet) is True:
                        self.set_state(ArduinoState.closed)
                        self.link.close()
                        self.active = False
                        logger.debug(f'Arduino connection now {self.state.name}')
            self.rx_packet = None


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
            return SendPacket
        return None


    def set_state(self, state:ArduinoState):
        logger.debug(f'Arduino state set to "{state.name}"')
        self.state = state
        if self.state is ArduinoState.run:
            self.bright.is_listening = True
        else:
            self.bright.is_listening = False


    def resume(self):
        logger.debug('Arduino resuming...')
        self.set_state(ArduinoState.run)


    def pause(self, duration=500):
        logger.debug('Pausing Arduino activity...')
        self.set_state(ArduinoState.pause)
        self.bright.set_value(0, 'force', duration=duration)


    def shutdown(self, duration=1000):
        logger.debug('Shutting down Arduino connection...')
        self.set_state(ArduinoState.close)
        self.bright.set_value(0, 'force', duration=duration)


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
        if self.enabled is True:
            self.link = txfer.SerialTransfer('/dev/ttyACM0', baud=38400)
            self.callback_list = [self.receive_packet]
            self.link.set_callbacks(self.callback_list)
            logger.debug(f'({len(self.link.callbacks)}) Arduino callback(s) ready.')
            self.link.open()
            self.wait_for_ready()
            self.active = True
            self.set_state(ArduinoState.run)
        logger.info(f'Arduino connection active: {self.active}')
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