
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

import logging

import multiprocessing as mp

from src.utils import scale
from src.sigmodule import SigModule
from src.sigprocess import ModuleProcess

logger = logging.getLogger(__name__)


class Mapper(SigModule):
    """# ValueMapper

    Multi-threaded value mapping module for processing output values from
    modules and assigning the values to input parameters of other modules. 
    """
    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)
        self.pipes = kwargs.get('pipes', None)


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
        self.pipes = pipes    


class MapperProcess(ModuleProcess, mp.Process):
    """
    Perform audio analysis on an input device.
    """
    def __init__(self, parent: Mapper) -> None:
        super().__init__(parent)
        # Mapping
        self.source_values = {}
        self.pipes = parent.pipes
        self.rules = self.config.get('rules', {})
        if self.parent_pipe.writable:
            self.parent_pipe.send('initialised')


    def pre_run(self):
        """
        Module-specific Process run preparation.
        """
        self.prev_dest_values = dict.fromkeys(self.pipes, {})
        self.new_destinations = dict.fromkeys(self.pipes, {})
        return True


    def mid_run(self):
        """
        Module-specific Process run commands. Where the bulk of the module's
        computation occurs.
        """
        self.gather_source_values()
        self.process_mappings()
        # Send destinations through pipes and clear sent modules
        for module, destinations in self.new_destinations.items():
            if destinations is not None and destinations != {}:
                if self.pipes[module].writable:
                    self.pipes[module].send(destinations)
                    self.new_destinations[module] = {}


    def gather_source_values(self):
        for pipe in self.pipes.values():
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
