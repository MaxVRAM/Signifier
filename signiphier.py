

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/




import logging, os, random, signal, sys, time
import pygame as pg
import sounddevice as sd
import pygame._sdl2 as sdl2

from clip_library import Library, Collection

# Initialise logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

os.environ["SDL_VIDEODRIVER"] = "dummy"

# Audio library defaults
VALID_EXT = ['.wav']
BASE_PATH = '/home/pi/Signifier/audio'

# Mixer defaults
DEFAULT_DEVICE = 'bcm2835'
#DEFAULT_DEVICE = 'default'
SAMPLE_RATE = 44100
SIZE = -16
NUM_CHANNELS = 2
BUFFER = 2048
MAX_PLAYTIME = 300000
DEFAULT_FADEIN = 2000
DEFAULT_FADEOUT = 3000

# Playback management
QUIET_LEVEL = 8
BUSY_LEVEL = 4
MIN_LOOP_LENGTH = 10
LOOP_RANGE = [0, 6]
CLIP_EVENT = pg.USEREVENT+1

active_pool = Collection(title='active')
inactive_pool = Collection(title='inactive')


def stop_all_clips(fade_time = DEFAULT_FADEOUT):
    """Fadeout and stop all active clips"""
    if pg.mixer.get_init():
        logger.info(f'Stopping audio clips with {fade_time}ms fade...')
        pg.mixer.fadeout(fade_time)

def get_fresh_channels(num_wanted:int):
    if pg.mixer.get_num_channels() != num_wanted:
        logger.info(f'Mixer has {pg.mixer.get_num_channels()} Channels but '
                    f'{num_wanted} are needed. Attempting to update mixer...')
        pg.mixer.set_num_channels(num_clips)
        logger.info(f'Mixer now has {pg.mixer.get_num_channels()} channels.')
        print()
    channels = [pg.mixer.Channel(i) for i in range(pg.mixer.get_num_channels())]
    return(list(enumerate(channels)))

def prepare_playback_engine():
    """Ensure audio driver exists and initialise the Pygame mixer."""
    import pygame._sdl2 as sdl2
    pg.init()
    is_capture = 0  # zero to request playback devices, non-zero to request recording devices
    num_devices = sdl2.get_num_audio_devices(is_capture)
    device_names = [str(sdl2.get_audio_device_name(i, is_capture), encoding="utf-8") for i in range(num_devices)]
    pg.quit()
    if device_names is None or len(device_names) == 0:
        logger.error(f'No audio devices detected!')
        exit_handler.shutdown()
    logger.debug(f'SDL2 detected the following audio devices: {device_names}')

    device = None
    for d in device_names:
        if DEFAULT_DEVICE in d:
            device = d
            break
    if device is None:
        logger.error(f'Expected audio device "{DEFAULT_DEVICE}" but was not detected on host!')
        exit_handler.shutdown()

    logger.info(f'"{device}" found on host and will be used for audio playback.')
    pg.mixer.pre_init(frequency=SAMPLE_RATE, size=SIZE, channels=1, buffer=BUFFER, devicename=device)
    pg.mixer.init()
    pg.mixer.set_num_channels(NUM_CHANNELS)
    pg.init()
    logger.debug(f'Audio mixer configured with device "{device} {pg.mixer.get_init()}"')
    print()


class ExitHandler:
    signals = { signal.SIGINT:'SIGINT', signal.SIGTERM:'SIGTERM' }
    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    def shutdown(self, *args):
        print()
        logger.info(f'Shutdown sequence started.')
        self.exiting = True
        # Replace this with a proper scheduler
        #activity_monitor.cancel()
        stop_all_clips()
        while pg.mixer.get_busy():
            time.sleep(0.1)
        pg.mixer.quit()
        logger.info("Signiphier shutdown complete.")
        print()
        sys.exit()


if __name__ == '__main__':
    print()
    logger.info('Prepare to be Signiphied!')
    print()
    exit_handler = ExitHandler()
    prepare_playback_engine()

    try:
        clip_library = Library(BASE_PATH, VALID_EXT)
    except OSError:
        exit_handler.shutdown()

    clip_library.init_library()

    # Get random collection from Library and initialise Clip pools
    collection = clip_library.get_collection()
    inactive_pool = collection.get_copy(title='inactive_pool')
    active_pool = collection.get_copy(title='active_pool')
    inactive_pool.clips = collection.get_distributed(12)
    num_clips = len(inactive_pool.clips)

    channels = get_fresh_channels(num_clips)
    inactive_pool.init_sounds(channels)
    print()

    # Initialise Channels and play
    for clip in inactive_pool.clips:
        clip.play(DEFAULT_FADEIN)



    # TODO Build basic automated clip playback manager!!!!



    # Main loop
    while True:
        for event in pg.event.get():
            if event.type == CLIP_EVENT:
                print(f'Clip ended: {event}')
        time.sleep(1)