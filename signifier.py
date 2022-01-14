
#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/

import logging
import os
import signal
import sys
import time
import schedule
import json

from ctypes import c_wchar
from signify.clip_manager import ClipManager
from pySerialTransfer import pySerialTransfer as txfer
import pygame as pg

os.environ["SDL_VIDEODRIVER"] = "dummy"

active_jobs = {}

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CONFIG_FILE = 'config.json'
with open(CONFIG_FILE) as c:
    config = json.load(c)

CLIP_EVENT = pg.USEREVENT+1
clip_manager:ClipManager

# NOTE The Arduino is here!
# 38400 is the only baud rate that worked to a standard I was happy with.
# Initally, I had issues with serial communication between the Arduino
# and RPi, so I attempted various baud rates: 9600, 14400, 19200, 28800.
# They all had major issues with dropped serial packets. 38400 is
# extremely robust, and I feel like I can rely on this to produce the
# results I'm after.

arduino = None
arduino_callbacks = None
arduino_send_time = time.time_ns() // 1_000_000
arduino_send_period = 300
brightness_value = 0

class arduinoStruct(object):
    command = ''
    value = 0
    duration = 0

arduino_return = arduinoStruct


#  _________ .__  .__              
#  \_   ___ \|  | |__|_____  ______
#  /    \  \/|  | |  \____ \/  ___/
#  \     \___|  |_|  |  |_> >___ \ 
#   \______  /____/__|   __/____  >
#          \/        |__|       \/ 

def stop_random_clip():
    """Stop a single clip from the active pool at random."""
    if config['audio']['enabled'] is True:
        clip_manager.stop_clip()

def stop_all_clips(fade_time=None, disable_events=False):
    """Tell all active clips to stop playing, emptying the mixer of\
    active channels.\n - "fade_time=(int)" the number of milliseconds 
    active clips should take to fade their volumes before stopping
    playback. If no parameter is provided, the [clip_manager][fade_out] 
    value from the config.json will be used."""
    if config['audio']['enabled'] is True:
        fade_time = config['clip_manager']['fade_out'] if fade_time is None \
            else fade_time
        if pg.mixer.get_init():
            if pg.mixer.get_busy():
                logger.info(f'Stopping audio clips, with {fade_time}ms fade...')
                if disable_events is True:
                    clip_manager.clear_events()
                pg.mixer.fadeout(fade_time)

def check_audio_events():
    """Check for audio playback completion events, 
    call the clip manager to clean them up"""
    if config['audio']['enabled'] is True and pg.get_init() is True:
        for event in pg.event.get():
            if event.type == CLIP_EVENT:
                logger.info(f'Clip end event: {event}')
                clip_manager.check_finished()


#       ____.     ___.           
#      |    | ____\_ |__   ______
#      |    |/  _ \| __ \ /  ___/
#  /\__|    (  <_> ) \_\ \\___ \ 
#  \________|\____/|___  /____  >
#                      \/     \/ 

def get_collection(pool_size=None, restart_jobs=True):
    """Select a new collection from the clip manager, replacing any\
    currently loaded collection.\n - "pool_size=(int)" defines the 
    number of clips to load from the collection. If parameter is
    not provided, the job's config.json default "pool_size" value 
    will be used.\n - "restart_jobs=(bool)" tells the function if the 
    additional modulation jobs should be started immediately after the 
    new collection has been loaded. If set to False, they will need 
    to be manually triggered using the "set_jobs()" function."""
    if config['audio']['enabled'] is True:
        pool_size = config['jobs']['collection']['parameters']['pool_size']\
            if pool_size is None else pool_size
        print()
        if restart_jobs is True:
            stop_job(['composition', 'volume'])
        stop_all_clips(disable_events=True)
        while pg.mixer.get_busy():
            time.sleep(0.1)
        while (collection := clip_manager.select_collection() is None):
            logger.info(f'Trying another collection in\
                {config["clip_manager"]["fail_retry_delay"]} seconds...')
            time.sleep(config["clip_manager"]["fail_retry_delay"])
            get_collection()
        logger.info(f'NEW COLLECTION JOB DONE.')
        print()
        if restart_jobs is True:
            time.sleep(1)
            automate_composition()
            start_job(['composition', 'volume'])

def automate_composition(quiet_level=None, busy_level=None):
    """Ensure the clip manager is playing an appropriate number of clips,\
    and move any finished clips still lingering in the active pool to
    the inactive pool.\n - "quiet_level=(int)" the lowest number of
    concurrent clips playing before looking for more to play.\n -
    "busy_level=(int)" the highest number of concurrent clips playing
    before stopping active clips."""
    if config['audio']['enabled'] is True:
        quiet_level = config['jobs']['composition']['parameters']['quiet_level']\
            if quiet_level is None else quiet_level
        busy_level = config['jobs']['composition']['parameters']['busy_level']\
            if busy_level is None else busy_level
        print()
        changed = set()
        changed = clip_manager.check_finished()
        if clip_manager.clips_playing() < quiet_level:
            changed.update(clip_manager.play_clip())
        elif clip_manager.clips_playing() > busy_level:
            changed.update(clip_manager.stop_clip())
        # Stop a random clip after a certain amount of time?
        print()

