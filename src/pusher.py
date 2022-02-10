
#  __________             .__                  
#  \______   \__ __  _____|  |__   ___________ 
#   |     ___/  |  \/  ___/  |  \_/ __ \_  __ \
#   |    |   |  |  /\___ \|   Y  \  ___/|  | \/
#   |____|   |____//____  >___|  /\___  >__|   
#                       \/     \/     \/       
"""
Provides module Process' a controlled method to push metrics to the gateway.
"""

import time
from queue import Full


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