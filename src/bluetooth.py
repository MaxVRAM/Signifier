
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
from queue import Full

from bleson import get_provider, Observer
from bleson import logger as blelogger

from src.utils import lerp, db_to_amp
from src.sigmodule import SigModule, ModuleProcess

blelogger.set_level(blelogger.ERROR)
logger = logging.getLogger(__name__)


class Bluetooth(SigModule):
    """
    Bluetooth scanner manager module.
    """
    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)


    def create_process(self) -> ModuleProcess:
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        return BluetoothProcess(self)


class BluetoothProcess(ModuleProcess):
    """
    Perform audio analysis on an input device.
    """
    def __init__(self, parent:Bluetooth) -> None:
        super().__init__(parent)
        # Bluetooth configuration
        self.remove_after = self.config.get('remove_after', 15)
        self.start_delay = self.config.get('start_delay', 2)
        self.duration = self.config.get('scan_dur', 3)
        self.signal_threshold = self.config.get('signal_threshold', 0.002)
        # Scanner data
        self.devices = {}


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
            time.sleep(self.duration)
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

            try:
                self.source_in.send(self.source_values)
            except Full:
                pass
            self.metrics.update_dict(self.source_values)
            self.metrics.queue()
            time.sleep(0.001)
            self.check_control_q()

        observer.stop()
        adapter.close()
        return None


    class Device():
        """
        BLE device class for managing individual device states. 
        """
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
            """
            Called on Device object to assign values from latest scan data.
            """
            self.difference = new_signal - self.current_signal
            self.scanned_signal = new_signal
            self.current_signal = new_signal
            self.updated = True
            self.updated_at = time.time()
            pass

        def post_scan(self):
            """
            Processes the Device object's values based on current readings.
            """
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
