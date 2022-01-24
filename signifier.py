
#    _________.__              .__  _____       
#   /   _____/|__| ____   ____ |__|/ ____\__.__.
#   \_____  \ |  |/ ___\ /    \|  \   __<   |  |
#   /        \|  / /_/  >   |  \  ||  |  \___  |
#  /_______  /|__\___  /|___|  /__||__|  / ____|
#          \/   /_____/      \/          \/     
#

"""
Audio System Information:

To run Signify with LEDs modulated by the Signify audio

An audio loopback device needs to be instantiated on
before this script: `sudo modprobe snd-aloop`. This will
create a device called 'Loopback, Loopback PCM', and
should be the device name set in config.json.

The audio sent to the loopback device then needs to be
manually routed through the RPi's physical audio output
jack. This can be done with the `alsa-utils` CLI tool
`alsaloop`, and should run prior to the Signifier.

`alsaloop -C hw:3,1 -P hw:0,0 -t 5000 -c 1 -f S16_LE`

Note, that these audio device numbers are system specific.
They may need to be changed to reflect you system config.

"""


import os
import sys
import time
import json
import queue
import signal
import logging
import schedule
import threading

import pygame as pg

from signify.siguino import Siguino, ArduinoState
from signify.clipManager import ClipManager
from signify.audioAnalysis import Analyser


CLIP_EVENT = pg.USEREVENT + 1
CONFIG_FILE = 'config.json'

os.environ['SDL_VIDEODRIVER'] = 'dummy'

config = None
active_jobs = {}

arduino_thread = None
arduino_active = False
arduino_state = ArduinoState
arduino_return_q = queue.Queue()
arduino_control_q = queue.Queue(maxsize=1)
arduino_value_q = queue.Queue()

audio_active = False
analysis_thread = None
analysis_active = False
analysis_return_q = queue.Queue()
analysis_control_q = queue.Queue(maxsize=1)

thread_event = threading.Event()
passthrough_thread = None

descriptors = {}
clip_manager: ClipManager
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


#  _________ .__  .__
#  \_   ___ \|  | |__|_____  ______
#  /    \  \/|  | |  \____ \/  ___/
#  \     \___|  |_|  |  |_> >___ \
#   \______  /____/__|   __/____  >
#          \/        |__|       \/

def stop_random_clip():
    """Stop a randomly selected audio clip from the active pool."""
    if audio_active:
        clip_manager.stop_clip()


def stop_all_clips(fade_time=None, disable_events=True):
    """Tell all active clips to stop playing, emptying the mixer of\
    active channels.\n `fade_time=(int)` the number of milliseconds active\
    clips should take to fade their volumes before stopping playback.\
    If no parameter is provided, the clip_manager's `fade_out`\
    value from the config.json will be used.\n Use 'disable_events=True'\
    to prevent misfiring audio jobs that use clip end events to launch more."""
    if audio_active:
        fade_time = config['clip_manager']['fade_out'] if fade_time is None\
            else fade_time
        if pg.mixer.get_init():
            if pg.mixer.get_busy():
                logger.info(f'Stopping audio clips: {fade_time}ms fade...')
                if disable_events is True:
                    clip_manager.clear_events()
                pg.mixer.fadeout(fade_time)


def manage_audio_events():
    """Check for audio playback completion events,
    call the clip manager to clean them up."""
    if audio_active:
        for event in pg.event.get():
            if event.type == CLIP_EVENT:
                logger.info(f'Clip end event: {event}')
                clip_manager.check_finished()


def wait_for_silence():
    """Stops the main thread until all challens have faded out."""
    if audio_active:
        while pg.mixer.get_busy():
            time.sleep(0.1)


#       ____.     ___.
#      |    | ____\_ |__   ______
#      |    |/  _ \| __ \ /  ___/
#  /\__|    (  <_> ) \_\ \\___ \
#  \________|\____/|___  /____  >
#                      \/     \/

def get_collection(pool_size=None, restart_jobs=True, pause_leds=True):
    """Select a new collection from the clip manager, replacing any\
    currently loaded collection.\n - `pool_size=(int)` defines the
    number of clips to load from the collection.\n If parameter is
    not provided, the job's config.json default `pool_size` value
    will be used.\n - `restart_jobs=(bool)` tells the function if the
    additional modulation jobs should be started immediately after the
    new collection has been loaded. If set to False, they will need
    to be manually triggered using the `set_jobs()` function."""
    if audio_active:
        job_params = config['jobs']['collection']['parameters']
        pool_size = job_params['pool_size']\
            if pool_size is None else pool_size
        print()
        if restart_jobs:
            stop_job('composition', 'volume')
        if pause_leds:
            set_arduino_state('pause')
        stop_all_clips()
        wait_for_silence()
        print()
        while clip_manager.select_collection() is None:
            logger.info(f'Trying another collection in\
                {config["clip_manager"]["fail_retry_delay"]} seconds...')
            time.sleep(config["clip_manager"]["fail_retry_delay"])
            get_collection()
        logger.info('NEW COLLECTION JOB DONE.')
        print()
        if pause_leds:
            set_arduino_state('starting')
        if restart_jobs:
            time.sleep(1)
            automate_composition(
                start_num=job_params['start_clips'])
            start_job('composition', 'volume')


