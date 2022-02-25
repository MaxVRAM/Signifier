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

import alsaaudio
import numpy as np
import multiprocessing as mp

from src.sigmodule import SigModule
from src.sigprocess import ModuleProcess

logger = logging.getLogger(__name__)

THRESHOLD = 2e-08


class Analysis(SigModule):
    """
    Audio analysis manager module.
    """

    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)

    def create_process(self):
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        self.process = AnalysisProcess(self)


class AnalysisProcess(ModuleProcess, mp.Process):
    """
    Perform audio analysis on an input device.
    """

    def __init__(self, parent: Analysis) -> None:
        super().__init__(parent)
        # Analysis configuration
        self.input_audio = None
        self.input_device = parent.module_config.get("input_device", "default")
        self.sample_rate = parent.module_config.get("sample_rate", 48000)
        self.dtype = parent.module_config.get("dtype", "int16")
        self.buffer_size = parent.module_config.get("buffer", 1024)
        self.output_volume = parent.main_config["composition"].get("volume", 1)
        self.gain = parent.module_config.get("gain", 2)
        # Mapping and metrics
        self.source_values = {f"{self.module_name}_peak": 0}
        if self.parent_pipe.writable:
            self.parent_pipe.send("initialised")

    def pre_shutdown(self):
        """
        Module-specific Process shutdown preparation.
        """
        self.input_audio.close()

    def pre_run(self) -> bool:
        """
        Module-specific Process run preparation.
        """
        self.prev_empty = 0
        self.input_audio = alsaaudio.PCM(
            type=alsaaudio.PCM_CAPTURE,
            mode=alsaaudio.PCM_NORMAL,
            rate=self.sample_rate,
            channels=1,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=self.buffer_size,
            device=self.input_device,
        )
        return True

    def mid_run(self):
        """
        Module-specific Process run commands. Where the bulk of the module's
        computation occurs.
        """
        length = 0
        while not length:
            try:
                length, data = self.input_audio.read()
            except alsaaudio.ALSAAudioError as exception:
                self.failed(exception)
                return None

            buffer = np.frombuffer(data, dtype="<i2")
            # Dirty hack to only output 0 if its the second set of zeros detected.
            # Some major issue going on with period size returns in the library.
            # Hopefully this doesn't produce majorly incorrect readings...
            # After the first set of 0 returns, will allow another 9 empty buffers
            # before preventing outputs. Remains until non zero buffer is filled
            # and restarts the counter.
            # if np.sum(buffer) != 0:
            #     self.prev_empty = 0
            # elif self.prev_empty == 0:
            #     self.prev_empty += 1
            #     buffer = None
            # elif self.prev_empty < 10:
            #     self.prev_empty += 1
            # else:
            #     buffer = None

            if buffer is not None and len(buffer) != 0:
                peak = np.amax(np.abs(buffer))
                peak = max(0.0, min(1.0, (1 / self.output_volume) * (peak / 16400) * self.gain ))
                if peak != self.source_values[f"{self.module_name}_peak"]:
                    self.source_values[f"{self.module_name}_peak"] = peak
                    self.metrics_pusher.update(f"{self.module_name}_peak", peak)
                self.metrics_pusher.update(f"{self.module_name}_buffer_size", length)
                self.metrics_pusher.update(
                    f"{self.module_name}_buffer_ms",
                    int((time.time() - self.prev_process_time) * 1000),
                )
                self.prev_process_time = time.time()
                buffer = None
