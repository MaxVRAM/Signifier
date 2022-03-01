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
from enum import Enum
from queue import Full
import multiprocessing as mp

from src.utils import FunctionHandler
from signifier import module_types


class ProcessStatus(Enum):
    disabled = 1
    empty = 2
    initialised = 3
    starting = 4
    running = 5
    closing = 6
    closed = 7
    failed = 8


class SigModule:
    """
    A generic module class for creating independent Signifier modules.
    """
    def __init__(self, name: str, configs: dict, *args, **kwargs) -> None:
        # Signifier configuration
        self.module_name = name
        self.logger = logging.getLogger(__name__)
        self.apply_new_configs(configs)
        self.status = ProcessStatus.empty if self.enabled else ProcessStatus.disabled
        # Process management
        self.module_type = None
        self.process = None
        self.metrics_q = kwargs.get("metrics", None)
        self.parent_pipe, self.child_pipe = mp.Pipe()
        self.mapping_pipe, self.module_pipe = mp.Pipe()
        self.module_start_time = time.time()
        self.module_end_time = time.time()
        # Remote function calls
        self.remote_functions = {
            "initialise": self.initialise,
            "update_config": self.update_config,
            "start": self.start,
            "stop": self.stop,
            "monitor": self.monitor,
            "process": self.send_to_process
            }
        self.function_handler = FunctionHandler(
            self.module_name, self.remote_functions)


    def apply_new_configs(self, configs):
        """
        Generic method to apply new configs to module instance.
        """
        self.main_config = configs['config']['modules']
        self.module_config = self.main_config[self.module_name]
        self.main_values = configs['values']['modules']
        self.module_values = self.main_values.get(self.module_name, {})
        self.rules_config = configs['rules']['modules']
        self.module_type = module_types[self.module_config['module_type']]
        self.enabled = self.module_config.get("enabled", False)
        self.logger.setLevel(
            logging.DEBUG if self.module_config.get("debug", True) else logging.INFO
        )


    def create_process(self):
        """
        Generic method to instantiate module-specific Process class.
        """
        pass


    def initialise(self, *args):
        """
        (re)Creates the given Signifier module's Process.
        """
        if (self.status in [ProcessStatus.empty,
                            ProcessStatus.failed,
                            ProcessStatus.closed]
                            or 'force' in args):
            self.process(self.module_type(self))
            if self.process is None:
                self.logger.error(
                    f"[{self.module_name}] process object could not be created!"
                )
                return None
        else:
            self.logger.warning(
                f'[{self.module_name}] cannot be initialised with status: '
                f'{self.status.name}')


    def update_config(self, configs: dict, **kwargs):
        """
        Updates the module's configuration based on supplied config dictionary.
        """
        self.logger.debug(f"Updating [{self.module_name}] module config...")
        if self.status == ProcessStatus.running:
            self.stop()
        self.apply_new_configs(configs)


    def start(self):
        """
        Start the module's Process run function.
        """
        if self.status == ProcessStatus.initialised:
            if self.process is not None:
                if not self.process.is_alive():
                    self.logger.debug(f"[{self.module_name}] process starting.")
                    self.status = ProcessStatus.starting
                    self.module_start_time = time.time()
                    self.process.start()
                else:
                    self.logger.warning(
                        f"[{self.module_name}] already running but status not up to date."
                    )
        else:
            self.logger.warning(
                f"[{self.module_name}] cannot be started with status: {self.status.name}")


    def stop(self):
        """
        Shutdown the module's Process object and deactivate module.
        """
        if self.status not in [ProcessStatus.empty,
                               ProcessStatus.closed,
                               ProcessStatus.failed,
                               ProcessStatus.closing]:
            self.status = ProcessStatus.closing
            self.send_to_process('close')


    def request_join(self):
        if self.process is not None:
            if (timeout := self.module_config.get("fade_out")) is not None:
                timeout /= 300
            else:
                timeout = 2
            try:
                self.process.join(timeout=timeout)
                self.logger.debug(
                    f"[{self.module_name}] process stopped and joined main thread."
                )
            except RuntimeError as exception:
                self.logger.warning(f'[{self.module_name}] {exception}')


    def monitor(self):
        """
        Generic monitoring tick call for module to check process statues.
        """
        previous_status = self.status
        # Retrieve and parse any pending messages from the child process
        if self.child_pipe.poll():
            message = self.child_pipe.recv()
            self.logger.debug(
                f"[{self.module_name}] module received "
                f'"{message}" from child process.'
            )
            if message == "running":
                self.status = ProcessStatus.running
                try:
                    self.metrics_q.put((f"{self.module_name}_active", 1), timeout=0.01)
                except Full:
                    pass
            if message == 'initialised':
                self.status = ProcessStatus.initialised
            elif message in ['initialised', 'closing', 'closed', 'failed']:
                self.status = ProcessStatus[message]
                if self.status not in [ProcessStatus.initialised, ProcessStatus.closing]:
                    self.module_end_time = time.time()
                    self.request_join()
                    try:
                        self.metrics_q.put((f"{self.module_name}_active", 0), timeout=0.01)
                    except (Full, AttributeError):
                        pass

        # Adjust module status' if necessary
        if self.enabled:
            if self.status in [ProcessStatus.running, ProcessStatus.starting, ProcessStatus.closing]:
                pass
            elif self.status == ProcessStatus.disabled:
                self.status = ProcessStatus.empty
            elif self.status == ProcessStatus.initialised:
                self.start()
            else:
                if time.time() > self.module_end_time + self.main_config.get(
                        'module_fail_restart_secs', 5):
                    self.module_end_time = time.time()
                    self.initialise('force')
        else:
            if self.status == ProcessStatus.disabled:
                pass
            elif self.status == ProcessStatus.running:
                self.stop()
            elif self.status not in [ProcessStatus.starting, ProcessStatus.closing]:
                self.status = ProcessStatus.disabled

        if previous_status != self.status:
            self.logger.info(f'[{self.module_name}] status changed to "{self.status.name}"')



    def module_call(self, *args):
        """
        Handles requests from remote locations to call internal module
        functions. Function names are supplied as strings, and call
        module functions with or without additional arguments.\n
        Basic module functions are `initialise`, 'start', 'stop' and
        'monitor'.\nThe special function name `process` passes the
        function call on to its child process via the module's control
        pipe. The available functions in this case are module-specific.
        """
        self.function_handler.call(args)


    def send_to_process(self, *args):
        """
        Pass a function call request on to the module's child process via
        the module's control pipe. By default, all process objects accept
        the `close` for shutting down the process gracefully. Additional
        function calls depend on the module.
        """
        if self.process is not None:
            if self.process.is_alive():
                self.logger.debug(f'[{self.module_name}] sending '
                                  f'{args} to process...')
                if self.child_pipe.writable:
                    self.child_pipe.send(args)
                else:
                    self.logger.warning(
                        f'[{self.module_name}] control pipe is not writable!'
                    )
                return True
            else:
                self.logger.debug(
                    f"[{self.module_name}] has no process running to send message to."
                )
        return False
