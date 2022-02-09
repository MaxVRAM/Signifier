
#     _____                       .__                
#    /     \ _____  ______ ______ |__| ____    ____  
#   /  \ /  \\__  \ \____ \\____ \|  |/    \  / ___\ 
#  /    Y    \/ __ \|  |_> >  |_> >  |   |  \/ /_/  >
#  \____|__  (____  /   __/|   __/|__|___|  /\___  / 
#          \/     \/|__|   |__|           \//_____/  

"""
Processes module source values and sends them to module destination parameters.
"""

from __future__ import annotations

import time
import logging
import multiprocessing as mp
from queue import Empty, Full

from src.utils import scale

logger = logging.getLogger(__name__)


class Mapping():
    """# ValueMapper

    Multi-threaded value mapping module for processing output values from
    modules and assigning the values to input parameters of other modules. 
    """
    def __init__(self, name:str, config:dict, destination_pipes:dict,
                source_pipes:dict, metrics_q:mp.Queue, args=(), kwargs=None) -> None:
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        self.active = False
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
        Creates a new Mapping process.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.ValueMapper(self)
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
                    self.active = True
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
                self.process.join(timeout=2)
                self.process = None
                logger.info(f'Mapping process stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop Mapping process, not running.')
        else:
            logger.debug('Ignoring request to stop Mapping process, module is not enabled.')
        self.active = False



    class ValueMapper(mp.Process):
        """
        Multiprocessing Process to compute and deliver Signifier modulation values.
        """
        def __init__(self, parent:Mapping) -> None:
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
            # Values
            self.source_values = {}
            self.prev_dest_values = dict.fromkeys(self.destination_pipes, {})
            self.new_destinations = dict.fromkeys(self.destination_pipes, {})


        def run(self):
            """
            Start processing output values and mapping configurations.
            """
            while not self.event.is_set():
                try:
                    if self.state_q.get_nowait() == 'close':
                        self.event.set()
                        break
                except Empty:
                    pass

                self.gather_source_values()
                self.process_mappings()
                # Send destinations through pipes and clear sent modules
                for module, destinations in self.new_destinations.items():
                    if destinations is not None and destinations != {}:
                        self.destination_pipes[module].send(destinations)
                        self.new_destinations[module] = {}
                time.sleep(0.001)


        def gather_source_values(self):
            for module, pipe in self.source_value_pipes.items():
                if pipe.poll():
                    sources = pipe.recv()
                    for k,v in sources.items():
                        self.source_values[k] = v


        def process_mappings(self):
            for r in self.rules:
                map_source = r['source']
                map_dest = r['destination']
                if (out_value := self.source_values.get(
                        map_source['name'])) is not None:
                    # Apply input/output scaling and attach duration (if supplied)
                    out_value = {'value':scale(out_value,
                                    map_source.get('range', [0, 1]),
                                    map_dest.get('range', [0, 1]))}
                    if (duration := map_dest.get('duration')) is not None:
                        out_value['duration'] = duration
                    # Update previous value dictionary and add to new destinations 
                    if (curr_value := self.prev_dest_values[map_dest['module']].get(
                            map_dest['name'])) is None or\
                            out_value['value'] != curr_value['value']:
                        self.prev_dest_values[map_dest['module']]\
                            [map_dest['name']] = out_value
                        self.new_destinations[map_dest['module']]\
                            [map_dest['name']] = out_value
