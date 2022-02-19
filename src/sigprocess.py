#    _________.__      __________
#   /   _____/|__| ____\______   \_______  ____   ____  ____   ______ ______
#   \_____  \ |  |/ ___\|     ___/\_  __ \/  _ \_/ ___\/ __ \ /  ___//  ___/
#   /        \|  / /_/  >    |     |  | \(  <_> )  \__\  ___/ \___ \ \___ \
#  /_______  /|__\___  /|____|     |__|   \____/ \___  >___  >____  >____  >
#          \/   /_____/                              \/    \/     \/     \/

"""
A generic class defining processes controlled by Signifier modules.
"""

from __future__ import annotations

import time
import multiprocessing as mp

from src.pusher import MetricsPusher
from src.sigmodule import SigModule
from src.utils import FunctionHandler


class ModuleProcess:
    """
    Generic Signifier Process object.
    """
    def __init__(self, parent: SigModule) -> None:
        # Module elements
        super().__init__()
        self.is_valid = True
        self.parent = parent
        self.module_name = parent.module_name
        self.values_config = parent.values_config
        self.config = parent.module_config
        self.logger = parent.logger
        # Process management
        self.parent_pipe = parent.parent_pipe
        self.prev_process_time = time.time()
        self.event = mp.Event()
        self.start_delay = self.config.get("start_delay", 0)
        self.loop_sleep = parent.main_config.get("process_loop_sleep", 0.001)
        # Mapping and metrics
        self.metrics_pusher = MetricsPusher(parent.metrics_q)
        self.mapping_pipe = parent.mapping_pipe
        self.source_values = {}
        self.destinations = {}
        self.dest_values = {}
        # Remote function calls
        self.remote_functions = {"close": self.shutdown}
        self.function_handler = FunctionHandler(
            self.module_name, self.remote_functions)


    def run(self):
        """
        Generic run function for Signifier module processes.
        Called by the multiprocessor `start()` function.
        """
        if self.pre_run():
            time.sleep(self.start_delay)
            if self.parent_pipe.writable:
                self.parent_pipe.send("started")
            while not self.event.is_set():
                self.poll_control()
                if self.event.is_set():
                    break
                self.dest_values = {}
                if self.mapping_pipe.poll():
                    self.dest_values = self.mapping_pipe.recv()
                self.mid_run()
                if self.source_values != {}:
                    if self.mapping_pipe.writable:
                        self.mapping_pipe.send(self.source_values)
                        self.metrics_pusher.update_dict(self.source_values)
                self.metrics_pusher.queue()
                time.sleep(self.loop_sleep)
        if self.parent_pipe.writable:
            self.parent_pipe.send("closed")


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
            self.function_handler.call(message)

        if block_for > 0:
            while time.time() < start_time + block_for and not self.event.is_set():
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
            self.parent_pipe.send("closing")
        self.pre_shutdown()


    def failed(self, exception=None):
        """
        Generic function to notify system Process has failed from
        a critical error and module should be deactivated.
        A supplied exception in arguments will be logged as a critical.
        """
        self.is_valid = False
        self.logger.critical(
            f"[{self.module_name}] encountered critical error: {exception}"
        )
        if self.parent_pipe.writable:
            self.parent_pipe.send("failed")
        self.shutdown()
