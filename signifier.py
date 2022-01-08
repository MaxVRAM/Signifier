

#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/


# Displaying audio hardware
# aplay -l

# For resolving error 'ALSA lib pcm_direct.c:1846:(_snd_pcm_direct_get_slave_ipc_offset) Invalid value for card'
# sudo usermod -aG audio $USER





# Web UI monitoring/control schema:
#
# (*) indicates GUI-controllable variable
#
# Clip Manager:
#   - Base Path (str)
#   - Collections (list)
#   - Active Collection (str) (*)
#   - Default Volume (float) (*)
#   - Default Fade (list: fade-down, fade-up) ms (*)
#
# Collection:
#   - Title
#   - Path
#   - Audio Files (names) (list)
#   - Active Clips (int) (*)
#
# Inactive Pool (clips) (list) (*):
#   - Clip Objects (list)
# Active Pool (clips) (list) (*)
#   - Clip Objects (list)
#
# Clip Object:
#   - Root (str)
#   - Name (str) (filename)
#   - Full path (str)
#   - Length (float)
#   - Category (str)
#   - Looping (bool)
#   - Channel (int)
#   - Playing (bool) [play/stop] (*) (associated with inactive/active pools)
#   - Volume (float) (*)
#
# Mixer:
#   - Channels (list) (int)
#   - Volume (float) (*)
#   - Playing (bool) [play/stop] (*) (controls clip playing status)
#
# Composition Dynamics:
#   - Number of Clips (int) (*)
#   - Quiet Level (int) (*)
#   - Busy Level (int) (*)
#
# Scheduler Timers:
#   - Collection Timer (int) (*)
#   - Clip Timer (int) (*)
#   - Volume Timer (int) (*)



import logging, os, random, signal, sys, time, schedule
import pygame as pg

from clip_manager import ClipManager

# Initialise logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

os.environ["SDL_VIDEODRIVER"] = "dummy"

CLIP_EVENT = pg.USEREVENT+1

# TODO Create method to remotely manage this dictionary
config = {
    'audio':
    {
        'device':'bcm2835 Headphones, bcm2835 Headphones',
        'sample_rate':44100,
        'bit_size':-16,
        'buffer':2048
    },
    'composition':
    {
        'quiet_level':3,
        'busy_level':6,
        'max_playtime':60,
    },
    'clips':
    {
        'base_path':'/home/pi/Signifier/audio',
        'fail_retry_delay':5,
        'valid_extensions':['.wav'],
        'strict_distribution':False,
        'collection_size':12,
        'volume':0.5,
        'fade_in':2000,
        'fade_out':3000
    },
    'jobs':
    {
        'collection':96,
        'clips':16,
        'volume':2
    }
}

jobs = {'collection':96, 'clips':16, 'volume':2}
clip_manager = None


def update_clips():
    print()
    changed = set()
    changed = clip_manager.check_finished()
    if clip_manager.clips_playing() < config['composition']['quiet_level']:
        changed.update(clip_manager.play_clip())
    elif clip_manager.clips_playing() > config['composition']['busy_level']:
        changed.update(clip_manager.stop_clip())
    # Stop a random clip after a certain amount of time?
    print()

def modulate_volume():
    clip_manager.modulate_volumes()

def stop_random_clip():
    clip_manager.stop_clip()


def new_collection():
    print()
    set_jobs(False)
    pg.event.clear()
    stop_all_clips()
    while pg.mixer.get_busy():
        time.sleep(0.1)
    
    while (collection := clip_manager.select_collection("S06") is None):
        logger.info(f'Trying another collection in {config["clips"]["fail_retry_delay"]} seconds...')
        time.sleep(config["clips"]["fail_retry_delay"])
        new_collection()

    set_jobs(True)
    logger.info(f'NEW COLLECTION JOB DONE.')
    print()
    #update_clips()
    pg.event.clear()
    