def modulate_volumes(speed=None, weight=None):
    """Randomly modulate the Channel volumes for all Clip(s) in the\
    active pool.\n - "speed=(int)" is the maximum volume jump per tick
    as a percentage of the total volume. 1 is slow, 10 is very quick.\n -
    "weight=(float)" is a signed normalised float (-1.0 to 1.0) that
    weighs the random steps towards either direction."""
    if config['audio']['enabled'] is True:
        speed = config['jobs']['volume']['parameters']['speed']\
            if speed is None else speed
        weight = config['jobs']['volume']['parameters']['weight']\
            if weight is None else weight
        clip_manager.modulate_volumes(speed, weight)


def start_job(jobs:list):
    """Start jobs matching the (str)name or list of from provided list."""
    if isinstance(jobs, str):
        jobs = [jobs]
    for job in jobs:
        job_info = config['jobs'].get(job, None)
        if job_info is not None and job_info['enabled'] is True and\
                job in jobs_dict and job not in active_jobs \
                and config[job_info['tag']]['enabled'] is not False:
            active_jobs[job] = \
                schedule.every(job_info['timer']).seconds.do(jobs_dict[job])

def stop_job(jobs):
    """Stop jobs matching the (str)name or list of from provided list."""
    if isinstance(jobs, str):
        jobs = [jobs]
    for job in jobs:
        if job in active_jobs:
            schedule.cancel_job(active_jobs.pop(job))

"""Dictionary object to convert job strings from the config file to
their associated function calls"""
jobs_dict = {
    'collection': get_collection,
    'composition': automate_composition,
    'volume': modulate_volumes
}


#    _________       __                
#   /   _____/ _____/  |_ __ ________  
#   \_____  \_/ __ \   __\  |  \____ \ 
#   /        \  ___/|  | |  |  /  |_> >
#  /_______  /\___  >__| |____/|   __/ 
#          \/     \/           |__|    

def audio_device_check() -> str:
    """Return valid audio device if it exists on the host."""
    # TODO Create functional mechanism to find and test audio devices
    if config['audio']['enabled'] is True:
        default_device = config['audio']['device']
        try:
            import pygame._sdl2 as sdl2
            pg.init()
            is_capture = 0
            num_devices = sdl2.get_num_audio_devices(is_capture)
            device_names = [str(sdl2.get_audio_device_name(i, is_capture),\
                encoding="utf-8") for i in range(num_devices)]
            pg.mixer.quit()
            pg.quit()
            if device_names is None or len(device_names) == 0:
                logger.warning(f'No audio devices detected by sdl2. Attempting '
                               f'to force default: "{default_device}"...')
                exit_handler.shutdown()
            logger.debug(f'SDL2 detected the following audio devices: '
                         f'{device_names}')
            device = None
            for d in device_names:
                if default_device in d:
                    device = d
                    break
            if device is None:
                logger.warning(f'Expected audio device "{default_device}" '
                               f'but was not detected by sdl2. '
                               f'Attempting to force driver...')
                exit_handler.shutdown()
            logger.info(f'"{device}" found on host and will be used for audio playback.')
            return default_device
        except Exception as exception:
            logger.warning(f'Error while using sdl2 to determine audio devices '
                           f'available on host. Attempting to force '
                           f'"{default_device}": {exception}')
            return default_device

def init_audio_engine():
    """Ensure audio driver exists and initialise the Pygame mixer."""
    if config['audio']['enabled'] is True:
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
        logger.debug(f'Audio mixer successfully configured with device: '
                     f'"{device} {pg.mixer.get_init()}"')
        print()

def init_clip_manager():
    """Load Clip Manager with audio library and initialise the clips."""
    if config['audio']['enabled'] is True:
        global clip_manager
        try:
            clip_manager = ClipManager(config['clip_manager'],\
                pg.mixer, CLIP_EVENT)
        except OSError:
            exit_handler.shutdown()
        clip_manager.init_library()


#     _____            .___    .__               
#    /  _  \_______  __| _/_ __|__| ____   ____  
#   /  /_\  \_  __ \/ __ |  |  \  |/    \ /  _ \ 
#  /    |    \  | \/ /_/ |  |  /  |   |  (  <_> )
#  \____|__  /__|  \____ |____/|__|___|  /\____/ 
#          \/           \/             \/        