def automate_composition(quiet_level=None, busy_level=None, start_num=1):
    """Ensure the clip manager is playing an appropriate number of clips,\
    and move any finished clips still lingering in the active pool to
    the inactive pool.\n - `quiet_level=(int)` the lowest number of
    concurrent clips playing before looking for more to play.\n -
    `busy_level=(int)` the highest number of concurrent clips playing
    before stopping active clips."""
    if audio_active:
        job_params = config['jobs']['composition']['parameters']
        quiet_level = job_params['quiet_level']\
            if quiet_level is None else quiet_level
        busy_level = job_params['busy_level']\
            if busy_level is None else busy_level
        print()
        changed = set()
        changed = clip_manager.check_finished()
        if clip_manager.clips_playing() < quiet_level:
            changed.update(clip_manager.play_clip(num_clips=start_num))
        elif clip_manager.clips_playing() > busy_level:
            changed.update(clip_manager.stop_clip())
        # Stop a random clip after a certain amount of time?
        print()


def modulate_volumes(speed=None, weight=None):
    """Randomly modulate the Channel volumes for all Clip(s) in the\
    active pool.\n - `speed=(int)` is the maximum volume jump per tick
    as a percentage of the total volume. 1 is slow, 10 is very quick.\n -
    "weight=(float)" is a signed normalised float (-1.0 to 1.0) that
    weighs the random steps towards either direction."""
    if audio_active:
        speed = config['jobs']['volume']['parameters']['speed']\
            if speed is None else speed
        weight = config['jobs']['volume']['parameters']['weight']\
            if weight is None else weight
        clip_manager.modulate_volumes(speed, weight)


def start_job(*args):
    """Start jobs matching names provided as string arguments.\n
    Jobs will only start if it is registered in the jobs dict,\
    not in the active jobs pool, and where it's tagged service\
    and the job ifself are both enabled in config file."""
    jobs = set(args)
    jobs.intersection_update(jobs_dict.keys())
    jobs.difference_update(active_jobs.keys())
    jobs.intersection_update(
        set(k for k, v in config['jobs'].items()
            if v['enabled'] and config[v['service']]['enabled']))
    for job in jobs:
        active_jobs[job] = schedule.every(config['jobs'][job]['timer'])\
                            .seconds.do(jobs_dict[job])
    logger.debug(f'({len(active_jobs)}) jobs scheduled!')


def stop_job(*args):
    """Stop jobs matching names provided as string arguments.\n
    Jobs will only be stopped if they are found in the active pool."""
    jobs = set(args)
    jobs.intersection_update(active_jobs.keys())
    for job in jobs:
        schedule.cancel_job(active_jobs.pop(job))


#    _________       __
#   /   _____/ _____/  |_ __ ________
#   \_____  \_/ __ \   __\  |  \____ \
#   /        \  ___/|  | |  |  /  |_> >
#  /_______  /\___  >__| |____/|   __/
#          \/     \/           |__|

def init_clip_manager():
    """Load Clip Manager with audio library and initialise the clips."""
    global clip_manager
    if audio_active:
        logger.info('Initialising Clip Mananger...')
        try:
            clip_manager = ClipManager(
                config['clip_manager'], pg.mixer, CLIP_EVENT)
        except OSError:
            exit_handler.shutdown()
        clip_manager.init_library()


def init_audio_system():
    """Initialise the Pygame mixer and analysis thread (if enabled)."""
    global audio_active, analysis_thread, analysis_active, passthrough_thread
    if config['audio']['enabled'] and not audio_active:
        logger.info('Initialising audio system...')
        pg.mixer.pre_init(
            frequency=config['audio']['sample_rate'],
            size=config['audio']['bit_size'],
            channels=1,
            buffer=config['audio']['buffer'])
        pg.mixer.init()
        pg.init()
        audio_active = True
        logger.debug(f'Audio output mixer set: {pg.mixer.get_init()}')
        if config['audio']['analysis']:
            analysis_thread = Analyser(
                                return_q=analysis_return_q,
                                control_q=analysis_control_q,
                                config=config['audio'])
            analysis_thread.setName('Audio Analysis Thread')
            passthrough_thread = threading.Thread(
                name='Passthrough Thread', target=process_analysis,
                args=(analysis_return_q, arduino_value_q))
            analysis_active = True
            logger.debug(f'{analysis_thread.getName()} active!')
            logger.debug(f'{passthrough_thread.getName()} active!')
        time.sleep(1)


