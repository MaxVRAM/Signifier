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
import subprocess
from dictdiffer import diff as dict_diff
import multiprocessing as mp


# Imports appear unused, but are dynamically loaded by module dictionary
from src.leds import Leds
from src.mapper import Mapper
from src.metrics import Metrics
from src.analysis import Analysis
from src.bluetooth import Bluetooth
from src.composition import Composition

from src.utils import SigLog
from src.utils import plural
from src.utils import Stopwatch
from src.utils import load_config_files


SigLog.roll_over()
logger = SigLog.get_logger('Sig')

HOSTNAME = os.getenv('HOST')
SIG_PATH = os.getenv('SIGNIFIER')
SITE_PATH = os.path.join(SIG_PATH, 'site')
CONFIG_PATH = os.path.join(SIG_PATH, 'cfg')
SIG_SCRIPTS = os.path.join(SIG_PATH, 'scripts')
DEFAULTS_PATH = os.path.join(SIG_PATH, 'sys', 'default_configs')
CONFIG_UPDATE_SECS = 2
CONFIG_FILES = {'config':'config.json',
                'values':'values.json',
                'rules': 'rules.json'}
configs = {name:{'file':file, 'modules':None}\
    for (name, file) in CONFIG_FILES.items()}

config_update_time = time.time()
process_loop_sleep = 0.001
metrics_q = mp.Queue(maxsize=500)

module_objects = {}
module_types = {'leds':Leds, 
                'mapper':Mapper,
                'metrics':Metrics,
                'analysis':Analysis,
                'bluetooth':Bluetooth,
                'composition':Composition}


def check_config_update():
    """
    Checks config files from the Signifier config path and updates any modules
    with updated configuration values.
    """
    global CONFIG_UPDATE_SECS, config_update_time, module_objects, configs

    updated_modules = set()
    if time.time() > config_update_time + CONFIG_UPDATE_SECS:
        config_update_time = time.time()
        new_configs = load_config_files(configs, CONFIG_FILES, CONFIG_PATH, DEFAULTS_PATH)
        values_config_changed = False
        # Find differences in current and new config
        for config, values in configs.items():
            modules = values['modules']
            for module, settings in modules.items():
                diff = list(
                    dict_diff(settings, new_configs[config]['modules'][module]))
                if len(diff) > 0:
                    print()
                    logger.info(f'Config change: [{module}]: {diff}')
                    updated_modules.add(module)
                    if config == 'values':
                        values_config_changed = True
        # Find and update all metrics modules if values config has changed
        if values_config_changed:
            for module in module_objects.values():
                if type(module).__name__.lower() == module_types['metrics']:
                    updated_modules.add(module)
        # Tell modules with updated configs to reload with new settings
        if updated_modules is not None and len(updated_modules) > 0:
            configs = new_configs
            logger.info(f'Updating modules: {updated_modules}')
            for m in updated_modules:
                if m in module_objects:
                    module_objects[m].update_config(configs)
            print()
        CONFIG_UPDATE_SECS = configs['config']['modules']['general'].get(
                'config_update_secs', 2)


def module_callback(module, message):
    """
    Provided to all modules on initialisation, this module executes functions in the
    main thread based on the supplied `message=(string)` kwarg. Arguments are simply
    for logging purposes of callback details.
    """
    logger.info(f'Message from [{module}]: "{message}"')
    # The analysis module has detect silence for X seconds, indicating a critical
    # ASIO underrun, which silently crashes PyGame's audio engine and requires a restart.
    if 'underrun' in message:
        if (module_objects.get('composition') is not None and
                module_objects.get('analysis') is not None and
                module_objects.get('composition').module_config.get('enabled', False) and
                module_objects.get('composition').module_config.get('mix_volume', 0) > 0):
            logger.critical(f'Message "{message}" triggered Signifier service restart.')
            command = os.path.join(SIG_SCRIPTS, 'restart.sh')
            subprocess.Popen([command])



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
                logger.info("Shutdown sequence started...")
                # Ignore open metrics queue points for open threads 
                metrics_q.cancel_join_thread()
                # Ask each module to close gracefully
                for m in module_objects.values():
                    if m.status.name not in ['closed', 'empty', 'disabled', 'failed']:
                        logger.debug(f'[{m.module_name}] status: "{m.status.name}". Asking to stop...')
                        m.stop()
                timeout = Stopwatch()
                still_waiting = True
                # Hold off shutdown for up to 3 seconds if a process is hanging
                while still_waiting and not timeout.check(3):
                    still_waiting = False
                    for module in module_objects.values():
                        if module.status.name not in ['closed', 'empty', 'disabled', 'failed']:
                            still_waiting = True
                    time.sleep(process_loop_sleep)
                logger.info("Signifier shutdown complete!")
                self.exiting = False
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

    configs = load_config_files(configs, CONFIG_FILES, CONFIG_PATH, DEFAULTS_PATH)
    if configs == None:
        exit_handler.shutdown()

    config_data = configs['config']['modules']
    logger.setLevel(config_data['general'].get('log_level'))
    process_loop_sleep = config_data['general'].get('process_loop_sleep')
    
    # Write current hostname to config file
    if config_data['general']['hostname'] != HOSTNAME:
        config_data['general']['hostname'] = HOSTNAME
        with open(os.path.join(CONFIG_PATH, configs['config']['file']),
                  'w', encoding='utf8') as c:
            json.dump(config_data, c, ensure_ascii=False, indent=4)

    print()
    logger.info(f'Starting Signifier on [{HOSTNAME}] as user [{os.getenv("USER")}]')

    # Define and load modules
    for name, settings in configs['config']['modules'].items():
        if (module_class := module_types.get(settings.get('module_type', ''))) is not None:
            module_objects[name] = module_class(name, configs, metrics=metrics_q, callback=module_callback)
        elif name != 'general':
            logger.warning(f'[{name}] module has no module_type, so cannot be started. '
                           f'Check config.json!')
    # Provide any mapper modules the module pipe from each module except its own
    for mapper_name, mapper_module in module_objects.items():
        if type(mapper_module).__name__.lower() == 'mapper':
            mapper_module.pipes = {name: module.module_pipe
                for name, module in module_objects.items()
                if mapper_name != name}

    logger.info(f'Signifier initialised with ({len(module_objects)}) '
                f'module{plural(module_objects)}. Starting main program loop...')

    # Main update loop
    while True:
        for m in module_objects.values():
            m.monitor_process()
        check_config_update()
        time.sleep(process_loop_sleep)
