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

from src.utils import validate_library

from src.leds import Leds
from src.metrics import Metrics, MetricsPusher
from src.mapping import Mapping
from src.analysis import Analysis
from src.bluetooth import Bluetooth
from src.composition import Composition


HOST_NAME = socket.gethostname()
CONFIG_FILE = 'config.json'
config_dict = None

return_q = mp.Queue(maxsize=50)
metrics_q = mp.Queue(maxsize=500)

metrics_pusher = MetricsPusher(metrics_q)

leds_module = None
mapping_module = None
analysis_module = None
bluetooth_module = None
composition_module = None

module_list = [
    leds_module,
    mapping_module,
    analysis_module,
    bluetooth_module,
    composition_module
]

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
                try:
                    composition_module.stop()
                except (NameError, AttributeError):
                    pass
                try:
                    bluetooth_module.stop()
                except (NameError, AttributeError):
                    pass
                try:
                    analysis_module.stop()
                except (NameError, AttributeError):
                    pass
                try:
                    mapping_module.stop()
                except (NameError, AttributeError):
                    pass
                try:
                    leds_module.stop()
                except (NameError, AttributeError):
                    pass
                try:
                    metrics_module.stop()
                except (NameError, AttributeError):
                    pass
                logger.info('Signifier shutdown complete!')
                self.exiting = False
                print()
                sys.exit()
        else:
            return None


def metrics_push():
    try:
        return_message = None
        while (return_message := return_q.get_nowait()) is not None:
            if return_message[0] == 'failed':
                module_name = return_message[1] + '_module'
                try:
                    module = locals()[module_name]
                    module.stop()
                    logger.warning(f'Failed module [{return_message[1]}] has been stopped.')
                except KeyError:
                    logger.warning(f'[{return_message[1]}] module failed '
                                   f'before initialisation.')
                    pass
    except Empty:
        pass

    for m in module_list:
        try:
            metrics_pusher.update(f'{m.module_name}_active',
                                    1 if m.active else 0)
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
        config_dict = json.load(c)
    if config_dict['general']['hostname'] != HOST_NAME:
        config_dict['general']['hostname'] = HOST_NAME
    with open(CONFIG_FILE, 'w', encoding ='utf8') as c:
        json.dump(config_dict, c, ensure_ascii = False, indent=4)

    if not validate_library(config_dict['composition']):
        logger.info('Aborting Signifier startup!')
        exit_handler.shutdown()
        
    print()
    logger.info(f'Starting Signifier on [{config_dict["general"]["hostname"]}]')
    print()

    leds_module = Leds(
        'leds',
        config_dict,
        metrics_q=metrics_q,
        return_q=return_q)

    analysis_module = Analysis(
        'analysis',
        config_dict,
        metrics_q=metrics_q,
        return_q=return_q)

    bluetooth_module = Bluetooth(
        'bluetooth',
        config_dict,
        metrics_q=metrics_q,
        return_q=return_q)

    composition_module = Composition(
        'composition',
        config_dict,
        metrics_q=metrics_q,
        return_q=return_q)

    leds_module.start()
    analysis_module.start()
    bluetooth_module.start()
    composition_module.start()

    time.sleep(0.5)

    dest_pipes = {
        'leds':leds_module.destination_in,
        'analysis':analysis_module.destination_in,
        'bluetooth':bluetooth_module.destination_in,
        'composition':composition_module.destination_in}
    source_pipes = {
        'leds':leds_module.source_out,
        'analysis':analysis_module.source_out,
        'bluetooth':bluetooth_module.source_out,
        'composition':composition_module.source_out}
    
    mapping_module = Mapping(
        'mapping',
        config_dict,
        dest_pipes,
        source_pipes,
        metrics_q,
        return_q)

    metrics_module = Metrics(
        'metrics',
        config_dict,
        metrics_q,
        return_q)

    mapping_module.start()
    metrics_module.start()

    while True:
        # TODO Change composition module over to threaded loop
        try:
            composition_module.tick()
        except:
            print('DEBUG --- error in composition module tick.')

        metrics_push()

        time.sleep(0.1)
