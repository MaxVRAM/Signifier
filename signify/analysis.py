
#     _____                .__               .__        
#    /  _  \   ____ _____  |  | ___.__. _____|__| ______
#   /  /_\  \ /    \\__  \ |  |<   |  |/  ___/  |/  ___/
#  /    |    \   |  \/ __ \|  |_\___  |\___ \|  |\___ \ 
#  \____|__  /___|  (____  /____/ ____/____  >__/____  >
#          \/     \/     \/     \/         \/        \/ 

"""
Signifier module to process audio streams, sending values to the input pool.
"""

from __future__ import annotations

import time
import logging
import numpy as np

from queue import Empty, Full, Queue
from threading import Thread, Event
import multiprocessing as mp

from signify.utils import lerp

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



class Analysis():
    """
    Audio analysis manager module.
    """
    def __init__(self, config:dict, args=(), kwargs=None) -> None:
        self.config = config
        self.enabled = self.config.get('enabled', False)
        self.thread = None
        # Process management
        self.return_q = Queue(maxsize=1)
        self.set_state_q = Queue(maxsize=1)
        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Analysis thread.
        """
        logger.info(f'Updating Analysis module configuration...')
        if self.enabled:
            if config.get('enabled', False) is False:
                self.config = config
                self.stop()
            else:
                self.stop()
                self.thread.join()
                self.config = config
                self.initialise()
                self.start()
        else:
            if config.get('enabled', False) is True:
                self.config = config
                self.start()
            else:
                self.config = config


    def initialise(self):
        """
        Creates a new Analysis thread.
        """
        if self.enabled:
            if self.thread is None:
                self.thread = self.AnalysisThread(self)
                logger.debug(f'Analysis module initialised.')
            else:
                logger.warning(f'Analysis module already initialised!')
        else:
            logger.warning(f'Cannot create Analysis process, module not enabled!')


    def start(self):
        """
        Creates a Analysis thread and starts the routine.
        """
        if self.enabled:
            if self.thread is not None:
                if not self.thread.is_alive():
                    self.thread.start()
                    logger.info(f'Analysis thread started.')
                else:
                    logger.warning(f'Cannot start Analysis thread, already running!')
            else:
                logger.warning(f'Trying to start Analysis thread but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start Analysis thread, module is not enabled.')


    def stop(self):
        """
        Shuts down the Analysis thread.
        """
        if self.thread is not None:
            if self.thread.is_alive():
                logger.debug(f'Analysis thread shutting down...')
                self.set_state_q.put('close', timeout=2)
                self.thread.join(timeout=1)
                self.thread = None
                logger.info(f'Analysis thread stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop Analysis process, not running.')
        else:
            logger.debug('Ignoring request to stop Analysis process, module is not enabled.')



    class AnalysisThread(Thread):
        """
        Perform audio analysis on the input device provided in `config.json`.
        """
        def __init__(self, parent:Analysis) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.event = Event()
            self.return_q = parent.return_q
            self.set_state_q = parent.set_state_q
            # Analysis configuration
            self.input = parent.config.get('input_device', 'default')
            self.sample_rate = parent.config.get('sample_rate', 48000)
            self.dtype = parent.config.get('dtype', 'int16')
            self.buffer = parent.config.get('buffer', 2048)
            # Analysis data
            self.data = {'peak': 0}
            self.prev_process_time = time.time()
            value_config = parent.config.get('values', {})
            peak_config = value_config.get('peak', {})
            self.peak_enabled = peak_config.get('enabled', False)
            self.peak_smooth = peak_config.get('smooth', 0.5)


        def run(self):
            """
            Begin executing Analyser thread to produce audio descriptors.\
            These are returned to the `analysis_return_q` in the main thread.
            """
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
                        if self.set_state_q.get_nowait() == 'close':
                            break
                    except Empty:
                        pass
                    try:
                        self.return_q.get_nowait()
                    except Empty:
                        pass
                    try:
                        self.return_q.put_nowait(self.data)
                    except Full:
                        pass
            return None


        def stream_callback(self, indata, _frames, _time, status):
            """
            The primary function called by the Streaming thread. This function\
            calculates the amplitude of the input signal.
            """
            if status:
                logger.debug(status)

            if self.peak_enabled:
                peak = np.amax(np.abs(indata))
                peak = max(0.0, min(1.0, peak / 10000))
                self.data['peak'] = lerp(self.data['peak'], peak, 0.5)

            self.prev_process_time = time.time()


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    # https://github.com/SiggiGue/pyfilterbank/issues/17
    rms = np.sqrt(np.mean(np.absolute(a)**2))
    return rms
