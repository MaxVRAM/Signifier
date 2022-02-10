
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

from src.utils import scale
from src.sigmodule import SigModule, ModuleProcess

logger = logging.getLogger(__name__)


class Mapper(SigModule):
    """# ValueMapper

    Multi-threaded value mapping module for processing output values from
    modules and assigning the values to input parameters of other modules. 
    """
    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)
        pipes = kwargs.get('pipes', {})
        self.source_pipes = pipes.get('sources', None)
        self.dest_pipes = pipes.get('destinations', None)


    def create_process(self) -> ModuleProcess:
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        return MapperProcess(self)


    def set_pipes(self, pipes:dict):
        """
        Update Mapper's return and destination pipes after initialisation.
        """
        self.source_pipes = pipes['sources']
        self.dest_pipes = pipes['destinations']        


class MapperProcess(ModuleProcess):
    """
    Perform audio analysis on an input device.
    """
    def __init__(self, parent:Mapper) -> None:
        super().__init__(parent)
        # Mapping parameters
        self.rules = self.config.get('rules', {})
        # Values
        self.source_values = {}
        self.prev_dest_values = dict.fromkeys(self.parent.dest_pipes, {})
        self.new_destinations = dict.fromkeys(self.parent.dest_pipes, {})


    def run(self):
        """
        Start processing output values and mapping configurations.
        """
        while not self.event.is_set():
            self.gather_source_values()
            self.process_mappings()
            # Send destinations through pipes and clear sent modules
            for module, destinations in self.new_destinations.items():
                if destinations is not None and destinations != {}:
                    self.parent.dest_pipes[module].send(destinations)
                    self.new_destinations[module] = {}
            time.sleep(0.001)
            self.check_control_q()


    def gather_source_values(self):
        for module, pipe in self.parent.source_pipes.items():
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
