#    _________.__          ____ ___   __  .__.__
#   /   _____/|__| ____   |    |   \_/  |_|__|  |   ______
#   \_____  \ |  |/ ___\  |    |   /\   __\  |  |  /  ___/
#   /        \|  / /_/  > |    |  /  |  | |  |  |__\___ \
#  /_______  /|__\___  /  |______/   |__| |__|____/____  >
#          \/   /_____/                                \/

import os
import sys
import json
import time
import signal
import logging
import logging.handlers
import numpy as np

logger = logging.getLogger(__name__)


def plural(value) -> str:
    """
    Return "s" or "" pluralise strings based on supplied (int) value or len(!int).
    """
    if value is None:
        return ""
    try:
        num = int(value)
    except TypeError:
        num = len(value)
    # except:
    #     return ""
    return "" if num == 1 else "s"


def scale(value, source_range, dest_range, *args):
    """
    Scale the given value from the scale of src to the scale of dst.\
    Send argument `clamp` to limit output to destination range as well.
    """
    s_range = source_range[1] - source_range[0]
    d_range = dest_range[1] - dest_range[0]
    scaled_value = ((value - source_range[0]) / s_range) * d_range + dest_range[0]
    if "clamp" in args:
        return max(dest_range[0], min(dest_range[1], scaled_value))
    return scaled_value


def lerp(a, b, pos) -> float:
    """### Basic linear interpolation.
    
    This method returns a value between the given `a`->`b` values.\n
    When `pos=0` the return value will be `a`.\n
    When `pos=1` the turn value will be the value of `b`. `pos=0.5` would be\
    half-way between `a` and `b`.
    """
    lerp_out = a * (1.0 - pos) + (b * pos)
    return lerp_out


def db_to_amp(db: float) -> float:
    """
    Convert dB to amplitude
    """
    return pow(10, float(db) / 100)


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    """
    # https://github.com/SiggiGue/pyfilterbank/issues/17
    rms = np.sqrt(np.mean(np.absolute(a) ** 2))
    return rms


def load_dict_from_json(file) -> dict:
    """
    Returns a valid dictionary from provided absolute path to JSON file. Returns
    None otherwise.
    """
    try:
        with open(file) as c:
            try:
                return json.load(c)
            except json.decoder.JSONDecodeError:
                return None
    except FileNotFoundError:
        return None


def load_config_files(configs_dict:dict, config_files:dict, config_path:str, default_path:str) -> dict:
    """
    Reads configuration JSON files, applying a series of checks to retain current
    values or apply defaults if configuration files are invalid.
    """
    new_configs = {name:{'file':file, 'modules':None}\
        for (name, file) in config_files.items()}
    for name, values in configs_dict.items():
        config_file = os.path.join(config_path, values['file'])
        default_file = os.path.join(default_path, values['file'])
        # 1. Try to apply new config file
        if os.path.isfile(config_file) and (
                new_config := load_dict_from_json(config_file)) is not None:
            new_configs[name]['modules'] = new_config
            continue
        # 2. Try to keep current settings
        if values.get('modules') is not None:
            logger.warning(f'Config file [{values["file"]}] broken or missing. Keeping current settings.')
            new_configs[name]['modules'] = values['modules']
            continue
        # 3. Try to use default settings from backup file
        if os.path.isfile(default_file) and (
                new_config := load_dict_from_json(default_file)) is not None:
            logger.warning(f'Config file [{values["file"]}] broken or missing. Importing defaults.')
            new_configs[name]['modules'] = new_config
            continue
        # 4. Cannot continue without any settings. Terminate Signifier
        logger.critical(f'Config file [{values["file"]}] and its default are missing or broken!')
        signal.SIGTERM
    return new_configs


class FunctionHandler:
    """
    Object that handles incoming function call requests. Must be supplied
    its parent's module name and a dictionary containing parent object's
    instance variables available to be called.
    """
    def __init__(self, module_name, function_dict) -> None:
        self.module_name = module_name
        self.function_dict = function_dict


    def call(self, message):
        """
        Will perform a function call from the provided function name (with
        or without arguments) if a matching function name was supplied on
        instantiation of the FunctionHandler object.
        """
        if isinstance(message, str):
            command = message
        else:
            try:
                command = message[0]
                args = list(message[1:])
            except TypeError:
                logger.warning(f'Received malformed command: {message}')
                return None
        if (func := self.function_dict.get(command)) is not None:
            logger.debug(f'Received command "{command}", executing...')
            func(*args)
        else:
            logger.warning(f'Does not recognise "{command}" command.')



class SmoothedValue:
    # https://gitlab.zenairo.6 com/led-projects/dancyPi-audio-reactive-led/-/raw/262206d35962b2383f2649d726ff9bc513095ec7/python/dsp.py
    """
    Simple exponential smoothing filter
    """

    def __init__(self, init=0.0, amount=(0.5, 0.5), threshold=9e-5):
        """
        Smoothing arguments:

        - `init=0.0` value to initialise the filter with
        - `amount=(0.5, 0.5)` tuple with decay/rise smoothing amount,
        lower values increase smoothing.
        - `rise=0.5` rise smoothing [0-1], lower = more smoothing
        - `threshold=9e-5` delta of current and new value before snapping
        """
        assert 0.0 < amount[0] < 1.0, "Invalid decay smoothing factor"
        assert 0.0 < amount[1] < 1.0, "Invalid rise smoothing factor"
        self.decay = amount[0]
        self.rise = amount[1]
        self.value = init
        self.threshold = threshold

    def update(self, new_value):
        """
        Applies smoothing function between new value in argument to the
        existing one and returns result.
        """
        if abs(new_value - self.value) > self.threshold:
            if not isinstance(self.value, (int, float)):
                delta = new_value - self.value
                delta[delta > 0.0] = self.rise
                delta[delta <= 0.0] = self.decay
            else:
                delta = self.rise if new_value > self.value else self.decay
            self.value = delta * new_value + (1.0 - delta) * self.value
        else:
            self.value = new_value
        return self.value


class SigLog:
    file = "signifier.log"
    level = logging.DEBUG
    format_dt = '%d-%m-%y %H:%M:%S'
    format_msg = '%(asctime)s %(name)18s - %(levelname)10s - %(message)s'
    formatter = logging.Formatter(fmt=format_msg, datefmt=format_dt)


    def get_console_handler():
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(SigLog.formatter)
        return console_handler


    def get_file_handler():
        file_handler = logging.FileHandler(SigLog.file)
        file_handler.setFormatter(SigLog.formatter)
        return file_handler


    def get_logger(logger_name):
        logger = logging.getLogger(logger_name)
        logger.setLevel(SigLog.level)
        logger.addHandler(SigLog.get_console_handler())
        logger.addHandler(SigLog.get_file_handler())
        logger.propagate = False
        return logger


    def roll_over():        
        should_roll_over = os.path.isfile(SigLog.file)
        handler = logging.handlers.RotatingFileHandler(SigLog.file, mode='w', backupCount=5)
        if should_roll_over:
            handler.doRollover()

class TimeOut:
    """
    When `check()` is called on object, returns True when duration in seconds has
    elapsed since its creation.
    """

    def __init__(self, duration) -> None:
        self.start_time = time.time()
        self.duration = duration

    def check(self):
        return True if time.time() > self.start_time + self.duration else False
