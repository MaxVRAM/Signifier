# This script will test the ability for the Pi to output a reliable multi-clip audio stream playback

# https://python-sounddevice.readthedocs.io/en/0.4.3/installation.html
# python3 -m pip install sounddevice
# python3 -m pip install numpy
# sudo apt-get install libportaudio2

# Query valid audio devices:
#   - CLI: python3 -m sounddevice
#   - Python: sd.query_devices()

import numpy as np
import sounddevice as sd


# Default globals for all audio output sounddevice functions
SAMPLERATE = 44100
sd.default.samplerate = SAMPLERATE
sd.default.device = 'default'
sd.default.channels = 1


# Sinewave test globals
AMPLITUDE = 0.2
FREQUENCY = 500

# TODO make move to multiprocessor thread
def sine_wave(outdata, frames, time, status):
    """Basic sinewave buffer callback."""
    if status:
        print(status, file=sys.stderr)
    global start_idx
    t = (start_idx + np.arange(frames)) / SAMPLERATE
    t = t.reshape(-1, 1)
    outdata[:] = AMPLITUDE * np.sin(2 * np.pi * FREQUENCY * t)
    start_idx += frames


# A start index variable will possibly need to be defined for each audio source thread
start_idx = 0

# Main audio test code
try:
    # Currently this is only populating the OutputStream with a static sinewave callback.
    # Instead, this will be populated with a number dynamic buffers across several threads/processors,
    # each with their own content from an associated audio file and independant playback position.
    # These will sum into a primary RawOutputStream function.
    with sd.OutputStream(callback=sine_wave):
        print('#' * 80)
        print('press Return to quit')
        print('#' * 80)
        input()
except KeyboardInterrupt:
    parser.exit('')
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))