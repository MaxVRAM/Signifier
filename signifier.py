
#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/


# ARDUINO SCRIPT CURRENTLY LOADED:
# - purple_volume.ino
#
# STATUS: Serial working, but no brightness change. Need to debug.



# Displaying audio hardware:
# aplay -l

# Create a virtual audio loopback device:
# sudo modprobe snd-aloop

# For resolving error 'ALSA lib pcm_direct.c:1846:(_snd_pcm_direct_get_slave_ipc_offset) Invalid value for card'??
# sudo usermod -aG audio $USER
# Or you know... hardcode? :(

import logging, os, signal, sys, time, schedule, json, random
import pygame as pg
from signify.clip_manager import ClipManager
from pySerialTransfer import pySerialTransfer as txfer

# Initialise logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

os.environ["SDL_VIDEODRIVER"] = "dummy"

arduino_link = None
clip_manager = None
CLIP_EVENT = pg.USEREVENT+1

CONFIG_FILE = 'config.json'
with open(CONFIG_FILE) as c:
    config = json.load(c)


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
        arduino_link.close()
        schedule.clear()
        stop_all_clips()
        while pg.mixer.get_busy():
            time.sleep(0.1)
        pg.mixer.quit()
        logger.info("Signifier shutdown complete.")
        print()
        sys.exit()




def arduino_send_test(value:float):
        sendSize = arduino_link.tx_obj(value)
        print(f'Sending Arduino: {value}')
        print(f'Success: {arduino_link.send(sendSize)}')

        # send_size = 0
        # ###################################################################
        # # Send a float
        # ###################################################################
        # float_ = value
        # float_size = arduino_link.tx_obj(float_, send_size) - send_size
        # send_size += float_size
        
        # ###################################################################
        # # Transmit all the data to send in a single packet
        # ###################################################################
        # arduino_link.send(send_size)




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

    # Arduino setup
    arduino_link = txfer.SerialTransfer('/dev/ttyACM0')
    arduino_link.open()

    prepare_playback_engine()
    try:
        clip_manager = ClipManager(config['clip_manager'], pg.mixer, CLIP_EVENT)
    except OSError:
        exit_handler.shutdown()

    clip_manager.init_library()
    new_collection()

    time.sleep(4) # allow some time for the Arduino to completely reset

    coll_job = schedule.every(config['jobs']['collection']['timer']).seconds.do(new_collection)

    # Main loop
    while True:
        random_float = random.triangular(0.0, 1.0, 0.5)
        print(random_float)
        arduino_send_test(random_float)
        schedule.run_pending()
        for event in pg.event.get():
            if event.type == CLIP_EVENT:
                logger.info(f'Clip end event: {event}')
                clip_manager.check_finished()
                # if clip_manager.clips_playing() == 0:
                #     update_clips()
        time.sleep(1)