

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/




import logging, os, random, signal, sys, time
import pygame as pg

from clip_library import Library

# Initialise logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

os.environ["SDL_VIDEODRIVER"] = "dummy"

# Audio library defaults
VALID_EXT = ['.wav']
BASE_PATH = '/home/pi/Signifier/audio'

# Mixer defaults
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


def import_clips(collection: Library.Collection) -> set:
    """Create pg.mixer.Sound objects from supplied Collection.\n
    Returns set of successfully imported audio clips."""
    audio_objects = set()

    for path in collection.get_paths():
        new_clip = pg.mixer.Sound(file=path)
        audio_objects.add(new_clip)

    logger.debug(f'Imported {len(audio_objects)} audio objects.')

    return audio_objects


def play_clip(audio_clip: pg.mixer.Sound) -> pg.mixer.Channel:
    """Start playback of an inactive pg.mixer.Sound object.\n
    Returns channel object if successfully triggered, otherwise returns None."""
    if (channel := pg.mixer.find_channel()) is None:
        logger.warning(f'Cannot play audio clip. No available mixer channels.')
        return None

    # Define loop properties of new audio clip playback and return the channel
    num_loops = -1 if audio_clip.get_length() < MIN_LOOP_LENGTH else random.randint(LOOP_RANGE[0],LOOP_RANGE[1])
    channel.play(audio_clip, loops=num_loops, maxtime=MAX_PLAYTIME, fade_ms=DEFAULT_FADEIN)
    clip_done_event = pg.event.Event(CLIP_END_EVENT, chan=channel)
    channel.set_endevent(clip_done_event.type)
    pg.event.post(clip_done_event)
    logger.info(f'Playing sound with length {audio_clip.get_length():.2f}, looping {num_loops} times on channel {channel}.')
    return channel


def unload_busy(fade_time = DEFAULT_FADEOUT):
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
        unload_busy()
        logger.info("Finished.")
        print()
        sys.exit()


if __name__ == '__main__':
    print()
    logger.info('Prepare to be Signiphied!')
    active_pool = []
    inactive_pool = []

    exit_handler = ExitHandler()

    # On testing equipment, 'bcm2835 Headphones, bcm2835 Headphones' is the correct devicename
    # Will need to test this on production before prototype submission to make sure this is a neat/safe solution
    pg.mixer.pre_init(frequency=SAMPLE_RATE, size=SIZE, channels=1, buffer=BUFFER, devicename='bcm2835 Headphones, bcm2835 Headphones')
    pg.mixer.init()
    pg.init()
    logger.debug(f'Audio mixer loaded: {pg.mixer.get_init()}')

    # Initialise audio library and select collection at random
    try:
        clip_library = Library(BASE_PATH, VALID_EXT, logger)
    except OSError:
        logger.fatal(f'Invalid root path for library: {BASE_PATH}.')
        exit_handler.shutdown()
        

    clip_library.init_library()
    collection = clip_library.get_collection()
    inactive_pool = import_clips(collection)

    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))


    while True:
        for event in pg.event.get():
            if event.type == CLIP_END_EVENT:
                print(f'Clip ended: {event}   on channel {event.chan}')

    # while pg.mixer.get_busy():
    #     time.sleep(0.001)






# sudo apt-get install libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0
# ^^ this might not be the corerct answer

# Trying instead this:
# sudo apt-get install libsdl1.2-dev libsdl-image1.2-dev libsdl-mixer1.2-dev libsdl-ttf2.0-dev
# From here: https://github.com/br007/Hot-in-Hurr/issues/1

# Producing audio device list:

# import pygame._sdl2 as sdl2
# pg.init()
# is_capture = 0  # zero to request playback devices, non-zero to request recording devices
# num = sdl2.get_num_audio_devices(is_capture)
# names = [str(sdl2.get_audio_device_name(i, is_capture), encoding="utf-8") for i in range(num)]
# print("\n".join(names))
# pg.quit()