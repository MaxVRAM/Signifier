
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

from prometheus_client import CollectorRegistry, Gauge, Info, push_to_gateway, start_http_server

logger = logging.getLogger(__name__)


class Metrics():
    """# Metrics

    Process to send metrics to the Prometheus push gateway.
    """
    def __init__(self, name:str, config:dict, metrics_q:mp.Queue,
                    args=(), kwargs=None) -> None:
        self.main_config = config
        self.hostname = config['general']['hostname']
        self.module_name = name
        self.config = config[self.module_name]
        logger.setLevel(logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO)
        self.enabled = self.config.get('enabled', False)
        self.active = False
        self.metrics_q = metrics_q
        self.push_period = self.config['push_period']
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
                logger.warning(f'[{self.module_name}] module already '
                               f'initialised!')
        else:
            logger.warning(f'Cannot create [{self.module_name}] process, '
                           f'module not enabled!')


    def start(self):
        """
        Creates a multi-core Metrics process and starts the routine.
        """
        if self.enabled:
            if self.process is not None:
                if not self.process.is_alive():
                    self.process.start()
                    self.active = True
                    logger.info(f'[{self.module_name}] process started.')
                else:
                    logger.warning(f'Cannot start [{self.module_name}] '
                        f'process, already running!')
            else:
                logger.warning(f'Trying to start [{self.module_name}] '
                                f'process but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start [{self.module_name}] '
                        f'process, module is not enabled.')


    def stop(self):
        """
        Shuts down the Metrics processing thread.
        """
        if self.process is not None:
            if self.process.is_alive():
                logger.debug(f'[{self.module_name}] process shutting down...')
                self.state_q.put('close', timeout=2)
                self.process.join(timeout=2)
                self.process = None
                logger.info(f'[{self.module_name}] process stopped and joined '
                            f'main thread.')
            else:
                logger.debug(f'Cannot stop [{self.module_name}] '
                            f'process, not running.')
        else:
            logger.debug('Ignoring request to stop [{self.module_name}] '
                         'process, module is not enabled.')
        self.active = False



    class MetricsProcess(mp.Process):
        """
        Multiprocessing Process to compute and deliver Signifier
        metrics to the push gateway.
        """
        def __init__(self, parent:Metrics) -> None:
            super().__init__()
            # Process management
            self.daemon = True
            self.event = mp.Event()
            self.state_q = parent.state_q
            self.main_config = parent.main_config
            self.hostname = parent.hostname
            self.config = parent.config
            self.metrics_q = parent.metrics_q
            # Prometheus config
            self.push_period = self.config['push_period']
            
            self.registry = CollectorRegistry()
            self.metrics = {}
            self.build_metrics()
            #start_http_server(self.config['server_port'])


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
                # Drain queue, bailing after 100 ms ensuring we don't get stuck
                loop_time = time.time()
                while time.time() < loop_time + 0.1:
                    try:
                        input_metric = self.metrics_q.get_nowait()
                        if (metric := self.metrics.get(input_metric[0])) is not None:
                            if 'gauge' in metric.keys():
                                metric['gauge'].labels(self.hostname).set(input_metric[1])
                                continue
                            if 'info' in metric.keys():
                                metric['info'].info(
                                    {'instance':self.hostname,
                                    'value':input_metric[1]})
                                continue
                        else:
                            name = input_metric[0]
                            self.metrics[name] = self.create_metric(
                                                    name, {'type':'gauge'})
                            self.metrics[name]['gauge'].labels(
                                                    self.hostname).set(
                                                    input_metric[1])
                        # TODO Add array metrics

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
                    except (ConnectionResetError,
                            ConnectionRefusedError,
                            URLError):
                        self.increase_push_time()
                        logger.warning(f'Prometheus gateway '
                            f'[{self.config["target_gateway"]}] '
                            f'cannot be reached. Retry in '
                            f'{self.push_period}s.')
                        prev_push = time.time()
                time.sleep(0.001)


        def build_metrics(self):
            """
            Construct a list of Prometheus metric objects for the push gateway
            """
            for module, config in self.main_config.items():
                metrics = config.get('sources', {})
                metrics.update(config.get('destinations', {}))
                if metrics is not None and metrics != {}:
                    for name, metric in metrics.items():
                        self.metrics[name] = self.create_metric(name, metric)


        def create_metric(self, name:str, metric:dict) -> dict:
            """
            Build and return a Prometheus metric object type based on the
            dictionary supplied in the arguments.  
            """
            new_metric = None
            if metric.get('enabled', True):
                if (metric_type := metric.get('type', '')) == 'gauge':
                    new_metric = {'gauge':Gauge(f'sig_{name}',
                                    metric.get('description', ''),
                                    labelnames=['instance'],
                                    registry=self.registry)}
                    new_metric['gauge'].labels(self.hostname)
                elif metric_type == 'info':
                    new_metric = {'info':Info(f'sig_{name}',
                                    metric.get('description', ''),
                                    registry=self.registry)}
                return new_metric


        def increase_push_time(self):
            """
            Increases duration between push attempts if the gateway
            is not reachable.
            """
            self.push_period += 2
            if self.push_period > 30:
                self.push_period = 30


class ArrayMetric():
    """
    Object class to handle arrays of Prometheus metrics.
    """
    def __init__(self, name:str, description:str, metric_type) -> None:
        self.name = name
        self.description = description
        self.metric_type = metric_type
        self.values = []

        def update_value(self, index:int, value):
            try:
                self.values[index] = value
            except IndexError:
                for i in range(len(self.values) - 1, index - 1):
                    self.values[i] = value if i == index else None


class MetricsPusher():
    """
    Object for managing module-wide metrics updates to Prometheus push gateway.
    """
    def __init__(self, metrics_q, period=0.1) -> None:
        """
        MetricsPusher is initialised with the metrics queue pointing to the
        metrics module for collating updated metrics.
        
        Use `period=(float)` to define minimum second between pushes.  
        """
        self.metrics_q = metrics_q
        self.last_values = {}
        self.new_values = {}
        self.period = period
        self.prev_push_time = time.time()


    def update_dict(self, dict):
        """
        Updates each value from dictionary only if it's different from the previous.
        """
        for k, v in dict.items():
            if self.last_values.get(k) != v or self.last_values.get(k) is None:
                self.new_values[k] = v
                self.last_values[k] = v


    def update(self, name, value):
        """
        Updates a single value only if it's different from the previous.
        """
        if self.last_values.get(name) != value or self.last_values.get(name) is None:
            self.new_values[name] = value
            self.last_values[name] = value


    def queue(self):
        """
        Position the latest dictionary of data in the metrics push gateway
        queue. Each dictionary item is unpacked, sent to the metrics queue.
        Sent metrics are removed from the `new_values` dictionary, leaving
        metrics unable to be sent due to a full queue to be sent in the
        next queue attempt.  
        """
        if self.metrics_q is not None:
            if self.new_values is not None or self.new_values != {}:
                if self.period == 0 or time.time()\
                        > self.prev_push_time + self.period:
                    for k in list(self.new_values):
                        try:
                            self.metrics_q.put_nowait(
                                (k, self.new_values.pop(k)))
                            
                        except Full:
                            pass
                    self.prev_push_time = time.time()