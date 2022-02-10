
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

import logging
from queue import Full
import multiprocessing as mp


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
        self.source_in, self.source_out = mp.Pipe()
        self.destination_in, self.destination_out = mp.Pipe()
        self.state_q = mp.Queue(maxsize=1)
        self.return_q = kwargs.get('return_q', None)
        self.metrics_q = kwargs.get('metrics_q', None)
        self.source_pipes = kwargs.get('source_pipes', None)
        self.destination_pipes = kwargs.get('destination_pipes', None)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the module configuration from provided `config.json`.
        """
        logger.info(f'Updating [{self.module_name}] module config...')
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
        (re)Creates the given Signifier module's process.
        """
        def module(self) -> any:
            """
            Module-specific function call.
            """
            pass

        if self.enabled:
            if self.process is None:
                self.process = module()
                if self.process is None:
                    logger.error(f'[{self.module_name}] module could not '
                                 f'created!')
                    return None
                logger.debug(f'[{self.module_name}] module initialised.')
            else:
                logger.warning(f'[{self.module_name}] module '
                               f'already initialised!')
        else:
            logger.warning(f'Cannot create [{self.module_name}] '
                           f'process, module not enabled!')


    def start(self):
        """
        Start the Signifier module's process run function.
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
                logger.warning(f'Trying to start [{self.module_name}] '
                               f'process but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start [{self.module_name}] '
                         f'process, module is not enabled.')


    def stop(self):
        """
        Shutdown the Signifier module's process object and deactivate module.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'[{self.module_name}] process shutting down...')
                try:
                    self.state_q.put('close', timeout=2)
                except Full:
                    pass
                self.process.join(timeout=2)
                self.state_q.cancel_join_thread()
                self.active = False
                logger.info(f'[{self.module_name}] process stopped and '
                            f'joined main thread.')
            else:
                logger.debug(f'No [{self.module_name}] process running '
                             f'to shutdown.')
        else:
            logger.debug(f'Process object for [{self.module_name}] is '
                         f'`None`. Forcing module to deactivate.')
        self.active = False


    def tick(self):
        """
        Tick call to process module-specific actions.
        """
        def module(self) -> any:
            """
            Module-specific function call.
            """
            pass

        module()
