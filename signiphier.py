

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/




import logging, os, random, signal, sys, time, copy
import pygame as pg
from threading import Timer

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
MAX_PLAYTIME = 60
DEFAULT_FADE = [3000, 2000] # fade out / fade in

# Playback management
NUM_CLIPS = 12
QUIET_LEVEL = 3
BUSY_LEVEL = 6
CLIP_EVENT = pg.USEREVENT+1

COLLECTION_TIMER = 600
MONITOR_TIMER = 30


clip_library = None
active_pool = Collection
inactive_pool = None



def monitor_playback():
    global active_pool, inactive_pool
    print()
    logger.info(f'RUNNING MONITORING JOB.')
    finished_clips = set()
    finished_clips.update(active_pool.get_finished())
    for clip in active_pool.clips:
        if time.time() - clip.started > MAX_PLAYTIME and clip.channel.get_busy() == True:
            logging.debug(f'{clip.name} has been playing long enough. Telling it to stop.')
            finished_clips.add(clip.stop())
            break

    # Now balance things out
    if len(active_pool.clips) > BUSY_LEVEL:
        clip = set(active_pool.get_clip(keep=True))
        finished_clips.add(clip.stop())

    if len(active_pool.clips) - len(finished_clips) < QUIET_LEVEL:
        active_pool.push_clip(inactive_pool.play_clip(num_clips=1))

    logging.debug(f'Removing {len(finished_clips)} finished clips from active_pool.')
    inactive_pool.push_clip(active_pool.pull_clip(finished_clips, keep=False))
    print()


def start_new_collection(num_clips=NUM_CLIPS):
    global clip_library, active_pool, inactive_pool
    print()
    print()
    logger.info(f'RUNNING NEW COLLECTION JOB.')
    stop_all_clips()
    while pg.mixer.get_busy():
        time.sleep(0.1)

    active_pool = None
    inactive_pool = None

    collection = copy.deepcopy(clip_library.select_collection())
    collection.init_clips()
    
    active_pool = collection.get_copy(title='active_pool')
    inactive_pool = collection.get_copy(title='inactive_pool')
    inactive_pool.clips = collection.get_distributed(num_clips)

    num_clips = len(inactive_pool.clips)
    channels = get_fresh_channels(num_clips)
    inactive_pool.init_sounds(channels)
    active_pool.push_clip(inactive_pool.play_clip(num_clips=1))

    print()
    logger.info(f'Finished new Collection playback job.')
    print()



def stop_all_clips(fade_time=DEFAULT_FADE[0]):
    """Fadeout and stop all active clips"""
    if pg.mixer.get_init():
        logger.info(f'Stopping audio clips with {fade_time}ms fade...')
        pg.mixer.fadeout(fade_time)

def get_fresh_channels(num_wanted:int):
    if pg.mixer.get_num_channels() != num_wanted:
        logger.info(f'Mixer has {pg.mixer.get_num_channels()} Channels but '
                    f'{num_wanted} are needed. Attempting to update mixer...')
        pg.mixer.set_num_channels(num_wanted)
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


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

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
        logger.info("Clearing schedulers.")
        new_collection_schedule.cancel()
        monitor_schedule.cancel()
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
        clip_library = Library(base_path=BASE_PATH, fade=DEFAULT_FADE)
    except OSError:
        exit_handler.shutdown()
    clip_library.init_library()

    start_new_collection()

    new_collection_schedule = RepeatTimer(COLLECTION_TIMER, start_new_collection)
    new_collection_schedule.start()
    
    monitor_schedule = RepeatTimer(MONITOR_TIMER, monitor_playback)
    monitor_schedule.start()


    # Main loop
    while True:
        for event in pg.event.get():
            if event.type == CLIP_EVENT:
                print(f'Clip ended: {event}')
        time.sleep(1)