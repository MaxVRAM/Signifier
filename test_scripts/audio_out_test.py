# This script will test the ability for the Pi to output a reliable multi-clip audio stream playback

# https://python-sounddevice.readthedocs.io/en/0.4.3/installation.html
# python3 -m pip install sounddevice
# python3 -m pip install SoundFile
# python3 -m pip install numpy
# sudo apt-get install libportaudio2

# Query valid audio devices:
#   - CLI: python3 -m sounddevice
#   - Python: sd.query_devices()

import sys
import numpy as np
import sounddevice as sd
import soundfile as sf

# Default globals for all audio output sounddevice functions
SAMPLERATE = 44100
sd.default.samplerate = SAMPLERATE
sd.default.device = 'default'
sd.default.channels = 1


# Sinewave test globals
AMPLITUDE = 0.2
FREQUENCY = 500

sound_pool = []

class sound_object():
    def __init__(self, **kwargs) -> None:
        index = 0
        volume = 0
        pitch = 500

        if 'volume' in kwargs:
            volume = kwargs.volume
        if 'pitch' in kwargs:
            pitch = kwargs.pitch        


# TODO make this spawn multiple threads of audio file inputs
def fill_buffer(outdata, frames, time, status):
    """Basic sinewave buffer callback."""
    if status:
        print(status, file=sys.stderr)
    global start_idx
    t = (start_idx + np.arange(frames)) / SAMPLERATE
    t = t.reshape(-1, 1)
    outdata[:] = AMPLITUDE * np.sin(2 * np.pi * FREQUENCY * t)
    start_idx += frames
    print(f'buffer sample size: {len(t)}    frames: {frames}    start_idx: {start_idx}')


# Main audio test code
if __name__ == '__main__':
    # A start index variable will possibly need to be defined for each audio source thread
    start_idx = 0
    try:
        with sd.OutputStream(callback=fill_buffer):
            print('#' * 80)
            print('press Return to quit')
            print('#' * 80)
            input()
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        print(f'Exiting program with exception: {e}')
        sys.exit()
