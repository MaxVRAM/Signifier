import alsaaudio
from multiprocessing import Process

device = 'hw:Loopback,1'

def listen():
    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, 
        channels=1, rate=48000, format=alsaaudio.PCM_FORMAT_S16_LE, 
        periodsize=160, device=device)

    loops = 10000
    while loops > 0:
        loops -= 1
        # Read data from device
        l, data = inp.read()
        if l > 0:
            print(data)

listener = Process(target=listen)
listener.start()