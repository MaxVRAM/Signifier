

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

COLLECTION_TIMER = 96
CHANGE_TIMER = 32
MONITOR_TIMER = 16
VOLUME_TIMER = 2

clip_library = None

collection_schedule = Timer
mon_sched = Timer
clip_sched = Timer
vol_sched = Timer


def maintain_intensity():
    print()
    logger.info(f'RUNNING MONITORING JOB...')

    clip_library.check_finished()

    if clip_library.clips_playing() < QUIET_LEVEL:
        clip_library.play_clip()
    elif clip_library.clips_playing() > BUSY_LEVEL:
        clip_library.stop_clip()
    # Stop a random clip after a certain amount of time
    # Stop a random clip if there's still too many playing
    # Start new clip if there's not enough playing
    # Modulate playing clips' volume
    logger.info(f'MONITORING JOB DONE.')
    print()

def stop_random_clip():
    clip_library.stop_clip()
    logger.debug(f'RANDOM CLIP STOP JOB DONE.')

def modulate_volume():
    clip_library.modulate_volumes()
    logger.debug(f'VOLUME MODULAION JOB DONE.')



def new_collection():
    global mon_sched, clip_sched, vol_sched
    print()
    logger.info(f'RUNNING NEW COLLECTION JOB...')
    stop_all_clips()
    while pg.mixer.get_busy():
        time.sleep(0.1)



    clip_library.select_collection()
    clip_library.play_clip(num_clips=1)
    
    mon_sched = RepeatTimer(MONITOR_TIMER, maintain_intensity)
    mon_sched.start()
    clip_sched = RepeatTimer(CHANGE_TIMER, new_collection)
    clip_sched.start()
    vol_sched = RepeatTimer(VOLUME_TIMER, modulate_volume)
    vol_sched.start()

    logger.info(f'NEW COLLECTION JOB DONE.')
    print()

def stop_all_clips(fade_time=DEFAULT_FADE[0]):
    """Fadeout and stop all active clips"""
    if pg.mixer.get_init():
        if pg.mixer.get_busy():
            logger.info(f'Stopping audio clips, with {fade_time}ms fade...')
            pg.mixer.fadeout(fade_time)




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
        collection_schedule.cancel()
        mon_sched.cancel()
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
        clip_library = Library(pg.mixer, base_path=BASE_PATH, fade=DEFAULT_FADE)
    except OSError:
        exit_handler.shutdown()
    clip_library.init_library()

    new_collection()

    collection_schedule = RepeatTimer(COLLECTION_TIMER, new_collection)
    collection_schedule.start()

    # Main loop
    while True:
        for event in pg.event.get():
            if event.type == CLIP_EVENT:
                print(f'Clip ended: {event}')
        time.sleep(1)