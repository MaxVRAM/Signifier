
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
from queue import Full

import alsaaudio

from src.utils import lerp
from src.sigmodule import SigModule, ModuleProcess

logger = logging.getLogger(__name__)


class Analysis(SigModule):
    """
    Audio analysis manager module.
    """
    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)


    def create_process(self) -> ModuleProcess:
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        return AnalysisProcess(self)


class AnalysisProcess(ModuleProcess):
    """
    Perform audio analysis on an input device.
    """
    def __init__(self, parent:Analysis) -> None:
        super().__init__(parent)
        # Analysis configuration
        self.input_device = parent.module_config\
            .get('input_device', 'default')
        self.sample_rate = parent.module_config\
            .get('sample_rate', 48000)
        self.dtype = parent.module_config\
            .get('dtype', 'int16')
        self.buffer_size = parent.module_config\
            .get('buffer', 1024)
        self.output_volume = parent.main_config['composition']\
            .get('volume', 1)
        # Mapping and metrics
        self.source_values = {f'{self.module_name}_peak':0}

    def run(self):
        """
        Begin executing Analyser thread to produce audio descriptors.
        """
        prev_empty = 0

        while not self.event.is_set():
            try:
                inputAudio = alsaaudio.PCM(
                    alsaaudio.PCM_CAPTURE,
                    alsaaudio.PCM_NORMAL, 
                    channels=1,
                    rate=self.sample_rate,
                    format=alsaaudio.PCM_FORMAT_S16_LE, 
                    periodsize=self.buffer_size,
                    device=self.input_device)
                length, buffer = inputAudio.read()
            except alsaaudio.ALSAAudioError as exception:
                logger.critical(f'ALSA Audio error: {exception}')
                self.return_q.put(['failed', self.module_name], timeout=0.1)
                self.event.set()
                return None

            if length:
                buffer = np.frombuffer(buffer, dtype='<i2')
                # Dirty hack to only output 0 if its the second set of zeros detected.
                # Some major issue going on with period size returns in the library.
                # Hopefully this doesn't produce majorly incorrect readings...
                # After the first set of 0 returns, will allow another 9 empty buffers
                # before preventing outputs. Remains until non zero buffer is filled
                # and restarts the counter.
                if np.sum(buffer) != 0:
                    prev_empty = 0
                elif prev_empty == 0:
                    prev_empty += 1
                    buffer = None
                elif prev_empty < 10:
                    prev_empty += 1
                else:
                    buffer = None

                if buffer is not None:
                    peak = np.amax(np.abs(buffer))
                    peak = max(0.0, min(1.0, (1 / self.output_volume) * (peak / 16400)))
                    peak = lerp(
                        self.source_values[f'{self.module_name}_peak'], peak, 0.5)

                    self.source_values[f'{self.module_name}_peak'] = peak
                    self.metrics.update(f'{self.module_name}_peak', peak)
                    self.metrics.update(f'{self.module_name}_buffer_size', length)
                    self.metrics.update(f'{self.module_name}_buffer_ms',
                        int((time.time()-self.prev_process_time) * 1000))
                    self.prev_process_time = time.time()
                    length = None
                    buffer = None
                    try:
                        self.source_in.send(self.source_values)
                    except Full:
                        pass

                self.metrics.queue()
                self.check_control_q()

        return None


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    # https://github.com/SiggiGue/pyfilterbank/issues/17
    rms = np.sqrt(np.mean(np.absolute(a)**2))
    return rms
