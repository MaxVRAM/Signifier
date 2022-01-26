
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
import numpy as np
from queue import Empty, Full
from multiprocessing import Process, Queue, Event
import sounddevice as sd

from signify.utils import ExpFilter as Filter

DEFAULT_CONF = {
    "input_device":"Loopback: PCM (hw:1,1)",
    "sample_rate":48000,
    "buffer":2048 }

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Analyser(Process):
    """
    Perform audio analysis on the default PulseAudio input device.\n
    Supply the audio portion of `config.json`, ie `config=config['audio']`.
    """

    Process.daemon = True

    def __init__(self, return_q:Queue, control_q:Queue, config=None):
        super().__init__()
        if config is None:
            config = DEFAULT_CONF
        self.input = config['input_device']
        self.buffer = config['buffer']
        self.sample_rate = config['sample_rate']
        self.event = Event()
        self.rms = Filter(0, alpha_decay=0.02, alpha_rise=0.02)
        self.peak = Filter(0, alpha_decay=0.02, alpha_rise=0.02)
        self.analysis_data = {}
        self.analysis_q = return_q
        self.control_q = control_q
        print(sd.query_devices())
        for api in sd.query_hostapis():
            if api['name'] == 'ALSA':
                print(sd.query_devices(api['default_input_device']))
            break

    def run(self):
        """
        Begin executing Analyser thread to produce audio descriptors.\
        These are returned to the `analysis_return_q` in the main thread.
        """
        logger.debug('Audio analysis thread now running...')
        self.event.clear()
        sd.default.channels = 1
        # sd.default.device = self.input
        sd.default.blocksize = self.buffer
        sd.default.samplerate = self.sample_rate
        print(sd.check_input_settings())
        with sd.InputStream(callback=self.process):
            while not self.event.is_set():
                try:
                    if self.control_q.get_nowait() == 'close':
                        return None
                except Empty:
                    pass
        logger.info('Audio analysis thread closed.')
        return None


    def process(self, indata, frames, time, status):
        """
        The primary function called by the Streaming thread. This function\
        calculates the amplitude of the input signal, then streams it to the\
        output audio device.
        """
        if status:
            logger.debug(status)
        peak = np.amax(np.abs(indata)) * 10
        peak = max(0.0, min(1.0, self.peak.update(peak)))
        with np.errstate(divide='ignore'):
            rms = 20 * np.log10(rms_flat(indata) / 2e-5)
            rms = rms * 0.01 if np.isfinite(rms) else 0
        rms = max(0.0, min(1.0, self.rms.update(rms)))
        try:
            data = {"peak":peak, "rms":rms}
            self.analysis_q.put_nowait(data)
        except Full:
            pass


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    # https://github.com/SiggiGue/pyfilterbank/issues/17
    return np.sqrt(np.mean(np.absolute(a)**2))
