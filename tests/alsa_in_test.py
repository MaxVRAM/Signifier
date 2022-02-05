import alsaaudio
import numpy as np
from multiprocessing import Process

device = 'hw:Loopback,1'
device = 'default'


alsaaudio.PCM()


#def listen():
prev_empty = 0
loops = 10000
while loops > 0:
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, 
        channels=1, rate=48000, format=alsaaudio.PCM_FORMAT_S16_LE, 
        periodsize=512, device=device)


    loops -= 1

    # Read data from device
    l, data = inp.read()
    peak = None

    if l:
        buffer = np.frombuffer(data, dtype='<i2')
        # Dirty hack to only output 0 if its the second set of zeros detected.
        # Some major issue going on with period size returns in the library.
        # Hopefully this doesn't produce majorly incorrect readings...
        if np.sum(buffer) != 0:
            prev_empty = 0
            peak = np.amax(np.abs(buffer))
        elif prev_empty == 0:
            prev_empty = 1
        elif prev_empty == 1:
            prev_empty = 2
            peak = np.amax(np.abs(buffer))

    if peak is not None:
        # do queue pushy stuff
        pass


    else:
        print('oohhhhh, empty!')

# listener = Process(target=listen)
# listener.start()