def init_arduino_comms():
    """Initialise the Arduino serial communication thread."""
    global arduino_active, arduino_thread
    if config['arduino']['enabled']:
        arduino_thread = Siguino(
            return_q=arduino_return_q,
            control_q=arduino_control_q,
            value_q=arduino_value_q,
            config=config['arduino'])
        arduino_thread.setName('Arduino Comms Thread')
        arduino_thread.start()
        arduino_active = True
        logger.debug(f'{arduino_thread.getName()} has started.')


#    _________.__            __      .___
#   /   _____/|  |__  __ ___/  |_  __| _/______  _  ______
#   \_____  \ |  |  \|  |  \   __\/ __ |/  _ \ \/ \/ /    \
#   /        \|   Y  \  |  /|  | / /_/ (  <_> )     /   |  \
#  /_______  /|___|  /____/ |__| \____ |\____/ \/\_/|___|  /
#          \/      \/                 \/                 \/

class ExitHandler:
    signals = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}

    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, *args):
        global analysis_active, arduino_active
        self.exiting = True
        print()
        logger.info('Shutdown sequence started!')
        stop_scheduler()
        stop_all_clips()
        wait_for_silence()
        close_arduino_connection()
        close_audio_system()
        logger.info('Waiting to join threads...')

        if analysis_thread is not None and analysis_thread.is_alive():
            analysis_thread.join()
            analysis_active = False
            print('analysis thread down')
        if arduino_thread is not None and arduino_thread.is_alive():
            arduino_thread.join()
            arduino_active = False
            print('arduino thread down')
        logger.info('Signifier shutdown complete!')
        print()
        sys.exit()


def stop_scheduler():
    schedule.clear()


def close_arduino_connection():
    global arduino_thread, arduino_active
    if arduino_thread is not None and arduino_thread.is_alive():
        logger.info('Closing Arduino communications...')
        set_arduino_state('closed', 2)
        arduino_thread.event.set()
        arduino_thread.join()
    arduino_active = False


def close_audio_system():
    global audio_active, analysis_thread
    if audio_active:
        logger.info('Closing audio system...')
        if analysis_thread is not None and analysis_thread.is_alive():
            analysis_control_q.put('close', timeout=2)
            analysis_thread.event.set()
            analysis_thread.join()
        thread_event.set()
        if pg.get_init() is True and pg.mixer.get_init() is not None:
            pg.quit()
        audio_active = False
        logger.info('Audio system now inactive!')


jobs_dict = {
    'collection': get_collection,
    'composition': automate_composition,
    'volume': modulate_volumes
}


#  ________                               
#  \_____  \  __ __   ____  __ __   ____  
#   /  / \  \|  |  \_/ __ \|  |  \_/ __ \ 
#  /   \_/.  \  |  /\  ___/|  |  /\  ___/ 
#  \_____\ \_/____/  \___  >____/  \___  >
#         \__>           \/            \/ 


def process_analysis(audio_q, arduino_q):
    while not thread_event.is_set():
        try:
            value = audio_q.get(timeout=1)
            message = ('brightness', value['peak'])
            try:
                arduino_q.put(message, timeout=1)
            except queue.Full:
                pass
        except queue.Empty:
            pass


def set_arduino_value(message:tuple):
    if arduino_thread is not None and arduino_active:
        try:
            arduino_value_q.put_nowait(message)
        except queue.Full:
            pass


def set_arduino_state(state:str, timeout=0.5):
    if arduino_thread is not None and arduino_active:
        try:
            logger.debug(f'Trying to send Arduino thread "{state}" state.')
            arduino_control_q.put(state, timeout=timeout)
            logger.debug(f'Sent state "{state}" to Arduino thread!')
            return True
        except queue.Full:
            logger.error(f'Timed out sending "{state}" state to Arduino thread!')
            return False
    return False


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

    with open(CONFIG_FILE) as c:
        config = json.load(c)

    exit_handler = ExitHandler()
    thread_event.clear()
    time.sleep(1)

    init_audio_system()
    init_clip_manager()
    init_arduino_comms()
    get_collection(restart_jobs=False, pause_leds=False)
    start_job('collection', 'composition', 'volume')
    automate_composition(start_num=config['jobs']['collection']['parameters']['start_clips'])
    if analysis_thread is not None:
        analysis_thread.start()
    if passthrough_thread is not None:
        passthrough_thread.start()

    while True:
        schedule.run_pending()
        manage_audio_events()
        #time.sleep(0.01)