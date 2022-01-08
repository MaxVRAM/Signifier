
#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/

# Displaying audio hardware:
# aplay -l

# Create a virtual audio loopback device:
# sudo modprobe snd-aloop

# For resolving error 'ALSA lib pcm_direct.c:1846:(_snd_pcm_direct_get_slave_ipc_offset) Invalid value for card'??
# sudo usermod -aG audio $USER
# Or you know... hardcode? :(


import logging, os, signal, sys, time, schedule
import pygame as pg
from signify.clip_manager import ClipManager

# Initialise logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

os.environ["SDL_VIDEODRIVER"] = "dummy"

clip_manager = None
CLIP_EVENT = pg.USEREVENT+1

# TODO Export as JSON and create method to remotely manage this dictionary
config = {
    'audio':
    {
        'device':'bcm2835 Headphones, bcm2835 Headphones',
        'sample_rate':44100,
        'bit_size':-16,
        'buffer':2048
    },
    'clip_manager':
    {
        'fail_retry_delay':5,
        'base_path':'/home/pi/Signifier/audio',
        'valid_extensions':['.wav'],
        'strict_distribution':False,
        'volume':0.5,
        'fade_in':2000,
        'fade_out':3000,
        'max_playtime':60,
        'categories':
        {
            'oneshot':{'threshold':0, 'is_loop':False, 'loop_range':[0,0]},
            'short':{'threshold':5, 'is_loop':False, 'loop_range':[2,6]},
            'medium':{'threshold':10, 'is_loop':True, 'loop_range':[0,0]},
            'loop':{'threshold':30, 'is_loop':True, 'loop_range':[0,0]}
        }
    },
    'jobs':
    {
        'collection':
        {
            'state':True,
            'timer':96,
            'parameters': {'size':12}
        },
        'composition':
        {
            'state':True,
            'timer':16,
            'parameters': {'quiet_level':3, 'busy_level':6}
        },
        'volume':
        {
            'state':True,
            'timer':2,
            'parameters': {'speed':5, 'weight':0}
        }
    }
}



#  _________                __                .__   
#  \_   ___ \  ____   _____/  |________  ____ |  |  
#  /    \  \/ /  _ \ /    \   __\_  __ \/  _ \|  |  
#  \     \___(  <_> )   |  \  |  |  | \(  <_> )  |__
#   \______  /\____/|___|  /__|  |__|   \____/|____/
#          \/            \/                         

def new_collection(pool_size=None):
    pool_size = config['jobs']['collection']['parameters']['size'] if pool_size is None else pool_size
    print()
    set_jobs(False)
    pg.event.clear()
    stop_all_clips()
    while pg.mixer.get_busy():
        time.sleep(0.1)
    while (collection := clip_manager.select_collection() is None):
        logger.info(f'Trying another collection in {config["clip_manager"]["fail_retry_delay"]} seconds...')
        time.sleep(config["clip_manager"]["fail_retry_delay"])
        new_collection()
    logger.info(f'NEW COLLECTION JOB DONE.')
    print()
    time.sleep(2)
    set_jobs(True)
    #update_clips()
    pg.event.clear()

def modulate_volume(speed=None, weight=None):
    """Randomly modulate the Channel volumes for all Clip(s) in the active pool.\n 
    - "speed=(int)" is the maximum volume jump per tick as a percentage of the total volume.
    1 is slow, 10 is very quick.\n - "weight=(float)" is a signed normalised float (-1.0 to 1.0)
    that weighs the random steps towards either direction."""
    speed = config['jobs']['volume']['parameters']['speed'] if speed is None else speed
    weight = config['jobs']['volume']['parameters']['weight'] if weight is None else weight
    clip_manager.modulate_volumes(speed, weight)

def update_clips(quiet_level=None, busy_level=None):
    """Ensure the clip manager is playing an appropriate number of clips,
    and tidy lingering completed clips from the active pool."""
    quiet_level = config['jobs']['composition']['parameters']['quiet_level'] if quiet_level is None else quiet_level
    busy_level = config['jobs']['composition']['parameters']['busy_level'] if busy_level is None else busy_level
    print()
    changed = set()
    changed = clip_manager.check_finished()
    if clip_manager.clips_playing() < quiet_level:
        changed.update(clip_manager.play_clip())
    elif clip_manager.clips_playing() > busy_level:
        changed.update(clip_manager.stop_clip())
    # Stop a random clip after a certain amount of time?
    print()

def stop_random_clip():
    clip_manager.stop_clip()

def stop_all_clips(fade_time=None):
    """Fadeout and stop all active clips"""
    fade_time = config['clip_manager']['fade_out'] if fade_time is None else fade_time
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
        schedule.every(config['jobs']['composition']['timer']).seconds.do(update_clips).tag('modulation')
        schedule.every(config['jobs']['volume']['timer']).seconds.do(modulate_volume).tag('modulation')
        logger.debug(f'Jobs: {schedule.get_jobs("modulation")}')


#    _________       __                
#   /   _____/ _____/  |_ __ ________  
#   \_____  \_/ __ \   __\  |  \____ \ 
#   /        \  ___/|  | |  |  /  |_> >
#  /_______  /\___  >__| |____/|   __/ 
#          \/     \/           |__|    

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
    print()

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



#     _____         .__        
#    /     \ _____  |__| ____  
#   /  \ /  \\__  \ |  |/    \ 
#  /    Y    \/ __ \|  |   |  \
#  \____|__  (____  /__|___|  /
#          \/     \/        \/ 

if __name__ == '__main__':
    print()
    logger.info('Prepare to be Signified!!')
    print()

    exit_handler = ExitHandler()

    prepare_playback_engine()
    try:
        clip_manager = ClipManager(config['clip_manager'], pg.mixer, CLIP_EVENT)
    except OSError:
        exit_handler.shutdown()

    clip_manager.init_library()

    new_collection()
    coll_job = schedule.every(config['jobs']['collection']['timer']).seconds.do(new_collection)
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