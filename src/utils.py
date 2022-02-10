
#    _________.__          ____ ___   __  .__.__          
#   /   _____/|__| ____   |    |   \_/  |_|__|  |   ______
#   \_____  \ |  |/ ___\  |    |   /\   __\  |  |  /  ___/
#   /        \|  / /_/  > |    |  /  |  | |  |  |__\___ \ 
#  /_______  /|__\___  /  |______/   |__| |__|____/____  >
#          \/   /_____/                                \/ 


import os
import logging

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
    if 'clamp' in args:
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
    return pow(10, float(db)/100)


def validate_library(config_file:dict) -> bool:
    """
    Utility for checking validity of audio clip library.
    Returns `False` unless paths are valid and audio clips exist.
    """
    audio_path = config_file['base_path']
    print()
    if not os.path.isdir(audio_path):
        logger.critical(f'Invalid root path for library: {audio_path}.')
        logger.info(f'Ensure audio library exists or check path in config.')
        return False
    else:
        collections = [f.path for f in os.scandir(audio_path) if f.is_dir()]
        if len(collections) == 0:
            logger.critical(f'No collections found in audio library: {audio_path}')
            logger.info(f'Ensure audio library exists or check path in config.')
            return False
        else:
            logger.info(f'Found {len(collections)} audio clip '
                        f'collection{plural(collections)}.')
            clips = []
            for c in collections:
                for f in os.listdir(c):
                    if os.path.splitext(f)[1][1:] in config_file['valid_extensions']:
                        clips.append(f)
            if len(clips) == 0:
                logger.critical(
                    f'No valid clips found in library with extention '
                    f'{config_file["valid_extensions"]}.')
                return False
            logger.info(f'[{len(clips)}] clip{plural(clips)} found in library.')
            return True


class ExponentialFilter:
    # https://gitlab.zenairo.6 com/led-projects/dancyPi-audio-reactive-led/-/raw/262206d35962b2383f2649d726ff9bc513095ec7/python/dsp.py
    """
    Simple exponential smoothing filter
    """
    def __init__(self, val=0.0, alpha_decay=0.5, alpha_rise=0.5):
        """
        Small rise / decay factors = more smoothing
        """
        assert 0.0 < alpha_decay < 1.0, 'Invalid decay smoothing factor'
        assert 0.0 < alpha_rise < 1.0, 'Invalid rise smoothing factor'
        self.alpha_decay = alpha_decay
        self.alpha_rise = alpha_rise
        self.value = val

    def update(self, value):
        """
        Applies smoothing function between new value in argument to the
        existing one and returns result. 
        """
        if not isinstance(self.value, (int, long, float)):
            alpha = value - self.value
            alpha[alpha > 0.0] = self.alpha_rise
            alpha[alpha <= 0.0] = self.alpha_decay
        else:
            alpha = self.alpha_rise if value > self.value else self.alpha_decay
        self.value = alpha * value + (1.0 - alpha) * self.value
        return self.value

