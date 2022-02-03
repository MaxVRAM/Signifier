
#    _________.__          ____ ___   __  .__.__          
#   /   _____/|__| ____   |    |   \_/  |_|__|  |   ______
#   \_____  \ |  |/ ___\  |    |   /\   __\  |  |  /  ___/
#   /        \|  / /_/  > |    |  /  |  | |  |  |__\___ \ 
#  /_______  /|__\___  /  |______/   |__| |__|____/____  >
#          \/   /_____/                                \/ 


from numpy import ndarray


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
    except:
        return ""
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

class ExpFilter:
    """
    Simple exponential smoothing filter.
    """
    def __init__(self, val=0.0, alpha_decay=0.5, alpha_rise=0.5):
        """Small rise / decay factors = more smoothing"""
        assert 0.0 < alpha_decay < 1.0
        assert 0.0 < alpha_rise < 1.0
        self.alpha_decay = alpha_decay
        self.alpha_rise = alpha_rise
        self.value = val

    def update(self, value):
        if isinstance(self.value, (list, ndarray, tuple)):
            alpha = value - self.value
            alpha[alpha > 0.0] = self.alpha_rise
            alpha[alpha <= 0.0] = self.alpha_decay
        else:
            alpha = self.alpha_rise if value > self.value else self.alpha_decay
        self.value = alpha * value + (1.0 - alpha) * self.value
        return self.value