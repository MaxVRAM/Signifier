
#  __________.__                 __                 __  .__     
#  \______   \  |  __ __   _____/  |_  ____   _____/  |_|  |__  
#   |    |  _/  | |  |  \_/ __ \   __\/  _ \ /  _ \   __\  |  \ 
#   |    |   \  |_|  |  /\  ___/|  | (  <_> |  <_> )  | |   Y  \
#   |______  /____/____/  \___  >__|  \____/ \____/|__| |___|  /
#          \/                 \/                             \/ 


from __future__ import annotations
import logging
from time import sleep, time
from datetime import datetime as dt
from multiprocessing import Process, Queue, Event
from queue import Empty, Full

from bleson import get_provider, Observer
from bleson import logger as blelogger

# Silencing the bleson module because of all the logged warnings
blelogger.set_level(blelogger.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Will need to be adjusted in real-time, socket/api/env var or something similar
SIG_THRESHOLD = 0.002


class Bluetooth(Process):
    def __init__(self, 
            return_q:Queue, control_q:Queue,
            config:dict, args=(), kwargs=None) -> None:
        super().__init__()
        self.daemon = True
        self.config = config
        self.enabled = self.config['enabled']
        self.remove_after = self.config['remove_after']
        self.active = False
        self.start_delay = self.config['start_delay']
        self.duration = self.config['scan_dur']
        self.updated_devices = []
        self.active_devices = {}
        # Thread/state management
        self.event = Event()
        self.return_q = return_q
        self.control_q = control_q
        logger.info('Bluetooth scanner thread initialised!')


    # (Callback) On each BLE device signal report
    def got_blip(self, device):
        """
        Callback for BLE device update.
        """
        mac = device.address.address
        sig = db_to_amp(device.rssi)
        if sig >= SIG_THRESHOLD:
            # Update existing device values
            if (dev := self.active_devices.get(mac)) is not None:
                dev['sig_previous'] = self.active_devices[mac]['sig_current']
                dev['sig_current'] = sig
                dev['activity'] = abs(dev['sig_current'] - dev['sig_previous'])
                dev['last_seen'] = time()
            # Add new device with initial values
            else:
                self.active_devices[mac] = {'sig_previous': 0, 'sig_current': sig, 'activty': 0, 'last_seen':time()}
        else:
            # Remove existing device with weak signal
            if mac in self.active_devices:
                self.active_devices.pop(mac)
                print(f'Removed device: {mac}')


    def run(self):
        """
        Begin executing Bluetooth scanning thread.
        """
        logger.info('Bluetooth scanner thread started!')
        adapter = get_provider().get_adapter()
        observer = Observer(adapter)
        observer.on_advertising_data = self.got_blip
        sleep(self.start_delay)
        while not self.event.is_set():
            observer.start()
            try:
                if self.control_q.get(timeout=self.duration) == 'close':
                    self.event.set()
                    break
            except Empty:
                pass
            observer.stop()

            strongest = 0
            most_active = 0

            signal_array = []
            total_signal = 0
            average_signal = 0

            activity_array = []
            total_activity = 0
            average_activity = 0

            remove_devices = []
            current_time = time()
            
            for k, v in self.active_devices.items():
                if current_time - v['last_seen'] > self.remove_after:
                    remove_devices.append(k)
                    continue
                signal_array.append(v['sig_current'])
                total_signal = sum(signal_array)
                try:
                    activity_array.append(v['activity'])
                    total_activity = sum(activity_array)
                except KeyError:
                    pass

            for d in remove_devices:
                self.active_devices.pop(d)

            try:
                average_signal = total_signal / len(signal_array)
                average_activity = total_activity / len(activity_array)
            except ZeroDivisionError:
                pass
            try:
                strongest = max(signal_array)
                most_active = max(activity_array)
            except ValueError:
                pass

            print(' ' * 40)
            print(f'total activity: {total_activity:.4f} | avg activity: {average_activity:.4f} | total signal: {total_signal:.4f} | avg siginal: {average_signal:.4f} | strongest: {strongest:.4f}')
            print(' ' * 40)

        observer.stop()
        logger.info('Bluetooth scanner thread stopped!')


# Convert dB to amplitude
def db_to_amp(db: float) -> float:
    return pow(10, float(db)/100)