def arduino_command(command:c_wchar, value:int, duration:int) -> bool:
    """Send the Arduino a command via serial, including a value,\
    and duration for the command to run for."""
    # https://github.com/PowerBroker2/pySerialTransfer/blob/master/examples/data/Python/tx_data.py
    if config['leds']['enabled'] is True:
        sendSize = 0
        value = int(value)
        sendSize = arduino.tx_obj(command, start_pos=sendSize)
        sendSize = arduino.tx_obj(value, start_pos=sendSize)
        sendSize = arduino.tx_obj(duration, start_pos=sendSize)
        success = arduino.send(sendSize)
        return success

def arduino_callback():
    """Called when arduino.tick() receives a serial message from the\
    Arduino, automatically parsing the serial packets for processing (i.e.\
    using the arduino.rx_obj() function).\n Depending on the message\
    received, this function may or may not execute additional commands."""
    if config['leds']['enabled'] is True:
        recSize = 0
        arduino_return.command = arduino.rx_obj(obj_type='c', start_pos=recSize)
        arduino_return.command = arduino_return.command.decode("utf-8")
        recSize += txfer.STRUCT_FORMAT_LENGTHS['c']
        arduino_return.value = arduino.rx_obj(obj_type='l', start_pos=recSize)
        recSize += txfer.STRUCT_FORMAT_LENGTHS['l']
        arduino_return.duration = arduino.rx_obj(obj_type='l', start_pos=recSize)
        recSize += txfer.STRUCT_FORMAT_LENGTHS['l']

        if arduino_return.command != 'r':
            print(f'RECEIVED FROM ARDUINO: {arduino_return.command} '
                  f'{arduino_return.value} {arduino_return.duration}')

        if arduino_return.command == 'r':
            global arduino_send_time, brightness_value
            # Test message for checking Arduino Tx/Rx and LED control
            if (current_ms := time.time_ns() // 1_000_000)\
                    > arduino_send_time + arduino_send_period:
                arduino_send_time = current_ms
                #brightness_value = random.triangular(0.0, 1.0, 0.5)
                if brightness_value == 0:
                    brightness_value = 1
                else:
                    brightness_value = 0

                dur = int(arduino_send_period / 2)
                arduino_command('B', int(brightness_value * 255),\
                    int(dur))
                print()
                print(f'SEND TO ARDUINO: "B" {brightness_value * 255} {dur}')

def arduino_setup():
    """TODO will populate with checks and timeouts for Arduino serial\
    connection.\n If reaches timeout before connection, will disable\
    Arduino/LED portion of the Signifier code."""
    if config['leds']['enabled'] is True:
        global arduino
        arduino = txfer.SerialTransfer('/dev/ttyACM0', baud=38400)
        arduino.set_callbacks(arduino_callbacks)
        logger.debug(f'({len(arduino.callbacks)}) Arduino callback(s) set.')
        arduino.open()
        
        wait_to_start()

def wait_to_start(start_delay=None):
    """Sleep after initialisation to make sure Arduino and\
    RPi start at the same time."""
    # TODO: Replace with a serial message callback for Arduino ready.
    if config['leds']['enabled'] is True:
        print()
        start_delay = config["leds"]["arduino_delay"]\
            if start_delay is None else start_delay
        logger.info(f'Signifier ready! Delaying start to make sure Arduino '
                    f'is ready. Starting in ({start_delay}) seconds...')
        time.sleep(1)
        for i in range(1, start_delay):
            print(f'...{start_delay-i}')
            time.sleep(1)
        print()

arduino_callbacks = [arduino_callback]


#    _________.__            __      .___                   
#   /   _____/|  |__  __ ___/  |_  __| _/______  _  ______  
#   \_____  \ |  |  \|  |  \   __\/ __ |/  _ \ \/ \/ /    \ 
#   /        \|   Y  \  |  /|  | / /_/ (  <_> )     /   |  \
#  /_______  /|___|  /____/ |__| \____ |\____/ \/\_/|___|  /
#          \/      \/                 \/                 \/ 

def stop_scheduler():
    logger.debug(f'({len(schedule.get_jobs())}) active jobs.')
    schedule.clear()

def close_arduino():
    # TODO: Check if Arduino is connected
    # TODO: Tell it to stop / go into idle state
    arduino.close()

def stop_audio():
    if pg.get_init() is True and pg.mixer.get_init() is not None:
        stop_all_clips()
        while pg.mixer.get_busy():
            time.sleep(0.1)
        pg.quit()

class ExitHandler:
    signals = {signal.SIGINT:'SIGINT', signal.SIGTERM:'SIGTERM'}

    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, *args):
        print()
        self.exiting = True
        logger.info(f'Shutdown sequence started.')
        stop_scheduler()
        close_arduino()
        stop_audio()
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
    init_audio_engine()
    init_clip_manager()
    get_collection(restart_jobs=False)
    arduino_setup()

    start_job(['collection','composition', 'volume'])
    automate_composition()

    while True:
        arduino.tick()
        schedule.run_pending()
        check_audio_events()
        #time.sleep(1)