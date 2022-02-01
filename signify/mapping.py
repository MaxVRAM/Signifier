
#  ____   ____      .__                     _____                       .__                
#  \   \ /   /____  |  |  __ __   ____     /     \ _____  ______ ______ |__| ____    ____  
#   \   Y   /\__  \ |  | |  |  \_/ __ \   /  \ /  \\__  \ \____ \\____ \|  |/    \  / ___\ 
#    \     /  / __ \|  |_|  |  /\  ___/  /    Y    \/ __ \|  |_> >  |_> >  |   |  \/ /_/  >
#     \___/  (____  /____/____/  \___  > \____|__  (____  /   __/|   __/|__|___|  /\___  / 
#                 \/                 \/          \/     \/|__|   |__|           \//_____/  

"""
Signifier module to process module outputs and send them to module inputs.
"""

from __future__ import annotations

import logging
import multiprocessing as mp
from queue import Empty, Full

from signify.utils import scale

logger = logging.getLogger(__name__)


class ValueMapper():
    """# ValueMapper

    Multi-threaded value mapping module for processing output values from
    modules and assigning the values to input parameters of other modules. 
    """
    def __init__(self, name:str, config:dict, destination_pipes:dict,
                source_pipes:dict, args=(), kwargs=None) -> None:
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        # Pipes
        self.destination_pipes = destination_pipes
        self.source_pipes = source_pipes
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
        Multiprocessing Process to compute and deliver Signifier modulation values.
        """
        def __init__(self, parent:ValueMapper) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.event = mp.Event()
            self.state_q = parent.state_q
            # Pipes
            self.destination_pipes = parent.destination_pipes
            self.source_value_pipes = parent.source_pipes
            # Mapping parameters
            self.rules = parent.config.get('rules', {})
            
            self.source_values = {}
            for m in self.source_value_pipes.keys():
                self.source_values[m] = {}

            self.destination_values = {}
            for m in self.destination_pipes.keys():
                self.destination_values[m] = {}


        def run(self):
            """
            Start processing output values and mapping configurations.
            """
            counter = 0
            while not self.event.is_set():
                try:
                    if self.state_q.get_nowait() == 'close':
                        self.event.set()
                        break
                except Empty:
                    pass
                counter += 1
                self.process_source_values()
                self.process_destinations()

                # if counter % 1000 == 0:
                #     print(self.source_values)


        def process_source_values(self):
            for module, data in self.source_value_pipes.items():
                if data.poll():
                    sources = data.recv()
                    keys = list(sources.keys())
                    values = list(sources.values())
                    if self.source_values.get(module) is None:
                        self.source_values[module] = {}
                    for r in range(len(keys)):
                        self.source_values[module].update({keys[r]:values[r]})


        def process_destinations(self):
            for r in self.rules:
                # try:
                dest = r['destination']
                source = r['source']
                if (source_values := self.source_values.get(source['module'])) is not None:
                    if (value := source_values.get(source['param'])) is not None:
                        value = {'value':scale(value, source['range'], dest['range'])}
                        if (duration := dest.get('duration')) is not None:
                            value.update({'duration':duration})
                        if (curr_value := self.destination_values.get(dest['param']))\
                            is None or value['value'] != curr_value['value']:
                                command = {dest['param']:value}
                                self.destination_values[dest['param']] = value
                                self.destination_pipes[dest['module']].send(command)

