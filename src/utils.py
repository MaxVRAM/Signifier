#    _________.__          ____ ___   __  .__.__
#   /   _____/|__| ____   |    |   \_/  |_|__|  |   ______
#   \_____  \ |  |/ ___\  |    |   /\   __\  |  |  /  ___/
#   /        \|  / /_/  > |    |  /  |  | |  |  |__\___ \
#  /_______  /|__\___  /  |______/   |__| |__|____/____  >
#          \/   /_____/                                \/

import os
import logging
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


def validate_library(config_file: dict) -> bool:
    """
    Utility for checking validity of audio clip library.
    Returns `False` unless paths are valid and audio clips exist.
    """
    audio_path = config_file["base_path"]
    if not os.path.isdir(audio_path):
        logger.critical(f"Invalid root path for library: {audio_path}.")
        logger.info(f"Ensure audio library exists or check path in config.")
        return False
    else:
        collections = [f.path for f in os.scandir(audio_path) if f.is_dir()]
        if len(collections) == 0:
            logger.critical(f"No collections found in audio library: {audio_path}")
            logger.info(f"Ensure audio library exists or check path in config.")
            return False
        else:
            logger.info(
                f"Found {len(collections)} audio clip "
                f"collection{plural(collections)}."
            )
            clips = []
            for c in collections:
                for f in os.listdir(c):
                    if os.path.splitext(f)[1][1:] in config_file["valid_extensions"]:
                        clips.append(f)
            if len(clips) == 0:
                logger.critical(
                    f"No valid clips found in library with extention "
                    f'{config_file["valid_extensions"]}.'
                )
                return False
            logger.info(f"[{len(clips)}] clip{plural(clips)} found in library.")
            return True


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
                logger.warning(
                    f'[{self.module_name}] received '
                    f'Malformed command: {message}'
                )
                return None
        if (func := self.function_dict.get(command)) is not None:
            logger.debug(
                f'[{self.module_name}] received command '
                f'"{command}", executing...'
            )
            func(*args)
        else:
            logger.warning(
                f'[{self.module_name}] does not recognise '
                f'"{command}" command.'
            )



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
