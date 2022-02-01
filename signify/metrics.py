
#     _____          __         .__               
#    /     \   _____/  |________|__| ____   ______
#   /  \ /  \_/ __ \   __\_  __ \  |/ ___\ /  ___/
#  /    Y    \  ___/|  |  |  | \/  \  \___ \___ \ 
#  \____|__  /\___  >__|  |__|  |__|\___  >____  >
#          \/     \/                    \/     \/ 

from __future__ import annotations

import time
import logging
import multiprocessing as mp
from queue import Empty, Full

from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

logger = logging.getLogger(__name__)


class Metrics():
    """# Metrics

    Process to send metrics to the Prometheus push gateway.
    """
    def __init__(self, name:str, config:dict, metrics_q:mp.Queue,
                    args=(), kwargs=None) -> None:
        self.main_config = config
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        self.metrics_q = metrics_q
        # Process management
        self.process = None
        self.state_q = mp.Queue(maxsize=1)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Metrics process.
        """
        logger.info(f'Updating Metrics module configuration...')
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
                logger.debug(f'Metrics module initialised.')
            else:
                logger.warning(f'Metrics module already initialised!')
        else:
            logger.warning(f'Cannot create Metrics process, module not enabled!')


    def start(self):
        """
        Creates a multi-core Metrics process and starts the routine.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    logger.info(f'Metrics process started.')
                else:
                    logger.warning(f'Cannot start Metrics process, already running!')
            else:
                logger.warning(f'Trying to start Metrics process but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start Metrics process, module is not enabled.')


    def stop(self):
        """
        Shuts down the Metrics processing thread.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'Metrics process shutting down...')
                self.state_q.put('close', timeout=2)
                self.process.join(timeout=1)
                self.process = None
                logger.info(f'Metrics process stopped and joined main thread.')
            else:
                logger.debug(f'Cannot stop Metrics process, not running.')
        else:
            logger.debug('Ignoring request to stop Metrics process, module is not enabled.')



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
            self.config = parent.config
            self.metrics_q = parent.metrics_q
            # Prometheus config
            self.previous_push_time = 0
            self.registry = CollectorRegistry()
            self.gauges = self.build_gauges(parent.main_config)


        def run(self):
            """
            Start processing Signifier metrics.
            """
            while not self.event.is_set():
                try:
                    if self.state_q.get_nowait() == 'close':
                        self.event.set()
                        break
                except Empty:
                    pass

                while True:
                    try:
                        metric = self.metrics_q.get_nowait()
                        if (gauge := self.gauges.get(metric[0])) is not None:
                            gauge.set(metric[1])
                    except Empty:
                        break

                if time.time() > self.previous_push_time\
                                + self.config['push_period']:
                    self.previous_push_time = time.time()
                    push_to_gateway(self.config['target_gateway'],
                                    self.config['job_name'],
                                    self.registry,
                                    timeout=self.config['timeout'])


        def build_gauges(self, main_config:dict) -> dict:
            gauge_details = {}
            for module in main_config.keys():
                if (sources := main_config[module].get('sources')) is not None:
                    for s in sources.keys():
                        name = f'{module}_{s}'
                        gauge_details.update({name:Gauge(
                            name, sources[s].get('description'))})
                if (destinations := main_config[module].get('destinations')) is not None:
                    for d in destinations.keys():
                        name = f'{module}_{d}'
                        gauge_details.update({name:Gauge(
                            name, destinations[d].get('description'))})
            return gauge_details