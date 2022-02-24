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
import socket
import logging
from queue import Empty
from urllib.error import URLError

import multiprocessing as mp

from prometheus_client import CollectorRegistry, Gauge, Info, push_to_gateway

from src.sigmodule import SigModule
from src.sigprocess import ModuleProcess

logger = logging.getLogger(__name__)


class Metrics(SigModule):
    """# Metrics

    Process to send metrics to the Prometheus push gateway.
    """

    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)

    def create_process(self):
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        self.process = MetricsProcess(self)


class MetricsProcess(ModuleProcess, mp.Process):
    """
    Multiprocessing Process to compute and deliver Signifier
    metrics to the push gateway.
    """

    def __init__(self, parent: Metrics) -> None:
        super().__init__(parent)
        # Prometheus config
        self.hostname = parent.main_config["general"]["hostname"]
        self.push_period = self.config["push_period"]
        self.metrics_q = parent.metrics_q
        self.metrics_dict = {}
        self.registry = CollectorRegistry()
        self.build_metrics()
        if self.parent_pipe.writable:
            self.parent_pipe.send("initialised")

    def pre_run(self):
        """
        Module-specific Process run preparation.
        """
        self.prev_push = 0
        if self.metrics_q is None:
            self.failed("No metrics_q assigned to module!")
            return False
        else:
            return True

    def mid_run(self):
        """
        Module-specific Process run commands. Where the bulk of the module's
        computation occurs.
        """
        # Drain queue, bailing after 100 ms ensuring we don't get stuck
        loop_time = time.time()
        while time.time() < loop_time + 0.1:
            try:
                input_metric = self.metrics_q.get_nowait()
            except Empty:
                break

            if (metric := self.metrics_dict.get(input_metric[0])) is not None:
                if "gauge" in metric.keys():
                    metric["gauge"].labels(self.hostname).set(input_metric[1])
                    continue
                if "info" in metric.keys():
                    metric["info"].info(
                        {"instance": self.hostname, "value": input_metric[1]}
                    )
                    continue
            else:
                name = input_metric[0]
                self.metrics_dict[name] = self.create_metric(
                    name, {"type": "gauge"}
                )
                self.metrics_dict[name]["gauge"].labels(self.hostname).set(
                    input_metric[1]
                )
            # TODO Add array metrics
        # Push current registry values if enough time has lapsed
        if time.time() > self.prev_push + self.push_period:
            try:
                push_to_gateway(
                    self.config["target_gateway"],
                    self.config["job_name"],
                    self.registry,
                    timeout=self.config["timeout"],
                )
            except (ConnectionResetError, ConnectionRefusedError, URLError, socket.error) as exception:
                print(exception)
                self.increase_push_time()
                logger.warning(
                    f"Prometheus gateway [{self.config['target_gateway']}] "
                    f"cannot be reached. Retry in {self.push_period}s."
                )
                self.prev_push = time.time()
                return None
        self.push_period = self.config["push_period"]

    def build_metrics(self):
        """
        Construct a list of Prometheus metric objects for the push gateway
        """
        vals = self.values_config.copy()
        for module, config in vals.items():
            source_metrics = config.get("sources", {})
            dest_metrics = config.get("destinations", {})
            if source_metrics != {}:
                for name, metric in source_metrics.items():
                    self.metrics_dict[name] = self.create_metric(name, metric)
            if dest_metrics != {}:
                for name, metric in dest_metrics.items():
                    self.metrics_dict[name] = self.create_metric(name, metric)

    def create_metric(self, name: str, metric: dict) -> dict:
        """
        Build and return a Prometheus metric object type based on the
        dictionary supplied in the arguments.
        """
        new_metric = None
        if metric.get("enabled", True):
            if (metric_type := metric.get("type", "")) == "gauge":
                new_metric = {
                    "gauge": Gauge(
                        f"sig_{name}",
                        metric.get("description", ""),
                        labelnames=["instance"],
                        registry=self.registry,
                    )
                }
                new_metric["gauge"].labels(self.hostname)
            elif metric_type == "info":
                new_metric = {
                    "info": Info(
                        f"sig_{name}",
                        metric.get("description", ""),
                        registry=self.registry,
                    )
                }
            return new_metric

    def increase_push_time(self):
        """
        Increases duration between push attempts if the gateway
        is not reachable.
        """
        self.push_period += 2
        if self.push_period > 30:
            self.push_period = 30


# class ArrayMetric:
#     """
#     Object class to handle arrays of Prometheus metrics.
#     """

#     def __init__(self, name: str, description: str, metric_type) -> None:
#         self.name = name
#         self.description = description
#         self.metric_type = metric_type
#         self.values = []

#         def update_value(self, index: int, value):
#             try:
#                 self.values[index] = value
#             except IndexError:
#                 for i in range(len(self.values) - 1, index - 1):
#                     self.values[i] = value if i == index else None
