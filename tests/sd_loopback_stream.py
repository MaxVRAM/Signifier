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

def callback(indata, frames, time, status):
    if status:
        print(status)
    if indata is not None:
        peak = np.max(np.abs(indata))
        try:
            q.put_nowait(peak)
        except queue.Full:
            pass


try:
    with sd.InputStream(channels=1, callback=callback):
    # with sd.Stream(device="pulse", channels=1, callback=callback):
        print('#' * 80)
        print('press Return to quit')
        print('#' * 80)
        while True:
            try:
                peak_out = q.get_nowait()
                print(peak_out)
            except queue.Empty:
                pass
            sd.sleep(20)
except Exception as e:
    print(f'{e}')