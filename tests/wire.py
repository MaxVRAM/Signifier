#!/usr/bin/env python3
"""Pass input directly to output.

https://app.assembla.com/spaces/portaudio/git/source/master/test/patest_wire.c

"""
import sounddevice as sd
import numpy as np  # Make sure NumPy is loaded before it is used in the callback

import queue

q = queue.Queue()

samples_per_frame = int(44100 / 20)
RHISTORY = 2
y_roll = np.random.rand(RHISTORY, samples_per_frame) / 1e16

def callback(indata, outdata, frames, time, status):
    if status:
        print(status)
    outdata[:] = indata
    if indata is not None:
        y_roll[:-1] = y_roll[1:]
        y_roll[-1, :] = np.copy(indata[0])
        y_data = np.concatenate(y_roll, axis=0).astype(np.float32)
        vol = np.max(np.abs(y_data))
        q.put(vol)

try:
    with sd.Stream(device=('Loopback: PCM (hw:3,1)', "bcm2835 Headphones: - (hw:0,0)"),
                   channels=1, callback=callback):
        print('#' * 80)
        print('press Return to quit')
        print('#' * 80)
        while True:
            print(q.get())
        input()
except Exception as e:
    pass