#!/usr/bin/env python3

#  __________                         __  .__                              .__     
#  \______   \_____    ______ _______/  |_|  |_________  ____  __ __  ____ |  |__  
#   |     ___/\__  \  /  ___//  ___/\   __\  |  \_  __ \/  _ \|  |  \/ ___\|  |  \ 
#   |    |     / __ \_\___ \ \___ \  |  | |   Y  \  | \(  <_> )  |  / /_/  >   Y  \
#   |____|    (____  /____  >____  > |__| |___|  /__|   \____/|____/\___  /|___|  /
#                  \/     \/     \/            \/                  /_____/      \/ 

"""Signify module to pass audio generated by the Clip Manager to the designated
audio output device. This module also produces analyise data on the incoming audio
stream, which can be sent to the arduino to modulate the LEDs."""

# sudo modprobe snd-aloop

import time
import queue
import random
import logging
import threading
import numpy as np
import sounddevice as sd


RHISTORY = 2
DEFAULT_CONF = {
    "enabled":True,
    "loopback_return":"Loopback: PCM (hw:1,1)",
    "hw_loop_output":"bcm2835 Headphones: - (hw:0,0)",
    "sample_rate":44100,
    "buffer":2048
    }

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
q = queue.Queue()
q.maxsize = 1
thread = None

runtime_config = DEFAULT_CONF
y_roll = np.random.rand(RHISTORY, runtime_config['buffer']) / 1e16
amplitude = 0

# class Stream():
#     def __init__(self, config=None, callback=None):
#         if config is None:
#             config = {
#                 "enabled":True,
#                 "loopback_return":"Loopback: PCM (hw:1,1)",
#                 "hw_loop_output":"bcm2835 Headphones: - (hw:0,0)",
#                 "sample_rate":44100,
#                 "buffer":2048}
#         self.active = True
#         self.loopback = config['loopback_return']
#         self.output = config['hw_loop_output']
#         self.sample_rate = config['sample_rate']
#         self.buffer = config['buffer']
#         self.y_roll = np.random.rand(RHISTORY, self.buffer) / 1e16
#         # self.sig_callback = callback
#         self.amplitude = 0
#         logger.debug('Audio passthrough module ready.')


def callback(indata, outdata, frames, time, status):
    global y_roll
    if status:
        print(status)
    if indata is not None:
        y_roll[:-1] = y_roll[1:]
        y_roll[-1, :] = np.copy(indata[0])
        y_data = np.concatenate(y_roll, axis=0).astype(np.float32)
        amp = np.max(np.abs(y_data))
        q.put(amp)
    outdata[:] = indata


def stream(input, output, rate):
    """Threaded routine that starts a PortAudio stream for piping Signifier\
    audio to the hardware audio output.\n
    Also executes audio analysis during the callback and updates audio\
    descriptors available from `get_descriptors()` function."""
    this_thread = threading.current_thread()
    logger.debug(f'This is "{this_thread.getName()}" thread saying hi!\
        Sample rate: {rate} | Input: {input} | Output: {output}.')
    with sd.Stream(
            device=(input,
            output),
            samplerate=rate,
            channels=1,
            callback=callback) as stream:
        while getattr(this_thread, "keep_going", True):
            sd.sleep(1)
        stream.stop()


def run(config=None):
    """Start the PulseAudio loopback stream to analyse the audio\
    and route it to the hardware output device.\n
    Supply the audio portion of `config.json`, i.e. `config['audio']`."""
    global runtime_config, y_roll, thread
    print(f'Streaming module detected the following devices:\n{sd.query_devices()}')
    if thread is None:
        print()
        logger.debug('Starting audio streaming thread...')
        if config is None:
            logger.warning('Audio streaming thread did not receive a configuration to use. Using default values.')
        else:
            runtime_config = config
        y_roll = np.random.rand(RHISTORY, runtime_config['buffer']) / 1e16
        thread = threading.Thread(
            target=stream, daemon=True, args=(
                runtime_config['loopback_return'],
                runtime_config['hw_loop_output'],
                runtime_config['sample_rate']))
        thread.setName('Audio Streaming')
        thread.start()
        logger.debug(f'({threading.enumerate()}) thread(s) now running.')
        print()


def stop():
    """Sets the streaming thread's `keep_going` attribute to `False`, which\
    should end the thread once the current buffer is done."""
    global thread
    if thread is not None:
        print()
        logger.info(f'Stopping "{thread.getName()}" ...')
        thread.keep_going = False
        thread.join()
        logger.info(f'"{thread.getName()}" finished.')
        print()
        thread = None

    

def get_descriptors() -> dict:
    """Return a dictionary with audio analysis values returned from thread."""
    global amplitude
    try:
        amplitude = q.get_nowait()
    except:
        pass
    return {"amplitude":amplitude}
        
        
        
        
        
# #!/usr/bin/env python3
# """Pass input directly to output.

# https://app.assembla.com/spaces/portaudio/git/source/master/test/patest_wire.c

# """
# import sounddevice as sd
# import numpy as np  # Make sure NumPy is loaded before it is used in the callback

# import queue

# q = queue.Queue()

# samples_per_frame = int(44100 / 20)
# RHISTORY = 2
# y_roll = np.random.rand(RHISTORY, samples_per_frame) / 1e16

# def callback(indata, outdata, frames, time, status):
#     if status:
#         print(status)
#     outdata[:] = indata
#     if indata is not None:
#         y_roll[:-1] = y_roll[1:]
#         y_roll[-1, :] = np.copy(indata[0])
#         y_data = np.concatenate(y_roll, axis=0).astype(np.float32)
#         vol = np.max(np.abs(y_data))
#         q.put(vol)

# try:
#     with sd.Stream(device=('Loopback: PCM (hw:3,1)', "bcm2835 Headphones: - (hw:0,0)"),
#                    channels=1, callback=callback):
#         print('#' * 80)
#         print('press Return to quit')
#         print('#' * 80)
#         while True:
#             print(q.get())
#         input()
# except Exception as e:
#     pass