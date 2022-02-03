
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

import logging

log_dt = "%d-%b-%y %H:%M:%S"
log_msg = "%(asctime)s %(levelname)8s - %(module)12s.py:%(lineno)4d - %(funcName)20s: %(message)s"
logging.basicConfig(level=logging.DEBUG, format=log_msg, datefmt=log_dt)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import sys
import time
import json
import socket
import signal

from queue import Empty, Full
import multiprocessing as mp
from multiprocessing.connection import Connection

from signifier.leds import Leds
from signifier.metrics import Metrics
from signifier.mapping import Mapping
from signifier.analysis import Analysis
from signifier.bluetooth import Bluetooth
from signifier.composition import Composition


HOST_NAME = socket.gethostname()
CONFIG_FILE = 'config.json'
config_dict = None

metrics_q = mp.Queue(maxsize=500)

source_pipes = {'analysis':None,'bluetooth':None}
dest_pipes = {'arduino':None,'composition':None}



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
                composition_module.stop()
                bluetooth_module.stop()
                analysis_module.stop()
                mapping_module.stop()
                metrics_module.stop()
                leds_module.stop()
                logger.info('Signifier shutdown complete!')
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
    print()
    logger.info('Prepare to be Signified!!')
    print()

    with open(CONFIG_FILE) as c:
        config_dict = json.load(c)
    config_dict['general']['hostname'] = HOST_NAME

    main_thread = mp.current_process()
    exit_handler = ExitHandler()

    leds_module = Leds('leds', config_dict, metrics_q=metrics_q)
    leds_module.start()
    analysis_module = Analysis('analysis', config_dict, metrics_q=metrics_q)
    analysis_module.start()
    bluetooth_module = Bluetooth('bluetooth', config_dict, metrics_q=metrics_q)
    bluetooth_module.start()
    composition_module = Composition('composition', config_dict, metrics_q=metrics_q)
    composition_module.start()

    dest_pipes = {
        'leds':leds_module.destination_in,
        'composition':composition_module.destination_in}
    source_pipes = {
        'analysis':analysis_module.source_out,
        'bluetooth':bluetooth_module.source_out}
    
    mapping_module = Mapping(
        'mapping', config_dict, dest_pipes, source_pipes, metrics_q)
    mapping_module.start()
    
    metrics_module = Metrics('metrics', config_dict, metrics_q)
    metrics_module.start()

    while True:
        # TODO Change composition module over to threaded loop
        composition_module.tick()
        time.sleep(0.1)
