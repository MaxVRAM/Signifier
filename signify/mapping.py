#  ____   ____      .__                     _____                       .__                
#  \   \ /   /____  |  |  __ __   ____     /     \ _____  ______ ______ |__| ____    ____  
#   \   Y   /\__  \ |  | |  |  \_/ __ \   /  \ /  \\__  \ \____ \\____ \|  |/    \  / ___\ 
#    \     /  / __ \|  |_|  |  /\  ___/  /    Y    \/ __ \|  |_> >  |_> >  |   |  \/ /_/  >
#     \___/  (____  /____/____/  \___  > \____|__  (____  /   __/|   __/|__|___|  /\___  / 
#                 \/                 \/          \/     \/|__|   |__|           \//_____/  

from __future__ import annotations

import time
import logging
import multiprocessing as mp
from multiprocessing.connection import Connection
from queue import Empty, Full

logger = logging.getLogger(__name__)


class ValueMapper():
    """
    Multi-threaded value mapping module.
    """
    def __init__(self, config:dict, input_pipes:dict,
                output_pipes:dict, args=(), kwargs=None) -> None:
        logger.setLevel(logging.DEBUG if config.get('debug', True) else logging.INFO)
        self.config = config
        self.enabled = self.config.get('enabled', False)
        # Pipes
        self.input_pipes = input_pipes
        self.output_pipes = output_pipes
        # Process management
        self.process = None
        self.state_q = mp.Queue(maxsize=1)
        self.output_value_pool = {}
        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Mapping process.
        """
        logger.info(f'Updating Mapping module configuration...')
        if self.enabled:
            if config.get('enabled', False) is False:
                self.config = config
                self.stop()
            else:
                self.stop()
                self.process.join()
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
        Creates a new Mapping scanner process.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.Mapping(self)
                logger.debug(f'Mapping module initialised.')
            else:
                logger.warning(f'Mapping module already initialised!')
        else:
            logger.warning(f'Cannot create Mapping process, module not enabled!')


    def start(self):
        """
        Creates a multi-core Mapping process and starts the routine.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    logger.info(f'Mapping process started.')
                else:
                    logger.warning(f'Cannot start Mapping process, already running!')
            else:
                logger.warning(f'Trying to start Mapping process but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start Mapping process, module is not enabled.')


    def stop(self):
        """
        Shuts down the Mapping processing thread.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'Mapping process shutting down...')
                self.state_q.put('close', timeout=2)
                self.process.join(timeout=1)
                self.process = None
                logger.info(f'Mapping process stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop Mapping process, not running.')
        else:
            logger.debug('Ignoring request to stop Mapping process, module is not enabled.')



    class Mapping(mp.Process):
        """
        Multiprocessing Process to process and deliver Signifier modulation values.
        """
        def __init__(self, parent:ValueMapper) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.event = mp.Event()
            self.state_q = parent.state_q
            # Pipes
            self.input_pipes = parent.input_pipes
            self.output_pipes = parent.output_pipes
            # Mapping parameters
            self.mappings = parent.config.get('rules', {})
            self.output_values = {}
            self.mapping_inputs = {}
            self.mapping_outputs = {}


        def unpack_mappings(self):
            self.mapping_inputs = ()
            self.mapping_outputs = {}
            for m in self.mappings:
                module = m['input']['module']
                value = m['input']['value']
                self.mapping_inputs[m['input']]['module']


        def run(self):
            """
            Begin executing Mapping process.
            """
            while not self.event.is_set():
                try:
                    if self.state_q.get_nowait()() == 'close':
                        self.event.set()
                        break
                except Empty:
                    pass

                self.get_output_values()


        def get_output_values(self):
            for k, v in self.output_pipes.items():
                if v.poll():
                    (key, value), = v.recv().items()
                    if self.output_values.get(k) is None:
                        self.output_values[k] = {key:value}
                    self.output_values[k][key] = value

# TODO Add output compoenent to mapping system.... something like this:

        # def push_input_values(self):
        #     for k, v in self.input_pipes.items():
        #         (key, value), = v.recv().items()
        #         if self.output_values.get(k) is None:
        #             self.output_values[k] = {key:value}
        #         self.output_values[k][key] = value
