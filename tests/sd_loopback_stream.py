# Testing the sounddevice's Stream() method for created
# real-time analysis of the Signifier's audio output.
#
# Analysis data will be used for modulating the LED
# outputs via serial from the signifier.py module.
# 


import time
import queue
import random
import logging
import numpy
assert numpy
import sounddevice as sd

q = queue.Queue()


def parse_samples(indata, frames, time, status):
    if status:
        print(f'Passthrough audio device status: {status}')
    # rando = random.randint(0, 100)
    # rms = np.sqrt(np.mean(indata**2))
    # q.put(rms)
    average = numpy.average(indata)
    max = numpy.amax(indata)
    q.put(max)
    #q.put(indata[::10])


while True:
    with sd.InputStream(device="Loopback: PCM (hw:3,1)",
                   samplerate=44100, blocksize=0, dtype='float32',
                   channels=1, callback=parse_samples):
        pass
        print(f'Callback: {q.get()}')
        
        
        
        #"Loopback, Loopback PCM"
        #"bcm2835 Headphones, bcm2835 Headphones"