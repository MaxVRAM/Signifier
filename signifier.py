
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
import signal

from queue import Empty, Full
import multiprocessing as mp
from multiprocessing.connection import Connection

from prometheus_client import CollectorRegistry, push_to_gateway

from signify.leds import Leds
from signify.analysis import Analysis
from signify.mapping import ValueMapper
from signify.bluetooth import Bluetooth
from signify.composition import Composition


CONFIG_FILE = 'config.json'
config_dict = None

registry = CollectorRegistry()

leds_module = Leds
analysis_module = Analysis
bluetooth_module = Bluetooth
composition_module = Composition

source_pipes = {'analysis':None,'bluetooth':None}
destination_pipes = {'arduino':None,'composition':None}



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

    main_thread = mp.current_process()
    exit_handler = ExitHandler()

    leds_module = Leds('leds', config_dict, prom_registry=registry)
    leds_module.start()
    analysis_module = Analysis('analysis', config_dict, prom_registry=registry)
    analysis_module.start()
    bluetooth_module = Bluetooth('bluetooth', config_dict, prom_registry=registry)
    bluetooth_module.start()
    composition_module = Composition('composition', config_dict, prom_registry=registry)
    composition_module.start()

    destination_pipes = {
        'leds':leds_module.destination_in,
        'composition':composition_module.destination_in}
    source_pipes = {
        'analysis':analysis_module.source_out,
        'bluetooth':bluetooth_module.source_out}
    
    mapping_module = ValueMapper('mapping', config_dict, destination_pipes, source_pipes)
    mapping_module.start()

    while True:
        # TODO Change composition module over to threaded loop
        composition_module.tick()
        push_to_gateway('localhost:9091', job='signifier', timeout=0.1, registry=registry)
        time.sleep(0.1)
