
#  __________.__                 __                 __  .__     
#  \______   \  |  __ __   _____/  |_  ____   _____/  |_|  |__  
#   |    |  _/  | |  |  \_/ __ \   __\/  _ \ /  _ \   __\  |  \ 
#   |    |   \  |_|  |  /\  ___/|  | (  <_> |  <_> )  | |   Y  \
#   |______  /____/____/  \___  >__|  \____/ \____/|__| |___|  /
#          \/                 \/                             \/ 


from __future__ import annotations

import time
import logging
import numpy as np
import multiprocessing as mp
from queue import Empty, Full

from bleson import get_provider, Observer
from bleson import logger as blelogger

from signify.utils import lerp

# Silencing the bleson module because of all the logged warnings
blelogger.set_level(blelogger.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



class Bluetooth():
    """
    Bluetooth scanner manager module.
    """
    def __init__(self, config:dict, args=(), kwargs=None) -> None:
        self.config = config
        self.enabled = self.config.get('enabled', False)
        self.process = None
        # Process management
        self.return_q = mp.Queue(maxsize=10)
        self.set_state_q = mp.Queue(maxsize=1)
        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Bluetooth process.
        """
        logger.info(f'Updating Bluetooth module configuration...')
        if self.enabled:
            if config.get('enabled', False) is False:
                self.config = config
                self.stop()
            else:
                self.stop()
                self.process.join()
                self.config = config
                self.initialise()
                self.start()
        else:
            if config.get('enabled', False) is True:
                self.config = config
                self.start()
            else:
                self.config = config


    def initialise(self):
        """
        Creates a new Bluetooth scanner process.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.BluetoothProcess(self)
                logger.info(f'Bluetooth module initialised.')
            else:
                logger.warning(f'Bluetooth module already initialised!')
        else:
            logger.warning(f'Cannot create Bluetooth process, module not enabled!')


    def start(self):
        """
        Creates a multi-core Bluetooth process and starts the routine.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    logger.info(f'Bluetooth process started!')
                else:
                    logger.warning(f'Cannot start Bluetooth process, already running!')
            else:
                logger.warning(f'Trying to start Bluetooth process but module not initialised!')
        else:
            logger.info(f'Ignoring request to start Bluetooth process, module is not enabled.')


    def stop(self):
        """
        Shuts down the Bluetooth processing thread.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.info(f'Bluetooth process shutting down...')
                self.set_state_q.put('close', timeout=2)
                self.process.join(timeout=1)
                self.process = None
                logger.info(f'Bluetooth process stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop Bluetooth process, not running.')
        else:
            logger.info('Ignoring request to stop Bluetooth process, module is not enabled.')



    class BluetoothProcess(mp.Process):
        """
        Multiprocessing Process to handle threaded Bluetooth scanner.
        """
        def __init__(self, parent:Bluetooth) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.event = mp.Event()
            self.return_q = parent.return_q
            self.set_state_q = parent.set_state_q
            # Bluetooth configuration
            self.remove_after = parent.config.get('remove_after', 15)
            self.start_delay = parent.config.get('start_delay', 2)
            self.duration = parent.config.get('scan_dur', 3)
            self.signal_threshold = parent.config.get('signal_threshold', 0.002)
            # Scanner data
            self.devices = {}
            self.bluetooth_data = {}


        class Device():
            def __init__(self, parent:Bluetooth, mac, signal) -> None:
                self.parent = parent
                self.mac = mac
                self.scanned_signal = signal
                self.current_signal = signal
                self.activity = signal
                self.difference = 0
                self.updated = True
                self.updated_at = time.time()
                pass

            def update_signal(self, new_signal):
                self.difference = new_signal - self.current_signal
                self.scanned_signal = new_signal
                self.current_signal = new_signal
                self.updated = True
                self.updated_at = time.time()
                pass

            def post_scan(self):
                if self.updated:
                    self.activity = abs(self.difference)
                    self.updated = False
                else:
                    fraction = (time.time() - self.updated_at) / (
                        self.parent.remove_after - self.parent.duration)
                    self.current_signal = lerp(self.scanned_signal, 0, fraction)
                    self.difference = self.current_signal - self.scanned_signal
                    self.activity = 0
                if time.time() > self.updated_at + self.parent.remove_after\
                        or self.current_signal < 0:
                    return self


        # (Callback) On each BLE device signal report
        def got_blip(self, device):
            """
            Callback for BLE device update.
            """
            mac = device.address.address
            sig = db_to_amp(device.rssi)
            if sig >= self.signal_threshold:
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
            adapter = get_provider().get_adapter()
            observer = Observer(adapter)
            observer.on_advertising_data = self.got_blip
            time.sleep(self.start_delay)

            while not self.event.is_set():
                observer.start()
                try:
                    if self.set_state_q.get(timeout=self.duration) == 'close':
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


# Convert dB to amplitude
def db_to_amp(db: float) -> float:
    return pow(10, float(db)/100)