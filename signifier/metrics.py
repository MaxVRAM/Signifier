
#     _____          __         .__               
#    /     \   _____/  |________|__| ____   ______
#   /  \ /  \_/ __ \   __\_  __ \  |/ ___\ /  ___/
#  /    Y    \  ___/|  |  |  | \/  \  \___ \___ \ 
#  \____|__  /\___  >__|  |__|  |__|\___  >____  >
#          \/     \/                    \/     \/ 

"""
Gathers Signifier metrics and exports to Prometheus push gateway.
"""

from __future__ import annotations

import time
import logging
import multiprocessing as mp
from queue import Empty, Full
from urllib.error import URLError

from prometheus_client import CollectorRegistry, Gauge, Info, push_to_gateway

logger = logging.getLogger(__name__)


class Metrics():
    """# Metrics

    Process to send metrics to the Prometheus push gateway.
    """
    push_period = 1

    def __init__(self, name:str, config:dict, metrics_q:mp.Queue,
                    args=(), kwargs=None) -> None:
        self.main_config = config
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        self.metrics_q = metrics_q
        Metrics.push_period = self.config['push_period']
        # Process management
        self.process = None
        self.state_q = mp.Queue(maxsize=1)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Metrics process.
        """
        logger.info(f'Updating [{self.module_name}] module configuration...')
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
        Creates a new Metrics process.
        """
        if self.enabled:
            if self.process is None:
                self.process = self.MetricsProcess(self)
                logger.debug(f'[{self.module_name}] module initialised.')
            else:
                logger.warning(f'[{self.module_name}] module already initialised!')
        else:
            logger.warning(f'Cannot create [{self.module_name}] process, module not enabled!')


    def start(self):
        """
        Creates a multi-core Metrics process and starts the routine.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    logger.info(f'[{self.module_name}] process started.')
                else:
                    logger.warning(f'Cannot start [{self.module_name}] process, already running!')
            else:
                logger.warning(f'Trying to start [{self.module_name}] process but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start [{self.module_name}] process, module is not enabled.')


    def stop(self):
        """
        Shuts down the Metrics processing thread.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'[{self.module_name}] process shutting down...')
                self.state_q.put('close', timeout=2)
                self.process.join(timeout=1)
                self.process = None
                logger.info(f'[{self.module_name}] process stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop [{self.module_name}] process, not running.')
        else:
            logger.debug('Ignoring request to stop [{self.module_name}] process, module is not enabled.')



    class MetricsProcess(mp.Process):
        """
        Multiprocessing Process to compute and deliver Signifier metrics to the push gateway.
        """
        def __init__(self, parent:Metrics) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.event = mp.Event()
            self.state_q = parent.state_q
            self.main_config = parent.main_config
            self.config = parent.config
            self.metrics_q = parent.metrics_q
            # Prometheus config
            self.registry = CollectorRegistry()
            self.push_period = self.config['push_period']
            self.gauges = {}
            
            self.build_gauges()


        def run(self):
            """
            Start processing Signifier metrics.
            """
            prev_push = 0
            while not self.event.is_set():
                try:
                    if self.state_q.get_nowait() == 'close':
                        self.event.set()
                        return None
                except Empty:
                    pass

                # Drain queue for max 1 second, ensuring we don't get stuck
                loop_time = time.time()
                while time.time() < loop_time + 1:
                    try:
                        metric = self.metrics_q.get_nowait()
                        if (gauge := self.gauges.get(metric[0])) is not None:
                            gauge.set(metric[1])
                    except Empty:
                        break

                # Push current registry values if enough time has lapsed
                if time.time() > prev_push + self.push_period:
                    try:
                        push_to_gateway(self.config['target_gateway'],
                                        self.config['job_name'],
                                        self.registry,
                                        timeout=self.config['timeout'])
                        self.push_period = self.config['push_period']
                    except (ConnectionResetError, ConnectionRefusedError, URLError):
                        logger.warning(f'Target Prometheus gateway [{self.config["target_gateway"]}] cannot be reached.')
                        self.increase_push_time()
                    prev_push = time.time()
                    continue


        def build_gauges(self):
            for module in self.main_config.keys():
                try:
                    for k, v in self.main_config[module]['sources'].items():
                        if v.get('enabled', True) and v.get('type', '') == 'gauge':
                            name = f'{module}_{k}'
                            self.gauges[f'{name}'] = Gauge(f'sig_{name}',
                                v['description'], registry=self.registry)
                except KeyError:
                    pass
                try:
                    for k, v in self.main_config[module]['destinations'].items():
                        if v.get('enabled', True) and v.get('type', '') == 'gauge':
                            name = f'{module}_{k}'
                            self.gauges[f'{name}'] = Gauge(f'sig_{name}',
                                v['description'], registry=self.registry)
                except KeyError:
                    pass


        def increase_push_time(self):
            self.push_period += 2
            if self.push_period > 30:
                self.push_period = 30



class MetricsPusher():
    """
    Object for managing class-wide metrics updates to Prometheus push gateway.
    """
    def __init__(self, module_name, metrics_q) -> None:
        """
        MetricsPusher is initialised with the name of the containing module and a
        metrics queue pointing to the metrics module for collating updated metrics. 
        """
        self.module_name = module_name
        self.metrics_q = metrics_q
        self.new_values = {}


    def update_dict(self, dict):
        """
        Updates the class dictionary of metric values.
        Existing values for the metric name within the given module will be
        overwritten until the metric queue has been absorbed and pushed to
        the push gateway. This ensures the latest metrics are sent to the
        database, and prevents excess data from being passed between threads.
        """
        for d in dict.keys():
            self.new_values[dict[d]] = dict[d]



    def update(self, name, value):
        """
        Existing values for the metric name within the given module will be
        overwritten until the metric queue has been absorbed and pushed to
        the push gateway. This ensures the latest metrics are sent to the
        database, and prevents excess data from being passed between threads.

        """
        self.new_values[name] = value

    def queue(self):
        """
        Position the latest dictionary of data in the metrics push gateway queue.
        Each dictionary item will be unpacked and associated with its parent module.
        The entire dictionary will be zeroed once pushed to prevent excess data from
        being transferred between threads.
        """
        if self.metrics_q is not None:
            if self.new_values is not None or self.new_values != {}:
                for k, v in self.new_values.items():
                    try:
                        self.metrics_q.put_nowait((f'{self.module_name}_{k}', v))
                        self.new_values = {}
                    except Full:
                        pass