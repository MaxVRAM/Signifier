# This script will test the ability for the Pi to output a reliable multi-clip audio stream playback

# https://python-sounddevice.readthedocs.io/en/0.4.3/installation.html
# https://pysoundfile.readthedocs.io/en/latest/

# Using CLI tool "SoX" to batch-convert audio files to mono-sum the audio files. 

# The following commands create a mono mix-down of a stereo file:
# sox infile.wav outfile.wav remix 1,2
# sox infile.wav outfile.wav remix 1-2

# This was run in each Signifier audio directory:
# find * -name "*.wav" -print0 | while read -d $'\0' file; do sox "$file" m_"$file" remix 1,2; done

# sudo apt install libsndfile1

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
import threading


# Default globals for all audio output sounddevice functions
SAMPLERATE = 44100
sd.default.samplerate = SAMPLERATE
sd.default.device = 'default'
sd.default.channels = 1


# Sinewave test globals
AMPLITUDE = 0.2
FREQUENCY = 500

# Audio clip pooling
POOL_LIMIT = 10
inactive_clip_pool = []
active_clip_pool = []


class sound_object():
    def __init__(self, clip:sf.SoundFile, **kwargs) -> None:
        self.clip = clip
        self.currentSample = 0
        self.startSample = kwargs.get('startIndex', 0)
        self.volume = kwargs.get('volume', 0.2)
        self.pitch = kwargs.get('pitch', 1)

    def __str__(self) -> str:
        return f'{self.clip.name} | start index: {self.startSample}, playback index: {self.currentSample}, total samples: {self.clip.frames} volume: {self.volume}, pitch: {self.pitch}'

    


# TODO fill this buffer with existing array, then queue multiprocessor tasks to populate the next buffer
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
            print('Press Return to quit')
            print('#' * 80)
            input()
    except KeyboardInterrupt:
        sys.exit()
    except Exception as execption:
        print(f'Exiting program with exception: {execption}')
        sys.exit()
