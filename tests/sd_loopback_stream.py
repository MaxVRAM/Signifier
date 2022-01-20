# Testing the sounddevice's Stream() method for created
# real-time analysis of the Signifier's audio output.
#
# Analysis data will be used for modulating the LED
# outputs via serial from the signifier.py module.
# 

# https://python-sounddevice.readthedocs.io/en/0.3.15/examples.html#input-to-output-pass-through

import os
import time
import queue
import random
import logging
import numpy as np
assert np
import sounddevice as sd


RHISTORY = 2
done = False
q = queue.Queue()
buffer = 2048
y_roll = np.random.rand(RHISTORY, buffer) / 1e16


q.maxsize = 1

def callback(indata, outdata, frames, time, status):
    if status:
        print(status)
    if indata is not None:
        y_roll[:-1] = y_roll[1:]
        y_roll[-1, :] = np.copy(indata[0])
        y_data = np.concatenate(y_roll, axis=0).astype(np.float32)
        amp = np.max(np.abs(y_data))
        q.put(amp)
    outdata[:] = indata


try:
    with sd.Stream(device=("Loopback: PCM (hw:1,1)", "bcm2835 Headphones: - (hw:0,0)"),
                   channels=1, callback=callback):
        print('#' * 80)
        print('press Return to quit')
        print('#' * 80)
        while True:
#            print(f'{q.qsize()}')
            print(f'Callback size: {q.qsize()}      Callback value: {q.get()}')
except Exception as e:
    print(f'{e}')