
#    _________.__          _____             .___    .__          
#   /   _____/|__| ____   /     \   ____   __| _/_ __|  |   ____  
#   \_____  \ |  |/ ___\ /  \ /  \ /  _ \ / __ |  |  \  | _/ __ \ 
#   /        \|  / /_/  >    Y    (  <_> ) /_/ |  |  /  |_\  ___/ 
#  /_______  /|__\___  /\____|__  /\____/\____ |____/|____/\___  >
#          \/   /_____/         \/            \/               \/ 

"""
A generic module class for creating independent Signifier modules.
"""

from __future__ import annotations

import time
import logging
import numpy as np
import multiprocessing as mp
from queue import Empty, Full

from src.utils import lerp
from src.metrics import MetricsPusher

logger = logging.getLogger(__name__)


class SigModule():
    """
    A generic module class for creating independent Signifier modules.
    """
    def __init__(self, name:str, config:dict, *args, **kwargs) -> None:
        self.module_name = name
        self.main_config = config
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        self.active = False
        # Process management
        self.process = None
        self.state_q = mp.Queue(maxsize=1)
        self.source_in, self.source_out = mp.Pipe()
        self.destination_in, self.destination_out = mp.Pipe()
        self.metrics_q = kwargs.get('metrics_q', None)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the module configuration from provided `config.json`.
        """
        logger.info(f'Updating Bluetooth module configuration...')
        if self.enabled:
            self.config = config[self.module_name]
            if self.config.get('enabled', False) is False:
                self.stop()
            else:
                self.stop()
                self.initialise()
                self.start()
        else:
            self.config = config[self.module_name]
            if self.config.get('enabled', False) is True:
                self.start()
            else:
                pass

    def initialise(self):
        """
        (re)Creates the given Signifier module processor.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.BluetoothProcess(self)
                logger.debug(f'Bluetooth module initialised.')
            else:
                logger.warning(f'Bluetooth module already initialised!')
        else:
            logger.warning(f'Cannot create [{self.module_name}] process, '
                           f'module not enabled!')


    def start(self):
        """
        Start the Signifier module processor's run function.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    self.active = True
                    logger.info(f'[{self.module_name}] process started.')
                else:
                    logger.warning(f'Cannot start [{self.module_name}] '
                                   f'process, already running!')
            else:
                logger.warning(f'Trying to start [{self.module_name}] process '
                               f'but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start [{self.module_name}] '
                         f'process, module is not enabled.')


    def stop(self):
        """
        Shutdown the Signifier module's processor object and deactivate module.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'[{self.module_name}] process shutting down...')
                self.state_q.put('close', timeout=2)
                self.process.join(timeout=2)
                self.process = None
                self.active = False
                logger.info(f'[{self.module_name}] processor stopped and '
                            f'joined main thread.')
            else:
                logger.debug(f'No [{self.module_name}] processor running '
                             f'to shutdown.')
        else:
            logger.debug(f'Processor object for [{self.module_name}] is '
                         f'`None`. Forcing module to deactivate.')
        self.active = False

