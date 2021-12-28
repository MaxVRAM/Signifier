

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/




import logging, os, random, signal, sys, time

import pygame as pg

from clip_library import Library, Collection

# Initialise logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

os.environ["SDL_VIDEODRIVER"] = "dummy"

# Audio library defaults
VALID_EXT = ['.wav']
BASE_PATH = '/home/pi/Signifier/audio'

# Mixer defaults
DEFAULT_DEVICE = 'bcm2835 Headphones, bcm2835 Headphones'
SAMPLE_RATE = 44100
SIZE = -16
CHANNELS = 20
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



def play_clip(collection: Collection) -> pg.mixer.Sound:
    """Start playback of a Sound object from a given set of Sound objects.\n
    Returns Sound object if successfully triggered, otherwise returns None."""
    if (channel := pg.mixer.find_channel()) is None:
        logger.warning(f'Cannot play audio clip. No available mixer channels.')
        return None

    # TODO Add ability to select specific Sound object from set

    sound_object = random.choice(tuple(collection))
    # Define loop properties of new audio clip playback and return the channel
    num_loops = -1 if sound_object.get_length() < MIN_LOOP_LENGTH else random.randint(LOOP_RANGE[0],LOOP_RANGE[1])
    channel.play(sound_object, loops=num_loops, maxtime=MAX_PLAYTIME, fade_ms=DEFAULT_FADEIN)
    channel.set_endevent(CLIP_END_EVENT)
    #pg.event.post(clip_done_event)
    logger.info(f'Playing sound with length {sound_object.get_length():.2f}, looping {num_loops} times on channel {channel}.')
    return sound_object


def stop_all_clips(fade_time = DEFAULT_FADEOUT):
    """Fadeout and stop all active clips"""
    pg.mixer.fadeout(fade_time)


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
    exit_handler = ExitHandler()

    active_pool = {}
    inactive_pool = {}
    pg.mixer.pre_init(frequency=SAMPLE_RATE, size=SIZE, channels=1, buffer=BUFFER, devicename=DEFAULT_DEVICE)
    pg.mixer.init()
    pg.init()
    logger.debug(f'Audio mixer loaded: {pg.mixer.get_init()}')

    # Initialise audio library
    try:
        clip_library = Library(BASE_PATH, VALID_EXT, logger)
    except OSError:
        logger.fatal(f'Invalid root path for library: {BASE_PATH}.')
        exit_handler.shutdown()
    clip_library.init_library()

    # Load clips
    collection = clip_library.get_collection()
    print(collection)
    inactive_pool = collection.clips


    #active_pool.add(inactive_pool.pop(play_clip()))

    # Main loop
    while True:
        for event in pg.event.get():
            if event.type == CLIP_END_EVENT:
                print(f'Clip ended: {event}')
        time.sleep(1)