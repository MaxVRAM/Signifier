

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/



# Current approach is to have all base clip/Sound object functionality within the clip_library.py
# script. All high-level management, mixer.Channel objects, and event callbacks should exist
# within this main script. 


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

ACTIVE_POOL = Collection(logger, title='active')
INACTIVE_POOL = Collection(logger, title='inactive')


def play_clip(**kwargs) -> pg.mixer.Sound:
    """Start playback of a Sound object from a given set of Sound objects.\n
    Returns Sound object if successfully triggered, otherwise returns None."""

    global ACTIVE_POOL, INACTIVE_POOL

    if (channel := pg.mixer.find_channel()) is None:
        logger.warning(f'Cannot play audio clip. No available mixer channels.')
        return None

    clip = kwargs.get('clip', None)
    category = kwargs.get('category', None)

    # Load clip from Collection
    try:
        if clip is not None:
            logger.info(f'Trying specific clip {clip}.')
            new_clip = INACTIVE_POOL.specific_clip(clip)
        elif category is not None:
            logger.info(f'Trying random clip from category {category}.')
            new_clip = INACTIVE_POOL.clip_from_category(category)
        else:
            logger.info(f'Trying random clip from inactive pool.')
            new_clip = INACTIVE_POOL.clip_at_random()
    except Exception as exception:
        logger.error(f'Could not load clip with kwargs {kwargs}. Got exception: {exception}.')
        return None

    ACTIVE_POOL.add_clip(new_clip)

    # Define loop properties of new audio clip playback, set the end event, and return the clip
    num_loops = -1 if new_clip.looping else random.randint(LOOP_RANGE[0],LOOP_RANGE[1])
    channel.play(new_clip.sound, loops=num_loops, maxtime=MAX_PLAYTIME, fade_ms=DEFAULT_FADEIN)
    channel.set_endevent(CLIP_END_EVENT)
    logger.info(f'Playing sound {new_clip.name} with category {new_clip.category} at length {new_clip.length:.2f}, looping {num_loops} times on channel {channel}.')

    return new_clip


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

    # Load random Collection
    INACTIVE_POOL = clip_library.get_collection()

    play_clip()

    #active_pool.add(inactive_pool.pop(play_clip()))

    # Main loop
    while True:
        for event in pg.event.get():
            if event.type == CLIP_END_EVENT:
                print(f'Clip ended: {event}')
        time.sleep(1)