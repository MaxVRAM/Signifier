
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

from signifier.utils import lerp
from signifier.metrics import MetricsPusher

logger = logging.getLogger(__name__)


class Analysis():
    """
    Audio analysis manager module.
    """
    def __init__(self, name:str, config:dict, *args, **kwargs) -> None:
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        # Process management
        self.process = None
        self.state_q = Queue(maxsize=1)
        self.source_in, self.source_out = mp.Pipe()
        self.metrics_q = kwargs.get('metrics_q', None)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Analysis thread.
        """
        logger.info(f'Updating Analysis module configuration...')
        self.config = config[self.module_name]
        if self.enabled:
            if self.config.get('enabled', False) is False:
                self.stop()
            else:
                self.stop()
                self.initialise()
                self.start()
        else:
            if self.config.get('enabled', False) is True:
                self.start()
            else:
                pass


    def initialise(self):
        """
        Creates a new Analysis thread.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.AnalysisThread(self)
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
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
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
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'Analysis thread shutting down...')
                self.state_q.put('close', timeout=2)
                self.process.join(timeout=1)
                self.process = None
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
            self.source_in = parent.source_in
            self.state_q = parent.state_q
            # Analysis configuration
            self.input_device = parent.config.get('input_device', 'default')
            self.sample_rate = parent.config.get('sample_rate', 48000)
            self.dtype = parent.config.get('dtype', 'int16')
            self.buffer = parent.config.get('buffer', 2048)
            self.latency = parent.config.get('latency', 0.4)
            # Analysis data
            self.prev_process_time = time.time()
            self.sources = {'peak':0}
            # Metrics
            self.metrics = MetricsPusher(parent.module_name, parent.metrics_q)


        def run(self):
            """
            Begin executing Analyser thread to produce audio descriptors.
            """
            self.event.clear()
            import sounddevice as sd
            sd.default.channels = 1
            sd.default.device = self.input_device
            sd.default.dtype = self.dtype
            sd.default.blocksize = self.buffer
            sd.default.samplerate = self.sample_rate
            sd.default.latency = self.latency

            with sd.InputStream(callback=self.stream_callback):
                while not self.event.is_set():
                    try:
                        if self.state_q.get_nowait() == 'close':
                            self.event.set()
                            return None
                    except Empty:
                        pass
                    try:
                        self.source_in.send(self.sources)
                    except Full:
                        pass

                    self.metrics.queue()
            return None


        def stream_callback(self, indata, _frames, _time, status):
            """
            The primary function called by the Streaming thread. This function\
            calculates the amplitude of the input signal.
            """
            if status:
                logger.warning(status)

            peak = np.amax(np.abs(indata))
            peak = max(0.0, min(1.0, peak / 10000))
            peak = lerp(self.sources['peak'], peak, 0.5)
            self.sources['peak'] = peak
            self.metrics.update('peak', peak)
            self.prev_process_time = time.time()


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    # https://github.com/SiggiGue/pyfilterbank/issues/17
    rms = np.sqrt(np.mean(np.absolute(a)**2))
    return rms
