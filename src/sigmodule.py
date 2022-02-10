
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
from queue import Full, Empty
import multiprocessing as mp

from src.metrics import MetricsPusher


class SigModule():
    """
    A generic module class for creating independent Signifier modules.
    """
    def __init__(self, name:str, config:dict, *args, **kwargs) -> None:
        # Signifier configuration
        self.module_name = name
        self.main_config = config
        self.module_config = config[self.module_name]
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.module_config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.module_config.get('enabled', False)
        self.active = False
        # Process management
        self.process = None
        self.source_in, self.source_out = mp.Pipe()
        self.dest_in, self.dest_out = mp.Pipe()
        self.control_q = mp.Queue(maxsize=1)
        queues = kwargs.get('queues', {})
        self.return_q = queues.get('return', None)
        self.metrics_q = queues.get('metrics', None)


    def create_process(self) -> ModuleProcess:
        """
        Module-specific Process class return for initialisation function.
        """
        pass


    def initialise(self):
        """
        (re)Creates the given Signifier module's Process.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.create_process()
                if self.process is None:
                    self.logger.error(f'[{self.module_name}] Process could '
                                 f'not be created!')
                    return None
                self.logger.debug(f'[{self.module_name}] module initialised.')
            else:
                self.logger.warning(f'[{self.module_name}] Process '
                               f'already initialised!')
        else:
            self.logger.debug(f'Cannot create [{self.module_name}] '
                                f'Process, module not enabled.')


    def update_config(self, config:dict):
        """
        Updates the module's configuration based on supplied config dictionary.
        """
        self.logger.info(f'Updating [{self.module_name}] module config...')
        if self.enabled:
            self.module_config = config[self.module_name]
            if self.module_config.get('enabled', False) is False:
                self.stop()
            else:
                self.stop()
                self.initialise()
                self.start()
        else:
            self.module_config = config[self.module_name]
            if self.module_config.get('enabled', False) is True:
                self.start()
            else:
                pass


    def start(self):
        """
        Start the module's Process run function.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    self.active = True
                    self.logger.info(f'[{self.module_name}] Process started.')
                else:
                    self.logger.warning(f'Cannot start [{self.module_name}] '
                                   f'Process, already running!')
            else:
                self.logger.warning(f'Trying to start [{self.module_name}] '
                               f'Process but module not initialised!')
        else:
            self.logger.debug(f'Ignoring request to start [{self.module_name}] '
                         f'Process, module is not enabled.')


    def stop(self):
        """
        Shutdown the module's Process object and deactivate module.
        """
        if self.process is not None:
            if self.process.is_alive():
                self.logger.debug(f'[{self.module_name}] Process shutting down...')
                try:
                    self.control_q.put('close', timeout=2)
                except Full:
                    pass
                self.process.join(timeout=5)
                self.control_q.cancel_join_thread()
                self.active = False
                self.logger.info(f'[{self.module_name}] Process stopped and '
                            f'joined main thread.')
            else:
                self.logger.debug(f'No [{self.module_name}] Process running '
                             f'to shutdown.')
        else:
            self.logger.debug(f'Process object for [{self.module_name}] is '
                         f'`None`. Forcing module to deactivate.')
        self.active = False


    def tick(self):
        """
        Tick call for module-specific actions.
        """
        pass


class ModuleProcess(mp.Process):
    """
    Generic Signifier Process object.
    """
    def __init__(self, parent:SigModule) -> None:
        # Module elements
        super().__init__()
        self.is_valid = True
        self.parent = parent
        self.module_name = parent.module_name
        self.config = parent.module_config
        self.logger = parent.logger
        # Process management
        self.event = mp.Event()
        self.return_q = parent.return_q
        self.control_q = parent.control_q
        self.control_functions = {'close':self.shutdown}
        self.prev_process_time = time.time()
        # Mapping and metrics
        self.metrics = MetricsPusher(parent.metrics_q)
        self.source_in = parent.source_in
        self.source_values = {}
        self.dest_out = parent.dest_out
        self.destinations = {}


    def pre_shutdown(self):
        """
        Module-specific Process shutdown preparation.
        """
        pass


    def shutdown(self, *args):
        """
        Generic shutdown function to prepare Process for joining main thread.
        """
        self.return_q.put('closing', timeout=1)
        self.pre_shutdown()
        self.event.set()


    def check_control_q(self):
        """
        Generic Process call to manage incoming control messages.
        """
        command = None
        args = None

        # Avoid process getting stuck in case the queue won't empty
        timeout = time.time() + 1

        try:
            while (message := self.control_q.get_nowait()) is not None\
                    and not self.event.is_set and time.time() < timeout:
                if isinstance(message, str):
                    command = message
                else:
                    try:
                        command = message[0]
                        args = message[1:]
                    except TypeError:
                        self.logger.warning(f'Malformed command {command} sent '
                                            f'[{self.module_name}] process.')
                        return None
                if (func := self.control_functions.get(message)) is not None:
                    func(*args)
                else:
                    self.logger.warning(f'Command {command} not recognised by '
                                        f'[{self.module_name}] process.')
        except Empty:
            pass

        return None
