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

from src.utils import scale
from src.utils import SmoothedValue
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
        self.pipes = kwargs.get("pipes")
        self.period = kwargs.get("period", 10) / 1000


    def create_process(self):
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        self.process =  MapperProcess(self)


class MapperProcess(ModuleProcess, mp.Process):
    """
    Perform audio analysis on an input device.
    """

    def __init__(self, parent: Mapper) -> None:
        super().__init__(parent)
        # Mapping
        self.sources = {}
        self.pipes = parent.pipes
        self.rules = parent.rules_config.get("mapper")
        self.period = parent.period
        self.last_output_time = 0
        if self.parent_pipe.writable:
            self.parent_pipe.send("initialised")

    def pre_run(self):
        """
        Module-specific Process run preparation.
        """
        self.prev_dest_values = dict.fromkeys(self.pipes, {})
        self.new_destinations = dict.fromkeys(self.pipes, {})
        self.last_output_time = time.time()
        return True

    def mid_run(self):
        """
        Module-specific Process run commands. Where the bulk of the module's
        computation occurs.
        """
        self.gather_source_values()
        self.process_mappings()
        # Send destinations through pipes and clear sent modules if successful
        for module, destinations in self.new_destinations.items():
            if destinations is not None and destinations != {}:
                if self.pipes[module].writable:
                    self.pipes[module].send(destinations)
                    self.new_destinations[module] = {}

    def gather_source_values(self):
        """
        Gathers source value updates from each value pipe.
        """
        for pipe in self.pipes.values():
            if pipe.poll():
                new_sources = pipe.recv()
                for k, v in new_sources.items():
                    self.sources[k] = v

    def process_mappings(self):
        """
        Iterates over mapping rules, processing source values and sends the
        result to via destination pipes to the target module.
        """
        if time.time() > self.last_output_time + self.period:
            self.last_output_time = time.time()
            for r in self.rules:
                rule_source = r["source"]
                rule_dest = r["destination"]
                if (source_value := self.sources.get(rule_source["name"])) is not None:
                    source_value = scale(
                        source_value,
                        rule_source.get("range", [0, 1]),
                        rule_dest.get("range", [0, 1]),
                    )
                    prev_value = self.prev_dest_values[rule_dest["module"]].get(
                        rule_dest["name"]
                    )
                    if prev_value is not None and prev_value == source_value:
                        continue
                    if (
                        prev_value is not None
                        and (smoothing := rule_dest.get("smoothing")) is not None
                    ):
                        output_value = SmoothedValue(
                            init=prev_value, amount=tuple(smoothing)
                        ).update(source_value)
                    else:
                        output_value = source_value
                    rule_output = {"value": output_value}
                    if (duration := rule_dest.get("duration")) is not None:
                        rule_output.update({"duration": duration})
                    self.prev_dest_values[rule_dest["module"]].update(
                        {rule_dest["name"]: output_value}
                    )
                    self.new_destinations[rule_dest["module"]].update(
                        {rule_dest["name"]: rule_output}
                    )
