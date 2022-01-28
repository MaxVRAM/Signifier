
#     _____                .__               .__        
#    /  _  \   ____ _____  |  | ___.__. _____|__| ______
#   /  /_\  \ /    \\__  \ |  |<   |  |/  ___/  |/  ___/
#  /    |    \   |  \/ __ \|  |_\___  |\___ \|  |\___ \ 
#  \____|__  /___|  (____  /____/ ____/____  >__/____  >
#          \/     \/     \/     \/         \/        \/ 

"""
Signifier module to process audio streams, sending values to the input pool.
"""

import time as tm
import logging
import numpy as np

from queue import Empty, Full, Queue
from threading import Thread, Event

from signify.utils import lerp

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Analyser(Thread):
    """
    Perform audio analysis on the default PulseAudio input device.\n
    Supply the audio portion of `config.json`, ie `config=config['audio']`.
    """

    def __init__(self,
            return_pipe, control_q:Queue, config:dict, args=(), kwargs=None):
        super().__init__()
        self.daemon = True
        self.input = config['default_device']
        self.sample_rate = config['sample_rate']
        self.dtype = config['dtype']
        self.buffer = config['buffer']
        self.peak = 0
        # Thread management
        self.event = Event()
        self.return_pipe = return_pipe
        self.control_q = control_q
        self.prev_time = tm.time()


    def run(self):
        """
        Begin executing Analyser thread to produce audio descriptors.\
        These are returned to the `analysis_return_q` in the main thread.
        """
        logger.debug('Audio analysis thread now running...')
        self.event.clear()
        import sounddevice as sd
        sd.default.channels = 1
        sd.default.device = self.input
        sd.default.dtype = self.dtype
        sd.default.blocksize = self.buffer
        sd.default.samplerate = self.sample_rate
        with sd.InputStream(callback=self.stream_callback):
            while not self.event.is_set():
                try:
                    if self.control_q.get_nowait() == 'close':
                        break
                except Empty:
                    pass
        logger.info('Audio analysis thread closed.')
        return None


    def stream_callback(self, indata, frames, time, status):
        """
        The primary function called by the Streaming thread. This function\
        calculates the amplitude of the input signal.
        """
        if status:
            logger.debug(status)

        peak = np.amax(np.abs(indata))
        peak = max(0.0, min(1.0, peak / 10000))
        self.peak = lerp(self.peak, peak, 0.5)
        self.return_pipe.send(self.peak)
        #print(f'Analysis ')
        self.prev_time = tm.time()


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    # https://github.com/SiggiGue/pyfilterbank/issues/17
    rms = np.sqrt(np.mean(np.absolute(a)**2))
    return rms
