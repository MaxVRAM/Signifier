import alsaaudio
import numpy as np
from multiprocessing import Process

device = 'hw:Loopback,1'
device = 'default'

def listen():
    loops = 1000
    while loops > 0:
        inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, 
            channels=1, rate=48000, format=alsaaudio.PCM_FORMAT_S16_LE, 
            periodsize=512, device=device)
        loops -= 1
        # Read data from device
        l, data = inp.read()
        print(l)
        buffer = np.frombuffer(data)
        if np.sum(buffer) == 0:
            pass #print('That is totally bonked.....')
        else:
            pass #print(buffer)

listener = Process(target=listen)
listener.start()