def stop_all_clips(fade_time=config['clips']['fade_out']):
    """Fadeout and stop all active clips"""
    if pg.mixer.get_init():
        if pg.mixer.get_busy():
            logger.info(f'Stopping audio clips, with {fade_time}ms fade...')
            pg.mixer.fadeout(fade_time)



def set_jobs(state=True):
    """Add/remove jobs that control playback modulation."""
    print()
    modulation_jobs = schedule.get_jobs('modulation')
    if len(modulation_jobs) > 1:
        schedule.clear('modulation')
    if state:
        logger.debug(f'Scheduling modulation jobs...')
        schedule.every(config['jobs']['clips']).seconds.do(update_clips).tag('modulation')
        schedule.every(config['jobs']['volume']).seconds.do(modulate_volume).tag('modulation')
        logger.debug(f'Jobs: {schedule.get_jobs("modulation")}')


def audio_device_check() -> str:
    # TODO Create functional mechanism to find and test audio devices
    default_device = config['audio']['device']
    try:
        import pygame._sdl2 as sdl2
        pg.init()
        is_capture = 0  # zero to request playback devices, non-zero to request recording devices
        num_devices = sdl2.get_num_audio_devices(is_capture)
        device_names = [str(sdl2.get_audio_device_name(i, is_capture), encoding="utf-8") for i in range(num_devices)]
        pg.mixer.quit()
        pg.quit()
        if device_names is None or len(device_names) == 0:
            logger.warning(f'No audio devices detected by sdl2. Attempting to force default: "{default_device}"...')
            exit_handler.shutdown()
        logger.debug(f'SDL2 detected the following audio devices: {device_names}')
        device = None
        for d in device_names:
            if default_device in d:
                device = d
                break
        if device is None:
            logger.warning(f'Expected audio device "{default_device}" but was not detected by sdl2. '
                            f'Attempting to force driver...')
            exit_handler.shutdown()
        logger.info(f'"{device}" found on host and will be used for audio playback.')
        return default_device
    except Exception as exception:
        logger.warning(f'Error while using sdl2 to determine audio devices available on host. '
                        f'Attempting to force "{default_device}": {exception}')
        return default_device

def prepare_playback_engine():
    """Ensure audio driver exists and initialise the Pygame mixer."""
    device = audio_device_check()
    pg.mixer.pre_init(
        frequency=config['audio']['sample_rate'],
        size=config['audio']['bit_size'],
        channels=1,
        buffer=config['audio']['buffer'],
        devicename=device
        )
    pg.mixer.init()
    pg.init()
    logger.debug(f'Audio mixer successfully configured with device: "{device} {pg.mixer.get_init()}"')


class ExitHandler:
    signals = { signal.SIGINT:'SIGINT', signal.SIGTERM:'SIGTERM' }
    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
    def shutdown(self, *args):
        print()
        logger.info(f'Shutdown sequence started.')
        self.exiting = True
        schedule.clear()
        stop_all_clips()
        while pg.mixer.get_busy():
            time.sleep(0.1)
        pg.mixer.quit()
        logger.info("Signifier shutdown complete.")
        print()
        sys.exit()


if __name__ == '__main__':
    print()
    logger.info('Prepare to be Signified!!')
    print()

    exit_handler = ExitHandler()

    prepare_playback_engine()
    try:
        clip_manager = ClipManager(pg.mixer, config['clips'])
    except OSError:
        exit_handler.shutdown()

    clip_manager.init_library()

    new_collection()
    coll_job = schedule.every(config['jobs']['collection']).seconds.do(new_collection)
    #schedule.run_all()

    # Main loop
    while True:
        schedule.run_pending()
        for event in pg.event.get():
            if event.type == CLIP_EVENT:
                clip_manager.check_finished()
                if clip_manager.clips_playing() == 0:
                    update_clips()
                print(f'Clip ended: {event}')
        time.sleep(1)