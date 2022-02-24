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

import os
import sys
import json
import time
import signal
from dictdiffer import diff as dict_diff
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

HOSTNAME = os.getenv('HOST')
SIG_PATH = os.getenv('SIGNIFIER')
SITE_PATH = os.path.join(SIG_PATH, 'site')
CFG_PATH = os.path.join(SIG_PATH, 'cfg')
DEFAULTS_PATH = os.path.join(CFG_PATH, 'defaults')
CONFIG_FILE = 'config.json'
VALUES_FILE = 'values.json'
RULES_FILE = 'rules.json'
CONFIG_UPDATE_SECS = 5

prev_config_update = time.time()

metrics_q = mp.Queue(maxsize=500)

modules = {}
config = {}
values = {}
rules = {}


def load_config_files() -> tuple:
    with open(os.path.join(CFG_PATH, CONFIG_FILE)) as c:
        try:
            new_config = json.load(c)
        except json.decoder.JSONDecodeError:
            new_config = None
    with open(os.path.join(CFG_PATH, VALUES_FILE)) as v:
        try:
            new_values = json.load(v)
        except json.decoder.JSONDecodeError:
            new_values = None
    with open(os.path.join(CFG_PATH, RULES_FILE)) as r:
        try:
            new_rules = json.load(r)
        except json.decoder.JSONDecodeError:
            new_rules = None
    return new_config, new_values, new_rules


def check_config_update():
    global prev_config_update, modules, config, values, rules

    updated_modules = set()

    if time.time() > prev_config_update + CONFIG_UPDATE_SECS:
        prev_config_update = time.time()
        new_config, new_values, new_rules = load_config_files()

        if new_config is not None:
            for k, v in new_config.items():
                if k in config.keys():
                    diff = list(dict_diff(config[k], new_config[k]))
                    if len(diff) > 0:
                        print()
                        logger.info(f'Detected change in config: {diff}')
                        updated_modules.add(k)

        if new_values is not None:
            for k, v in new_values.items():
                if k in values.keys():
                    diff = list(dict_diff(values[k], new_values[k]))
                    if len(diff) > 0:
                        print()
                        logger.info(f'Detected change in config: {diff}')
                        updated_modules.add(k)

        if new_rules is not None:
            if set(new_rules) ^ set(rules):
                updated_modules.add('mapper')
        if new_values is not None:
            if set(new_values) ^ set(values):
                updated_modules.add('metrics')

        if updated_modules is not None and len(updated_modules) > 0:
            config = new_config
            values = new_values
            rules = new_rules
            logger.info(f'Updating modules: {updated_modules}')
            for m in updated_modules:
                if m in values:
                    new_value_config = values.get(m)
                else:
                    new_value_config = values
                modules[m].update_config(config, values=new_value_config, rules=rules)



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
        if mp.current_process() is main_thread and mp.parent_process() is None:
            if not self.exiting:
                self.exiting = True
                print()
                logger.info("Shutdown sequence started...")
                # Ignore open metrics queue points for open threads 
                metrics_q.cancel_join_thread()
                # Ask each module to close gracefully
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

    config, values, rules = load_config_files()

    if config['general']['hostname'] != HOSTNAME:
        config['general']['hostname'] = HOSTNAME
        with open(os.path.join(CFG_PATH, CONFIG_FILE), 'w', encoding='utf8') as c:
            json.dump(config, c, ensure_ascii=False, indent=4)

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
    time.sleep(0.5)

    while True:
        for m in modules.values():
            m.monitor()
        check_config_update()
        time.sleep(0.001)
