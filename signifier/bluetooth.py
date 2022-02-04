
#  __________.__                 __                 __  .__     
#  \______   \  |  __ __   _____/  |_  ____   _____/  |_|  |__  
#   |    |  _/  | |  |  \_/ __ \   __\/  _ \ /  _ \   __\  |  \ 
#   |    |   \  |_|  |  /\  ___/|  | (  <_> |  <_> )  | |   Y  \
#   |______  /____/____/  \___  >__|  \____/ \____/|__| |___|  /
#          \/                 \/                             \/ 

"""
Signifier module to manage Bluetooth scanner system.
"""

from __future__ import annotations

import time
import logging
import numpy as np
import multiprocessing as mp
from queue import Empty, Full

from bleson import get_provider, Observer
from bleson import logger as blelogger

from signifier.utils import lerp
from signifier.metrics import MetricsPusher

blelogger.set_level(blelogger.ERROR)
logger = logging.getLogger(__name__)


class Bluetooth():
    """
    Bluetooth scanner manager module.
    """
    def __init__(self, name:str, config:dict, *args, **kwargs) -> None:
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        # Process management
        self.process = None
        self.state_q = mp.Queue(maxsize=1)
        self.source_in, self.source_out = mp.Pipe()
        self.destination_in, self.destination_out = mp.Pipe()
        self.metrics_q = kwargs.get('metrics_q', None)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Bluetooth process.
        """
        logger.info(f'Updating Bluetooth module configuration...')
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
        Creates a new Bluetooth scanner process.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.BluetoothProcess(self)
                logger.debug(f'Bluetooth module initialised.')
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
                    logger.info(f'Bluetooth process started.')
                else:
                    logger.warning(f'Cannot start Bluetooth process, already running!')
            else:
                logger.warning(f'Trying to start Bluetooth process but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start Bluetooth process, module is not enabled.')


    def stop(self):
        """
        Shuts down the Bluetooth processing thread.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'Bluetooth process shutting down...')
                self.state_q.put('close', timeout=2)
                self.process.join(timeout=1)
                self.process = None
                logger.info(f'Bluetooth process stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop Bluetooth process, not running.')
        else:
            logger.debug('Ignoring request to stop Bluetooth process, module is not enabled.')



    class BluetoothProcess(mp.Process):
        """
        Multiprocessing Process to handle threaded Bluetooth scanner.
        """
        def __init__(self, parent:Bluetooth) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.event = mp.Event()
            self.set_state_q = parent.state_q
            self.module_name = parent.module_name
            # Bluetooth configuration
            self.remove_after = parent.config.get('remove_after', 15)
            self.start_delay = parent.config.get('start_delay', 2)
            self.duration = parent.config.get('scan_dur', 3)
            self.signal_threshold = parent.config.get('signal_threshold', 0.002)
            # Scanner data
            self.devices = {}
            # Mapping and metrics
            self.metrics = MetricsPusher(parent.metrics_q)
            self.source_in = parent.source_in
            self.source_values = {}


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
                    self.devices.pop(i)

                signal_array = [d.current_signal for d in self.devices.values()]
                activity_array = [d.activity for d in self.devices.values()]

                self.source_values = {
                    f'{self.module_name}_num_devices':len(self.devices),
                    f'{self.module_name}_signal_total': np.sum(signal_array),
                    f'{self.module_name}_signal_mean':np.mean(signal_array),
                    f'{self.module_name}_signal_std':np.std(signal_array),
                    f'{self.module_name}_signal_max':np.amax(signal_array),
                    f'{self.module_name}_activity_total': np.sum(activity_array),
                    f'{self.module_name}_activity_mean':np.mean(activity_array),
                    f'{self.module_name}_activity_std':np.std(activity_array),
                    f'{self.module_name}_activity_max':np.amax(activity_array)
                }

                self.source_in.send(self.source_values)
                self.metrics.update_dict(self.source_values)
                self.metrics.queue()

            observer.stop()


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


# Convert dB to amplitude
def db_to_amp(db: float) -> float:
    return pow(10, float(db)/100)
