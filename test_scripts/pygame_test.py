

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |φ> >   Y  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/




import logging, os, random, signal, sys, time
import pygame as pg

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)


# Audio clip library
VALID_EXT = ['.wav']
BASE_PATH = '/home/pi/Signifier/audio/mono'
CLIP_LIBRARY = []


SAMPLE_RATE = 44100
SIZE = -16
CHANNELS = 20
BUFFER = 2048


DEFAULT_FADEIN = 1000
DEFAULT_FADEOUT = 1000

# Playback management
QUIET_LEVEL = 8
BUSY_LEVEL = 4
MIN_LOOP_LENGTH = 10
LOOP_RANGE = [0, 6]

# Need to unpack this - I suspect this is a hack to maintain the playback beyond the events 
CLIP_DONE = pg.USEREVENT+1


def init_library(path: str) -> list:
    """Return a list of dicts, each containing a root path and set of wav files for every subdirectory."""
    library = []
    for (root, dirs, files) in sorted(os.walk(path)):
        audio_clips = set()
        # Only inlclude valid file extensions
        for f in files:
            if os.path.splitext(f)[1] in VALID_EXT:
                audio_clips.add(f)
        # If the clip set is not empty, add it to the library
        if len(audio_clips) > 0:
            library.append({'path':root, 'clips':audio_clips})
            logger.debug(f'[{len(library)-1}] {root} added to clip library with {len(audio_clips)} audio files.')

    return library


def get_collection(clip_library, index=None) -> set:
    """Return a set of absolute audio file paths from a collection within the library.\n
    Will randomly select a set if no index argument is supplied."""
    clip_paths = set()

    try:
        collection = clip_library[index]
    except TypeError:
        logger.debug('Collection index not supplied or is invalid. One will be randomly selected.')
    except IndexError:
        logger.error('Supplied collection index is out of range. One will be randomly selected.')
    finally:
        collection = random.choice(clip_library)
    
    for clip in collection['clips']:
        clip_paths.add(os.path.join(collection['path'], clip))

    logger.debug(f'Collection {collection["path"]} selected containing {len(clip_paths)} clips.')

    return clip_paths


def import_clips(clip_paths: set) -> set:
    """Create pg.mixer.Sound objects from supplied set of audio file paths.\n
    Returns set of successfully imported audio clips."""
    audio_objects = set()

    for path in clip_paths:
        new_clip = pg.mixer.Sound(file=path)
        audio_objects.add(new_clip)

    logger.debug(f'Imported {len(audio_objects)} audio objects.')

    return audio_objects


def play_clip(audio_clip: pg.mixer.Sound) -> pg.mixer.Channel:
    """Start playback of an inactive pg.mixer.Sound object.\n
    Returns designated channel object if successfully triggered, otherwise returns None."""
    if pg.mixer.find_channel() is None:
        logger.warning(f'Cannot play audio clip. No available mixer channels.')
        return None

    # Define loop properties of new audio clip playback and return the channel
    num_loop = -1 if audio_clip.get_length() < MIN_LOOP_LENGTH else random.randint(LOOP_RANGE[0],LOOP_RANGE[1])
    print(f'Playing sound with length {audio_clip.get_length()}, {num_loop} times.')
    audio_clip.set_volume(0.1)
    channel = audio_clip.play(loops=num_loop, fade_ms=DEFAULT_FADEIN)
    return channel


def unload_busy(fade_time = DEFAULT_FADEOUT):
    """Fadeout and stop all active clips"""
    pg.mixer.fadeout(fade_time)



class ExitHandler:
    signals = { signal.SIGINT: 'SIGINT',signal.SIGTERM: 'SIGTERM' }

    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def shutdown(self, signum, frame):
        self.exiting = True
        logger.info('Stopping scheduler and unloading audio clips.')
        # Replace this with a proper scheduler
        #activity_monitor.cancel()
        unload_busy()
        logger.info("Finihsed.")
        sys.exit()


if __name__ == '__main__':
    active_pool = []
    inactive_pool = []

    # On testing equipment, 'bcm2835 Headphones, bcm2835 Headphones' is the correct devicename
    # Will need to test this on production before prototype submission to make sure there is a neat solution
    pg.mixer.pre_init(frequency=SAMPLE_RATE, size=SIZE, channels=1, buffer=BUFFER, devicename='bcm2835 Headphones, bcm2835 Headphones')
    pg.mixer.init()
    logger.debug(f'Audio mixer loaded: {pg.mixer.get_init()}')

    CLIP_LIBRARY = init_library(BASE_PATH)

    current_collection = get_collection(CLIP_LIBRARY)
    inactive_pool = import_clips(current_collection)
    print(f'Inactive pool now contains {len(inactive_pool)} audio clips.')

    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))
    play_clip(random.choice(tuple(inactive_pool)))


    # Playback is working excellently!!
    # Crunkiness was from defining tons of channels instead of 1 for mixer output

    # Next steps for project:

    # TEST:
    #   A) Move Sound.play() over to pg.mixer.Channel(ch).play(sound)
    #       This might solve the problem with volume maxing out and Channel number crunkiness

    # Basic playback:
    #   1) Create proper exit function and audio clip playback length limiting
    #   2) add function to move newly played clip from inactive_pool to active_pool
    #   3) differentiate various clip types (short, med, long, loop, etc)
    #   4) replate original Signifier audio playback
    #   5) use noise to modulate channel volumes
    # Modulated playback:
    #   6) Create server of some kind. Accepting JSON would be ideal, for key/value control.
    #   7) Affix server responses to functions
    #   8) Create documentation for server commands
    # LED reactivity:
    #   9) Add function to analyise channel output amplitudes
    #   10) Test pyserial to Arduino functionality
    #   11) Create simple LED brightness reactivity based on audio output


    exit_handler = ExitHandler()
    while True:
        for event in pg.event.get():
            if event.type == CLIP_DONE:
                print(f'EVENT: {event}')

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