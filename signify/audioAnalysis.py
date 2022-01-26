
#     _____                .__               .__        
#    /  _  \   ____ _____  |  | ___.__. _____|__| ______
#   /  /_\  \ /    \\__  \ |  |<   |  |/  ___/  |/  ___/
#  /    |    \   |  \/ __ \|  |_\___  |\___ \|  |\___ \ 
#  \____|__  /___|  (____  /____/ ____/____  >__/____  >
#          \/     \/     \/     \/         \/        \/ 

"""
This module performs analyise on the Signifier audio stream, which can
be sent to the arduino to modulate the LEDs.
"""

# Primary research sources:
# - https://stackoverflow.com/questions/66964597/python-gui-freezing-problem-of-thread-using-tkinter-and-sounddevice

import logging
from socket import timeout
import numpy as np

from queue import Empty, Full, Queue
from threading import Thread, Event
from multiprocessing import Process
from multiprocessing import Queue as MpQueue

from signify.utils import lerp

DEFAULT_CONF = {
    "input_device":"Loopback: PCM (hw:1,1)",
    "sample_rate":48000,
    "dtype":"int16",
    "buffer":2048 }

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Analyser(Thread):
    """
    Perform audio analysis on the default PulseAudio input device.\n
    Supply the audio portion of `config.json`, ie `config=config['audio']`.
    """

    Thread.daemon = True

    def __init__(self, return_q:Queue, control_q:Queue, config=None):
        super().__init__()
        if config is None:
            config = DEFAULT_CONF
        self.input = config['input_device']
        self.sample_rate = config['sample_rate']
        self.dtype = config['dtype']
        self.buffer = config['buffer']
        self.event = Event()
        self.rms = 0
        self.peak = 0
        self.analysis_data = {}
        self.analysis_q = return_q
        self.control_q = control_q
        self.buffer_q = MpQueue(maxsize=1)



    def run(self):
        """
        Begin executing Analyser thread to produce audio descriptors.\
        These are returned to the `analysis_return_q` in the main thread.
        """
        logger.debug('Audio analysis thread now running...')
        self.event.clear()
        import sounddevice as sd
        logger.debug(f'PulseAudio audio devices:\n{sd.query_devices()}')
        sd.default.channels = 1
        #sd.default.device = self.input
        sd.default.dtype = self.dtype
        sd.default.blocksize = self.buffer
        sd.default.samplerate = self.sample_rate
        logger.debug(f'Analysis | device:{sd.default.device},\
                    channels:{sd.default.channels},\
                    bit-depth:{sd.default.dtype},\
                    sample-rate:{sd.default.samplerate},\
                    buffer size:{sd.default.blocksize}.')
        with sd.InputStream(callback=self.stream_callback):
            while not self.event.is_set():
                try:
                    if self.control_q.get_nowait() == 'close':
                        return None
                except Empty:
                    pass
        logger.info('Audio analysis thread closed.')
        return None


    def stream_callback(self, indata, frames, time, status):
        """
        The primary function called by the Streaming thread. This function\
        calculates the amplitude of the input signal, then streams it to the\
        output audio device.
        """
        if status:
            logger.debug(status)
        process_buffer = Process(target=analysis,
                            args=(indata, self.peak, self.rms, self.buffer_q))
        print(f'{process_buffer.name} waiting for data:')
        process_buffer.start()
        process_buffer.join()
        try:
            processed_values = self.buffer_q.get(timeout=0.01)
            print(processed_values)
            self.peak = processed_values[0]
            self.rms = processed_values[1]
        except Empty:
            print('Should not be empty, but the analysis queue is empty....')



def analysis(indata, in_peak, in_rms, thread_q):
    """Processes incomming audio buffer data and updates analysis values."""
    peak = np.amax(np.abs(indata)) * 10
    peak = max(0.0, min(1.0, peak))
    lerp_peak = lerp(in_peak, peak, 0.5)

    with np.errstate(divide='ignore'):
        rms = 20 * np.log10(rms_flat(indata) / 2e-5)
        rms = rms * 0.01 if np.isfinite(rms) else 0
    rms = max(0.0, min(1.0, rms))
    lerp_rms = lerp(in_rms, rms, 0.5)

    data = (lerp_peak, lerp_rms)
    print(f'InPeak: {in_peak} | Peak: {peak} | LerpPeak: {lerp_peak}      InRMS: {in_rms} | RMS: {rms} | LerpRMS:{lerp_rms}')

    try:
        thread_q.put(data, timeout=0.01)
    except Full:
        pass


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    # https://github.com/SiggiGue/pyfilterbank/issues/17
    return np.sqrt(np.mean(np.absolute(a)**2))
