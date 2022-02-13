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


class SigModule:
    """
    A generic module class for creating independent Signifier modules.
    """

    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        # Signifier configuration
        self.module_name = name
        self.main_config = config
        self.module_config = config[self.module_name]
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(
            logging.DEBUG if self.module_config.get("debug", True) else logging.INFO
        )
        self.enabled = self.module_config.get("enabled", False)
        self.active = False
        # Process management
        self.process = None
        self.metrics_q = kwargs.get("metrics", None)
        self.parent_pipe, self.child_pipe = mp.Pipe()
        self.mapping_pipe, self.module_pipe = mp.Pipe()

    def create_process(self) -> any:
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
                    self.logger.error(
                        f"[{self.module_name}] process object " f"could not be created!"
                    )
                    self.enabled = False
                    return None
                self.logger.debug(f"[{self.module_name}] module initialised.")
            else:
                self.logger.warning(
                    f"[{self.module_name}] process " f"already initialised!"
                )

    def update_config(self, config: dict):
        """
        Updates the module's configuration based on supplied config dictionary.
        """
        self.logger.info(f"Updating [{self.module_name}] module config...")
        self.main_config = config
        if self.enabled:
            self.module_config = config[self.module_name]
            if self.module_config.get("enabled", False) is False:
                self.stop()
            else:
                self.stop()
                self.initialise()
                self.start()
        else:
            self.module_config = config[self.module_name]
            if self.module_config.get("enabled", False) is True:
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
                    self.logger.info(f"[{self.module_name}] process started.")
                else:
                    self.logger.warning(
                        f"[{self.module_name}] process "
                        f"already running. Cannot run again."
                    )
            else:
                self.logger.warning(
                    f"[{self.module_name}] cannot be run "
                    f"before process is initialised!"
                )

    def stop(self):
        """
        Shutdown the module's Process object and deactivate module.
        """
        if self.process is not None:
            if self.process.is_alive():
                self.logger.debug(f"[{self.module_name}] shutting down...")
                if self.child_pipe.writable:
                    self.child_pipe.send("close")
                else:
                    self.logger.warning(
                        f"[{self.module_name}] control pipe "
                        f'cannot send "close" command to process!'
                    )
                self.request_join()
            else:
                self.logger.debug(
                    f"[{self.module_name}] has no process running " f"to shutdown."
                )
        self.active = False

    def request_join(self):
        if self.process is not None:
            if (timeout := self.module_config.get("fade_out")) is not None:
                timeout /= 300
            else:
                timeout = 2
            self.process.join(timeout=timeout)
            self.logger.info(
                f"[{self.module_name}] process stopped " f"and joined main thread."
            )

    def monitor(self):
        """
        Generic monitoring tick call for module to check process statues.
        """
        if self.child_pipe.poll():
            message = self.child_pipe.recv()
            self.logger.debug(
                f"[{self.module_name}] module received "
                f'"{message}" from child process.'
            )
            if message == "started":
                self.active = True
                try:
                    self.metrics_q.put((f"{self.module_name}_active", 1), timeout=0.01)
                except Full:
                    pass
            if message in ["closed", "failed"]:
                self.request_join()
                self.active = False
                try:
                    self.metrics_q.put((f"{self.module_name}_active", 0), timeout=0.01)
                except (Full, AttributeError):
                    pass

        if self.enabled and self.active == False:
            self.initialise()
