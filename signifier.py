
#    _________.__              .__  _____.__              
#   /   _____/|__| ____   ____ |__|/ ____\__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \   __\|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  ||  |  |  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__||__|  |__|\___  >__|   
#          \/   /_____/      \/                  \/       



import logging

log_time_format = "%d-%b-%y %H:%M:%S"
log_message_format = "%(asctime)s %(levelname)8s - %(module)12s.py:%(lineno)4d - %(funcName)20s: %(message)s"

logging.basicConfig(
    level=logging.DEBUG,
    format=log_message_format,
    datefmt=log_time_format)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import sys
import time
import json
import signal

from queue import Empty, Full
import multiprocessing as mp
from multiprocessing.connection import Connection

from signify.arduino import Arduino
from signify.analysis import Analysis
from signify.mapping import ValueMapper
from signify.bluetooth import Bluetooth
from signify.composition import Composition


CONFIG_FILE = 'config.json'
config_dict = None

arduino_module = Arduino
analysis_module = Analysis
bluetooth_module = Bluetooth
composition_module = Composition

input_pipes = {'arduino':None,'composition':None}
output_pipes = {'analysis':None,'bluetooth':None}



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
                logger.info('Shutdown sequence started!')
                composition_module.stop()
                bluetooth_module.stop()
                analysis_module.stop()
                mapping_module.stop()
                arduino_module.stop()
                time.sleep(2)
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

    arduino_module = Arduino(config_dict['arduino'])
    arduino_module.start()
    analysis_module = Analysis(config_dict['analysis'])
    analysis_module.start()
    bluetooth_module = Bluetooth(config_dict['bluetooth'])
    bluetooth_module.start()
    composition_module = Composition(config_dict['composition'])
    composition_module.start()

    input_pipes = {
        'arduino':arduino_module.input_value_out,
        'composition':composition_module.input_value_out}
    output_pipes = {
        'analysis':analysis_module.output_value_out,
        'bluetooth':bluetooth_module.output_value_out}
    
    mapping_module = ValueMapper(config_dict['mapping'], input_pipes, output_pipes)
    mapping_module.start()

    while True:
        composition_module.tick()
        time.sleep(0.1)

