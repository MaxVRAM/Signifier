

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/




import logging, os, random, signal, sys, time
import pygame as pg
import sounddevice as sd

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
#DEFAULT_DEVICE = 'bcm2835 Headphones, bcm2835 Headphones'
DEFAULT_DEVICE = 'default'
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
    pg.mixer.fadeout(fade_time)

def prepare_playback_engine():
    """Ensure the expected audio driver exists, initialises the Pygame mixer, and assigns"""
    audio_devices = sd.query_devices()
    if audio_devices is None or len(audio_devices) == 0:
        logger.error(f'No audio devices detected!')
        exit_handler.shutdown()
    logger.debug(f'Detected the following audio devices:')
    device = None
    for d in audio_devices:
        if d['name'] == DEFAULT_DEVICE:
            device = d
            logger.debug(f' *** {d}')
        else:
            logger.debug(f'     {d}')

    if device is None:
        logger.error(f'Expected audio device [{DEFAULT_DEVICE}] but it was not detected on host!')
        exit_handler.shutdown()

    logger.info(f'[{device["name"]}] found on host and will be used for audio playback.')

    pg.mixer.pre_init(frequency=SAMPLE_RATE, size=SIZE, channels=1, buffer=BUFFER, devicename=DEFAULT_DEVICE)
    pg.mixer.init()
    pg.init()
    for i in range(NUM_CHANNELS):
        channels[i] = pg.mixer.Channel(i)
    logger.debug(f'Audio mixer configured with device [{DEFAULT_DEVICE} {pg.mixer.get_init()}] '
                 f'and has {pg.mixer.get_num_channels()} playback channels.')


class ExitHandler:
    signals = { signal.SIGINT:'SIGINT', signal.SIGTERM:'SIGTERM' }
    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    def shutdown(self, *args):
        print()
        self.exiting = True
        logger.info('Stopping scheduler and unloading audio clips.')
        # Replace this with a proper scheduler
        #activity_monitor.cancel()
        stop_all_clips()
        pg.mixer.quit()
        logger.info("Finished.")
        print()
        sys.exit()


if __name__ == '__main__':
    print()
    logger.info('Prepare to be Signiphied!')
    print()
    exit_handler = ExitHandler()
    prepare_playback_engine()


    # Initialise audio library
    try:
        clip_library = Library(BASE_PATH, VALID_EXT)
    except AssertionError:
        logger.fatal(f'Invalid root path for library: {BASE_PATH}.')
        exit_handler.shutdown()

    clip_library.init_library()

    # Load random Collection
    collection = clip_library.get_collection()
    clip_selection = collection.get_distributed()

    inactive_pool = collection.get_copy(title='inactive', clip_set=clip_selection)
    active_pool = collection.get_copy(title='active', clip_set=set())
    inactive_pool.initialise_sounds()
    print()



    # Main loop
    while True:
        for event in pg.event.get():
            if event.type == CLIP_END_EVENT:
                print(f'Clip ended: {event}')
        time.sleep(1)