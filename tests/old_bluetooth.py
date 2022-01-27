from time import sleep
from datetime import datetime as dt
from bleson import get_provider, Observer
from bleson import logger as blelogger

# Silencing the bleson module because of all the logged warnings
blelogger.set_level(blelogger.ERROR)

# Prep some persistents
scan = {}
device_count_previous = 0
sig_total_previous = 0

active_devices = {}
updated_devices = []
total_activity = 0

# Will need to be adjusted in real-time, socket/api/env var or something similar
SIG_THRESHOLD = 0.001


class scan_result():
    device_count = 0
    sig_total = 0
    activity_avg = 0

# Convert dB to amplitude
def db_to_amp(db: float) -> float:
    return pow(10, float(db)/100)

# (Callback) On each BLE device signal report
def got_blip(device):
    global active_devices, total_activity
    
    mac = device.address.address
    sig = db_to_amp(device.rssi)

    if sig >= SIG_THRESHOLD:
        # Prevents multiple updates of the same device per scan
        if mac not in updated_devices:
            updated_devices.append(mac)
            # Update existing device values
            if mac in active_devices:
                dev = active_devices[mac]
                dev['sig_previous'] = active_devices[mac]['sig_current']
                dev['sig_current'] = sig
                dev['activity'] = abs(dev['sig_current'] - dev['sig_previous'])
                total_activity += dev['activity']
                print(f'Updated device: {mac} - with activity {dev["activity"]:.6f} and current signal {dev["sig_current"]:.6f}')
            # Add new device with initial values
            else:
                active_devices[mac] = {'sig_previous': 0, 'sig_current': sig, 'activty': 0}
                print(f'Added device: {mac}')
    else:
        # Remove existing device with weak signal
        if mac in active_devices:
            active_devices.pop(mac)
            print(f'Removed device: {mac}')

# Scan job
def timed_ble_scan(duration = 2):
    # Reset globals for difference 
    global updated_devices, total_activity
    total_activity = 0
    updated_devices = []
    # Scan service
    observer.start()
    sleep(duration)
    observer.stop()

# Assign the Bluetooth device and assign an observer with callback function
adapter = get_provider().get_adapter()
observer = Observer(adapter)
observer.on_advertising_data = got_blip

while True:
    timed_ble_scan(3)
    print('-----------------------------------------------------------------------')
    print(f'Total active devices: {len(active_devices)}   with total activity {total_activity:.6f}')
    print('-----------------------------------------------------------------------')
    print()
    sleep(1)