
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
from queue import Full
import multiprocessing as mp

from src.pusher import MetricsPusher


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
        self.metrics_q = kwargs.get('metrics', None)
        self.parent_pipe, self.child_pipe = mp.Pipe()
        self.mapping_pipe, self.module_pipe = mp.Pipe()


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
                    self.logger.error(f'[{self.module_name}] process could '
                                      f'not be created!')
                    self.enabled = False
                    return None
                self.logger.debug(f'[{self.module_name}] module initialised.')
            else:
                self.logger.warning(f'[{self.module_name}] process '
                                    f'already initialised!')


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
                    self.logger.info(f'[{self.module_name}] process started.')
                else:
                    self.logger.warning(f'[{self.module_name}] process '
                                        f'already running. Cannot run again.')
            else:
                self.logger.warning(f'[{self.module_name}] cannot be run '
                                    f'before process is initialised!')


    def stop(self):
        """
        Shutdown the module's Process object and deactivate module.
        """
        if self.process is not None:
            if self.process.is_alive():
                self.logger.debug(f'[{self.module_name}] shutting down...')
                if self.child_pipe.writable:
                    self.child_pipe.send('close')
                else:
                    self.logger.warning(f'[{self.module_name}] control pipe '
                                        f'cannot send "close" command to process!')
                self.request_join()
            else:
                self.logger.debug(f'[{self.module_name}] has no process running '
                                  f'to shutdown.')
        self.active = False


    def request_join(self):
        if self.process is not None:
            if (timeout := self.module_config.get('fade_out')) is not None:
                timeout /= 300
            else:
                timeout = 2
            self.process.join(timeout=timeout)
            self.logger.info(f'[{self.module_name}] process stopped '
                            f'and joined main thread.')



    def monitor(self):
        """
        Generic monitoring tick call for module to check process statues.
        """
        if self.child_pipe.poll():
            message = self.child_pipe.recv()
            self.logger.debug(f'[{self.module_name}] module received '
                              f'"{message}" from child process.')
            if message == 'started':
                self.active = True
                try:
                    self.metrics_q.put(
                        {f'{self.module_name}_active', 1}, timeout=0.01)
                except Full:
                    pass
            if message in ['closed', 'failed']:
                self.request_join()
                self.active = False
                try:
                    self.metrics_q.put(
                        {f'{self.module_name}_active', 0}, timeout=0.01)
                except (Full, AttributeError):
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
        self.prev_process_time = time.time()
        self.parent_pipe = parent.parent_pipe
        self.control_functions = {'close':self.shutdown}
        self.start_delay = self.config.get('start_delay', 0)
        self.loop_sleep = parent.main_config.get('process_loop_sleep', 0.001)
        # Mapping and metrics
        self.metrics_pusher = MetricsPusher(parent.metrics_q)
        self.mapping_pipe = parent.mapping_pipe
        self.source_values = {}
        self.destinations = {}
        self.dest_values = {}


    def run(self):
        """
        Generic run function for Signifier module processes.
        Called by the multiprocessor `start()` function.
        """
        if self.pre_run():
            time.sleep(self.start_delay)
            if self.parent_pipe.writable:
                self.parent_pipe.send('running')
            while not self.event.is_set():
                self.poll_control()
                if self.event.is_set():
                    break
                prev_values = self.source_values
                self.dest_values = {}
                if self.mapping_pipe.poll():
                    self.dest_values = self.mapping_pipe.recv()
                    self.metrics_pusher.update_dict(self.dest_values)
                self.mid_run()
                if self.source_values != prev_values and self.mapping_pipe.writable:
                    self.mapping_pipe.send(self.source_values)
                    self.metrics_pusher.update_dict(self.source_values)
                    self.metrics_pusher.queue()
                time.sleep(self.loop_sleep)
        if self.parent_pipe.writable:
            self.parent_pipe.send('closed')


    def pre_run(self) -> bool:
        """
        Module-specific Process run preparation to ensure module is ready.
        """
        True


    def mid_run(self):
        """
        Module-specific Process run commands. Where the bulk of the module's
        computation occurs.
        """
        pass


    def poll_control(self, block_for=0):
        """
        Generic Process call to manage incoming control messages.
        Provide `block_for=(float)` to force checking for a period of seconds.
        Useful in scenarios like BLE scanning, where using `time.sleep()` to
        create the scanning period would hold up the Signifier shutdown process. 
        """
        command = None
        args = []
        start_time = time.time()

        while self.parent_pipe.poll():
            message = self.parent_pipe.recv()
            if isinstance(message, str):
                command = message
            else:
                try:
                    command = message[0]
                    args = list(message[1:])
                except TypeError:
                    self.logger.warning(f'[{self.module_name}] received '
                                        f'Malformed command: {message}')
                    return None
            if (func := self.control_functions.get(message)) is not None:
                self.logger.debug(f'[{self.module_name}] received command '
                                    f'"{command}", executing...')
                func(*args)
            else:
                self.logger.warning(f'[{self.module_name}] does not recognise '
                                    f'{command} command.')

        if block_for > 0:
            while time.time() < start_time + block_for\
                    and not self.event.is_set():        
                time.sleep(0.01)
                self.poll_control()
        return None


    def pre_shutdown(self):
        """
        Module-specific Process shutdown preparation.
        """
        pass


    def shutdown(self, *args):
        """
        Generic shutdown function to prepare Process for joining main thread.
        """
        self.event.set()
        if self.parent_pipe.writable:
            self.parent_pipe.send('closing')
        self.pre_shutdown()


    def failed(self, exception=None):
        """
        Generic function to notify system Process has failed from
        a critical error and module should be deactivated.
        A supplied exception in arguments will be logged as a critical.
        """
        self.is_valid = False
        self.event.set()
        self.logger.critical(f'[{self.module_name}] encountered critical '
                             f'error: {exception}')
        if self.parent_pipe.writable:
            self.parent_pipe.send('failed')
