

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
NUM_CHANNELS = 20
BUFFER = 2048
MAX_PLAYTIME = 300000
DEFAULT_FADEIN = 1000
DEFAULT_FADEOUT = 1000

# Playback management
QUIET_LEVEL = 8
BUSY_LEVEL = 4
MIN_LOOP_LENGTH = 10
LOOP_RANGE = [0, 6]
CLIP_END_EVENT = pg.USEREVENT+1

active_pool = Collection(title='active')
inactive_pool = Collection(title='inactive')
channels = []


def play_clip(name=None, category=None, num_clips=1) -> pg.mixer.Sound:
    """Start clip playback from a given set of Sound objects.
    Return Sound object if successfully triggered, otherwise returns None.
    Use arguments to specify selection, otherwise a random clip will be played:\n
    - "name=(str)" for a specific clip (overrides other arguments)\n
    - "category=(int)" for a random clip from specific category\n
    - "num_clips=(int)" for a specific amount of clips.
    """

    global active_pool, inactive_pool

    if (channel := pg.mixer.find_channel()) is None:
        pg.mixer.get_busy()
        logger.warning(f'Cannot play audio clip. No available mixer channels.')
        return None
    
    if (clip := inactive_pool.get_clip(name=name, category=category, num_clips=num_clips)) is None:
        return None

    # Define loop properties of new audio clip playback, set the end event, and return the clip
    num_loops = -1 if clip.looping else random.randint(LOOP_RANGE[0],LOOP_RANGE[1])
    channel.play(clip.sound, loops=num_loops, maxtime=MAX_PLAYTIME, fade_ms=DEFAULT_FADEIN)
    channel.set_endevent(CLIP_END_EVENT)
    logger.info(f'Started clip plackback: {active_pool.push_clip(clip)} looping {num_loops}')

    return clip


def stop_all_clips(fade_time = DEFAULT_FADEOUT):
    """Fadeout and stop all active clips"""
    if pg.mixer.get_init():
        logger.info(f'Stopping audio clips with {fade_time}ms fade...')
        pg.mixer.fadeout(fade_time)

def prepare_playback_engine():
    """Ensure the expected audio driver exists and initialises the Pygame mixer."""
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
    inactive_pool.clips = collection.get_distributed()
    inactive_pool.initialise_sounds()
    print()

    # Initialise Channels and play
    i = 0
    for clip in inactive_pool.clips:
        clip.set_channel(i, pg.mixer.Channel(i))
        clip.play()
        i += 1


    # Main loop
    while True:
        for event in pg.event.get():
            if event.type == CLIP_END_EVENT:
                print(f'Clip ended: {event}')
        time.sleep(1)