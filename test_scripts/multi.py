# Here's the write up for this example code
# https://www.esologic.com/multi-audio/

"""
multi.py, uses the sounddevice library to play multiple audio files to multiple output devices at the same time
Written by Devon Bray (dev@esologic.com)
"""
 
import sounddevice as sd
import soundfile
import threading
import os
from pathlib import Path
 

DATA_TYPE = "float32"
AUDIO_DIR = 'audio/mono/S10'
PARENT_DIR = Path(os.getcwd()).parent.absolute()
AUDIO_PATH = os.path.join(PARENT_DIR, AUDIO_DIR)



def load_audio(path):
    """
    Get the in-memory version of a given path to a wav file
    :param path: wav file to be loaded
    :return: audio_data, a 2D numpy array
    """
 
    audio_data, _ = soundfile.read(path, dtype=DATA_TYPE)
    return audio_data
 
 
def get_device_number_if_usb_soundcard(index_info):
    """
    Given a device dict, return True if the device is one of our USB sound cards and False if otherwise
    :param index_info: a device info dict from PyAudio.
    :return: True if usb sound card, False if otherwise
    """
 
    index, info = index_info
 
    if "default" in info["name"]:
        return index
    return False
 
 
def play_wav_on_index(audio_data, stream_object):
    """
    Play an audio file given as the result of `load_sound_file_into_memory`
    :param audio_data: A two-dimensional NumPy array
    :param stream_object: a sounddevice.OutputStream object that will immediately start playing any data written to it.
    :return: None, returns when the data has all been consumed
    """
 
    stream_object.write(audio_data)
 
 
def create_stream():
    """
    Create an sounddevice.OutputStream that writes to the device specified by index that is ready to be written to.
    You can immediately call `write` on this object with data and it will play on the device.
    :param index: the device index of the audio device to write to
    :return: a started sounddevice.OutputStream object ready to be written to
    """
 
    output = sd.OutputStream(
        # device=index,
        # channels=1,
        # dtype=DATA_TYPE
    )
    output.start()
    return output
 
 
if __name__ == "__main__":
 
    # Grab files
    # Start threads for all available audio clips at once
    # Wait until they finish then join them
    # Exit


    sd.default.samplerate = 44100
    sd.default.device = 'default'
    sd.default.channels = 1
    sd.default.dtype = 'float32'

    if sd.default.device is not None:

        def get_audio_clips(path):
            """
            Grab unhidden .wav files
            """
            return str(path).endswith(".wav") and (not str(path).startswith("."))
    
        audio_clip_paths = [
            os.path.join(AUDIO_PATH, path) for path in sorted(filter(lambda path: get_audio_clips(path), os.listdir(AUDIO_PATH)))
        ]
    
        print("Loading the following .wav files into memory:", audio_clip_paths)
        files = [load_audio(path) for path in audio_clip_paths]

        # print("Looking for audio device.")
        # usb_sound_card_indices = list(filter(lambda x: x is not False,
        #                                     map(get_device_number_if_usb_soundcard,
        #                                         [index_info for index_info in enumerate(sd.query_devices())])))
        # print("Discovered the following usb sound devices", usb_sound_card_indices)

    
        streams = [create_stream() for index in audio_clip_paths]
    
        running = True
    
        if not len(streams) > 0:
            running = False
            print("No audio devices found, stopping")
    
        if not len(files) > 0:
            running = False
            print("No sound files found, stopping")
    
        while running:
    
            print("Playing files")
    
            threads = [threading.Thread(target=play_wav_on_index, args=[file_path, stream])
                    for file_path, stream in zip(files, streams)]

            
            try:
                for thread in threads:
                    thread.start()
    
                for thread in threads:
                    print(f'Waiting for device {thread.native_id} to finish')
                    thread.join()
    
            except KeyboardInterrupt:
                running = False
                print("Stopping stream")
                for stream in streams:
                    stream.abort(ignore_errors=True)
                    stream.close()
                print("Streams stopped")

    else:
        print("Could not find audio device. Exiting...")
    print("Bye.")