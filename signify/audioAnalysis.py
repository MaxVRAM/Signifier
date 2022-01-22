#!/usr/bin/env python3

#  __________                         __  .__                              .__     
#  \______   \_____    ______ _______/  |_|  |_________  ____  __ __  ____ |  |__  
#   |     ___/\__  \  /  ___//  ___/\   __\  |  \_  __ \/  _ \|  |  \/ ___\|  |  \ 
#   |    |     / __ \_\___ \ \___ \  |  | |   Y  \  | \(  <_> )  |  / /_/  >   Y  \
#   |____|    (____  /____  >____  > |__| |___|  /__|   \____/|____/\___  /|___|  /
#                  \/     \/     \/            \/                  /_____/      \/ 

"""Signify module to pass audio generated by the Clip Manager to the designated
audio output device. This module also produces analyise data on the incoming audio
stream, which can be sent to the arduino to modulate the LEDs."""

# Primary research sources:
# - https://stackoverflow.com/questions/66964597/python-gui-freezing-problem-of-thread-using-tkinter-and-sounddevice


from multiprocessing import Event
import time
import queue
import random
import logging
import threading
import numpy as np
import sounddevice as sd

RHISTORY = 2
DEFAULT_CONF = {
    "enabled":True,
    "loopback_return":1,
    "hw_loop_output":0,
    "sample_rate":44100,
    "buffer":4096 }

sd.default.device = (1,0)
sd.default.channels = (1,1)
sd.default.samplerate = DEFAULT_CONF['sample_rate']

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Analyser(threading.Thread):
    """A PulseAudio input stream to analyse the audio.\n
    Supply the audio portion of `config.json`, i.e. `config['audio']`."""
    def __init__(self, config=None, callback=None):
        super().__init__()
        logger.debug(f'Analysis module detected the following devices:\n{sd.query_devices()}')
        logger.debug(f'Default loopback capture device is {sd.default.device}')
        if config is None:
            config = DEFAULT_CONF
        else:
            self.active = True
            self.input = config['loopback_return']
            self.output = config['hw_loop_output']
            self.sample_rate = config['sample_rate']
            self.buffer = config['buffer']
        sd.default.channels = 1
        sd.default.device = (self.input, self.output)
        sd.default.samplerate = self.sample_rate
        self.event = None
        self.stream = None
        self.streaming = True
        self.signifier_return = callback
        # self.y_roll = np.random.rand(RHISTORY, self.buffer) / 1e16
        # self.amp = 0
        # self.amp_q = queue.Queue(maxsize=1)
        self.dBa = 0
        self.dBa_q = queue.Queue(maxsize=1)
        self.peak = 0
        self.peak_q = queue.Queue(maxsize=1)
        logger.debug('Audio passthrough module initialised.')


    def run(self):
        """Threaded routine that starts a PortAudio stream for piping Signifier\
        audio to the hardware audio output.\n
        Also executes audio analysis during the callback and updates audio\
        descriptors available from `get_descriptors()` function."""
        logger.debug('Starting loopback stream and analysis thread...')
        if self.stream is not None:
            self.stream.close()
        self.event = threading.Event()
        with sd.InputStream(
                device='pulse', channels=1, callback=self.process_audio) as self.stream:
            self.event.wait()
            try:
                sd.Stream.abort(self)
            except AttributeError:
                sd.CallbackAbort()
            print("ABORTED STREAM!")
            self.streaming = False


    def terminate(self):
        """Requests that the Stream thread aborts current buffer processing\
        and provides an `event.set()` call to terminate the thread."""
        print()
        logger.info(f'Stopping audio streaming thread...')
        self.streaming = False
        self.event.set()
        sd.sleep(10)
        self.stream.abort()


    def process_audio(self, indata, frames, time, status):
        """The primary function called by the Streaming thread. This function\
        calculates the amplitude of the input signal, then streams it to the\
        output audio device."""
        if self.streaming:
            if status:
                logger.debug(status)
            # self.y_roll[:-1] = self.y_roll[1:]
            # self.y_roll[-1, :] = np.copy(indata[0])
            # self.y_data = np.concatenate(self.y_roll, axis=0).astype(np.float32)
            # self.amp = np.max(np.abs(self.y_data))
            # try:
            #     self.amp_q.put_nowait(self.amp)
            # except queue.Full:
            #     pass
            boosted_indata = indata * 2
            self.peak = np.max(np.abs(boosted_indata))
            self.dBa = 20 * np.log10(rms_flat(boosted_indata) / 2e-5)
            try:
                self.peak_q.put_nowait(self.peak)
            except queue.Full:
                pass
            try:
                self.dBa_q.put_nowait(self.dBa)
            except queue.Full:
                pass
        else:
            self.stream.abort()


    def get_descriptors(self) -> dict:
        """Return a dictionary with audio analysis values returned from thread."""
        # try:
        #     self.amp = self.amp_q.get_nowait()
        # except queue.Empty:
        #     pass
        # try:
        #     self.peak = self.peak_q.get_nowait()
        # except queue.Empty:
        #     pass

        output = {"peak":self.peak, "dba":self.dBa}
        return output


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    From here: https://github.com/SiggiGue/pyfilterbank/issues/17
    """
    return np.sqrt(np.mean(np.absolute(a)**2))