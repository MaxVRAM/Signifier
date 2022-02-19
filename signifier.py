#!/usr/bin/env python

#    _________.__              .__  _____.__
#   /   _____/|__| ____   ____ |__|/ ____\__| ___________
#   \_____  \ |  |/ ___\ /    \|  \   __\|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  ||  |  |  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__||__|  |__|\___  >__|
#          \/   /_____/      \/                  \/

"""# Signifier
Version 0.9.0

A complete solution to drive the Melbourne Music Week Signifier units.
Visit the GitHub repo for installation and usage documentation:

https://github.com/MaxVRAM/Signifier

Copyright (c) 2022 Chris Vik - MIT License
"""


import sys
import json
import time
import socket
import signal

import multiprocessing as mp
import logging

LOG_DT = '%d-%m-%y %H:%M:%S'
LOG_MSG = '%(asctime)s %(levelname)8s - %(module)12s.py:%(lineno)4d - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_MSG, datefmt=LOG_DT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from src.leds import Leds
from src.mapper import Mapper
from src.metrics import Metrics
from src.analysis import Analysis
from src.bluetooth import Bluetooth
from src.composition import Composition

HOST_NAME = socket.gethostname()
CONFIG_FILE = 'cfg/config.json'
VALUES_FILE = 'cfg/values.json'
RULES_FILE = 'cfg/rules.json'
config = None

modules = {}
metrics_q = mp.Queue(maxsize=500)

#    _________.__            __      .___
#   /   _____/|  |__  __ ___/  |_  __| _/______  _  ______
#   \_____  \ |  |  \|  |  \   __\/ __ |/  _ \ \/ \/ /    \
#   /        \|   Y  \  |  /|  | / /_/ (  <_> )     /   |  \
#  /_______  /|___|  /____/ |__| \____ |\____/ \/\_/|___|  /
#          \/      \/                 \/                 \/


class ExitHandler:
    """
    Manages signals `SIGTERM` and `SIGINT`, and houses the subsequently called
    `shutdown()` method which exits the Signifier application gracefully.
    """

    signals = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}

    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, *args):
        """
        Initiates Signifier shutdown sequence when called by main thread.
        This is either called via signal callbacks, or explicitly via
        standard function calls.
        """
        if mp.current_process() is main_thread:
            if not self.exiting:
                self.exiting = True
                print()
                logger.info("Shutdown sequence started...")

                metrics_q.cancel_join_thread()

                for m in modules.values():
                    m.stop()

                logger.info("Signifier shutdown complete!")
                self.exiting = False
                print()
                sys.exit()
        else:
            return None


#     _____         .__
#    /     \ _____  |__| ____
#   /  \ /  \\__  \ |  |/    \
#  /    Y    \/ __ \|  |   |  \
#  \____|__  (____  /__|___|  /
#          \/     \/        \/

if __name__ == '__main__':
    main_thread = mp.current_process()
    exit_handler = ExitHandler()

    with open(CONFIG_FILE) as c:
        config = json.load(c)
    if config['general']['hostname'] != HOST_NAME:
        config['general']['hostname'] = HOST_NAME
    with open(CONFIG_FILE, 'w', encoding='utf8') as c:
        json.dump(config, c, ensure_ascii=False, indent=4)
    with open(VALUES_FILE) as v:
        values = json.load(v)
    with open(RULES_FILE) as r:
        rules = json.load(r)

    print()
    logger.info(f'Starting Signifier on [{config["general"]["hostname"]}]')
    print()

    modules = {
        'leds': Leds('leds', config, metrics=metrics_q,
                     values=values['leds']),
        'mapper': Mapper('mapper', config, metrics=metrics_q,
                         values=values, rules=rules),
        'metrics': Metrics('metrics', config, metrics=metrics_q,
                           values=values),
        'analysis': Analysis('analysis', config, metrics=metrics_q,
                             values=values['analysis']),
        'bluetooth': Bluetooth('bluetooth', config, metrics=metrics_q,
                               values=values['bluetooth']),
        'composition': Composition('composition', config, metrics=metrics_q,
                                   values=values['composition']),
    }

    pipes = {k: v.module_pipe for k, v in modules.items()}
    modules['mapper'].set_pipes(pipes)

    for m in modules.values():
        m.initialise()

    time.sleep(1)

    for m in modules.values():
        m.start()

    time.sleep(1)

    while True:
        for m in modules.values():
            m.monitor()
        time.sleep(0.01)
