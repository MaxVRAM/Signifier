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

from queue import Empty
import multiprocessing as mp

import logging

LOG_DT = "%d-%b-%y %H:%M:%S"
LOG_MSG = "%(asctime)s %(levelname)8s - %(module)12s.py:%(lineno)4d - %(funcName)20s: %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_MSG, datefmt=LOG_DT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from utils import validate_library
from leds import Leds
from mapper import Mapper
from metrics import Metrics, MetricsPusher
from analysis import Analysis
from bluetooth import Bluetooth
from composition import Composition


HOST_NAME = socket.gethostname()
CONFIG_FILE = 'config.json'
config = None

queues = {'return':mp.Queue(maxsize=50), 'metrics':mp.Queue(maxsize=500)}
metrics_pusher = MetricsPusher(queues['metrics'])

modules = {}

source_pipes = {'arduino':None, 'analysis':None, 'bluetooth':None, 'composition':None}
dest_pipes = {'arduino':None, 'analysis':None, 'bluetooth':None, 'composition':None}



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
    signals = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}

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
                logger.info('Shutdown sequence started...')

                for k, v in modules:
                    v.stop()

                for k, v in queues:
                    v.cancel_join_thread()

                logger.info('Signifier shutdown complete!')
                self.exiting = False
                print()
                sys.exit()
        else:
            return None


def process_returns():
    try:
        return_message = None
        while (return_message := queues['return'].get_nowait()) is not None:
            if return_message[0] == 'failed':
                try:
                    modules[return_message[1]].stop()
                except KeyError:
                    logger.warning(f'[{return_message[1]}] module failed '
                                   f'before initialisation.')
                    pass
    except Empty:
        pass

    for k, v in modules:
        try:
            metrics_pusher.update(f'{k}_active', 1 if v.active else 0)
        except AttributeError:
            pass
    metrics_pusher.queue()


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
    with open(CONFIG_FILE, 'w', encoding ='utf8') as c:
        json.dump(config, c, ensure_ascii = False, indent=4)

    if not validate_library(config['composition']):
        logger.info('Aborting Signifier startup!')
        exit_handler.shutdown()

    print()
    logger.info(f'Starting Signifier on [{config["general"]["hostname"]}]')
    print()

    modules = {
        'leds': Leds('leds', config, queues=queues),
        'mapper': Mapper('mapper', config, queues=queues),
        'metrics': Metrics('metrics', config, queues=queues),
        'analysis': Analysis('analysis', config, queues=queues),
        'bluetooth': Bluetooth('bluetooth', config, queues=queues),
        'composition': Composition('composition', config, queues=queues)
    }

    pipes = {}
    pipes['sources'] = {k:v.source_out for k, v in modules.items()}
    pipes['destinations'] = {k:v.dest_in for k, v in modules.items()}

    modules['mapper'].set_pipes(pipes)

    for k, v in modules:
        v.initialise()

    time.sleep(2)

    for k, v in modules:
        v.start()

    while True:
        process_returns()
        time.sleep(0.1)
