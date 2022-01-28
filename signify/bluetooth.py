
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
import numpy as np

from bleson import get_provider, Observer
from bleson import logger as blelogger

from signify.utils import lerp

# Silencing the bleson module because of all the logged warnings
blelogger.set_level(blelogger.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Will need to be adjusted in real-time, socket/api/env var or something similar
SIG_THRESHOLD = 0.002



"""Bluetooth dictionary structure"""

bluetooth_data = {
    'num_devices':0,
    'signal':
    {
        'total':0.0,
        'mean':0.0,
        'std':0.0,
        'max':0.0
    },
    'activity':
    {
        'total':0.0,
        'mean':0.0,
        'std':0.0,
        'max':0.0
    }
}


class Bluetooth(Process):
    def __init__(self, 
            return_q:Queue, control_q:Queue,
            config:dict, args=(), kwargs=None) -> None:
        super().__init__()
        self.daemon = True
        self.config = config
        self.active = False
        self.enabled = self.config['enabled']
        self.remove_after = self.config['remove_after']
        self.start_delay = self.config['start_delay']
        self.duration = self.config['scan_dur']
        self.devices = {}
        self.bluetooth_data = {}
        # Thread/state management
        self.event = Event()
        self.return_q = return_q
        self.control_q = control_q
        logger.info('Bluetooth scanner thread initialised!')


    class Device():
        def __init__(self, parent:Bluetooth, mac, signal) -> None:
            self.parent = parent
            self.mac = mac
            self.scanned_signal = signal
            self.current_signal = signal
            self.activity = signal
            self.difference = 0
            self.updated = True
            self.updated_at = time()
            pass

        def update_signal(self, new_signal):
            self.difference = new_signal - self.current_signal
            self.scanned_signal = new_signal
            self.current_signal = new_signal
            self.updated = True
            self.updated_at = time()
            pass

        def post_scan(self):
            if self.updated:
                self.activity = abs(self.difference)
                self.updated = False
            else:
                fraction = (time() - self.updated_at) / (
                    self.parent.remove_after - self.parent.duration)
                self.current_signal = lerp(self.scanned_signal, 0, fraction)
                self.difference = self.current_signal - self.scanned_signal
                self.activity = 0
            if time() > self.updated_at + self.parent.remove_after\
                    or self.current_signal < 0:
                return self


    # (Callback) On each BLE device signal report
    def got_blip(self, device):
        """
        Callback for BLE device update.
        """
        mac = device.address.address
        sig = db_to_amp(device.rssi)
        if sig >= SIG_THRESHOLD:
            if (dev := self.devices.get(mac)) is not None:
                dev.update_signal(sig)
                return
            self.devices[mac] = self.Device(self, mac, sig)
        else:
            # Remove existing device with weak signal
            if mac in self.devices:
                self.devices.pop(mac)
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

            inactive_list = []
            for k, v in self.devices.items():
                if v.post_scan() is not None:
                    inactive_list.append(k)
            for i in inactive_list:
                print(f'removed {self.devices.pop(i)}')

            signal_array = [d.current_signal for d in self.devices.values()]
            #print(f'Siginal array: {signal_array}')
            activity_array = [d.activity for d in self.devices.values()]
            #print(f'Activity array: {activity_array}')

            self.bluetooth_data = {
                'num_devices':len(self.devices),
                'signal':
                {
                    'total': np.sum(signal_array),
                    'mean':np.mean(signal_array),
                    'std':np.std(signal_array),
                    'max':np.amax(signal_array)
                },
                'activity':
                {
                    'total': np.sum(activity_array),
                    'mean':np.mean(activity_array),
                    'std':np.std(activity_array),
                    'max':np.amax(activity_array)
                }
            }
            print()
            print(f'Signal: {self.bluetooth_data["signal"]}')
            print(f'Activity: {self.bluetooth_data["activity"]}')
            print()
            
        observer.stop()
        logger.info('Bluetooth scanner thread stopped!')


# Convert dB to amplitude
def db_to_amp(db: float) -> float:
    return pow(10, float(db)/100)