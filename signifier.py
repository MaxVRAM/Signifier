
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
import signal
import logging
import schedule

import pygame as pg

from signify.siguino import Siguino, ArduinoState
from signify.clipManager import ClipManager
from signify.audioAnalysis import Analyser


CLIP_EVENT = pg.USEREVENT + 1
CONFIG_FILE = 'config.json'

os.environ['SDL_VIDEODRIVER'] = 'dummy'
# os.environ['ALSA_CARD'] = 'Loopback'
# os.environ['ALSA_CTL_CARD'] = 'Loopback'
# os.environ['ALSA_PCM_CARD'] = 'Loopback'


config = None
arduino = None
active_jobs = {}
audio_active = False
audio_analysis = None
audio_amplitude = 0
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


#       ____.     ___.
#      |    | ____\_ |__   ______
#      |    |/  _ \| __ \ /  ___/
#  /\__|    (  <_> ) \_\ \\___ \
#  \________|\____/|___  /____  >
#                      \/     \/

def get_collection(pool_size=None, restart_jobs=True):
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
        if restart_jobs is True:
            stop_job('composition', 'volume')
        arduino.set_state(ArduinoState.pause)
        stop_all_clips()
        print()
        while pg.mixer.get_busy():
            time.sleep(0.1)
        while clip_manager.select_collection() is None:
            logger.info(f'Trying another collection in\
                {config["clip_manager"]["fail_retry_delay"]} seconds...')
            time.sleep(config["clip_manager"]["fail_retry_delay"])
            get_collection()
        logger.info('NEW COLLECTION JOB DONE.')
        arduino.set_state(ArduinoState.run)
        print()
        if restart_jobs is True:
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
    print(f'({len(active_jobs)}) jobs active.')


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
    if audio_active:
        global clip_manager
        try:
            clip_manager = ClipManager(
                config['clip_manager'], pg.mixer, CLIP_EVENT)
        except OSError:
            exit_handler.shutdown()
        clip_manager.init_library()


# def check_audio_device(custom_device=None) -> str:
#     """Return valid audio device if it exists on the host. 'custom_device'\
#     must be a list of two strings defining the audio card and device names."""
#     # TODO Create functional mechanism to find and test audio devices
#     device = custom_device if custom_device is not None\
#         else config['audio']['device']
#     device_tuple = (device[0], device[1])
#     devices = [alsa.card_name(r) for r in range(len(alsa.card_indexes()))]
#     if device_tuple not in devices:
#         logger.warning(f'Audio device {device_tuple} not detected by ALSA.')
#         return None
#     logger.info(f'"{device_tuple}" is valid audio device.')
#     return f'{device[0]}, {device[1]}'


def passthrough_callback(values):
    if values is None:
        print('Audio values are none.')
    else:
        print(f'Passthrough values: {values}')

def check_audio_device() -> str:
    """Return valid audio device if it exists on the host."""
    # TODO Create functional mechanism to find and test audio devices
    # Possibly bash command `aplay -l`, or sounddevice.query_devices()
    #default_device = config['audio']['hw_loop_output']
    #default_device = config['audio']['loopback_output']
    #default_device = config['audio']['hw_direct_output']
    #default_device = config['audio']['hw_direct_output']
    # pg.init()
    # is_capture = 0
    # num_devices = sdl2.get_num_audio_devices(is_capture)
    # device_names = [str(sdl2.get_audio_device_name(i, is_capture),
    #                 encoding="utf-8") for i in range(num_devices)]
    # pg.mixer.quit()
    # pg.quit()
    # if device_names is None or len(device_names) == 0:
    #     logger.warning(f'No audio devices detected by sdl2. Attempting '
    #                    f'to force default: "{default_device}"...')
    #     return default_device
    # logger.debug(f'SDL2 detected: {len(device_names)} audio devices.')
    # device = None
    # for d in device_names:
    #     if default_device in d:
    #         device = d
    #         break
    # if device is None:
    #     logger.warning(f'Expected audio device "{default_device}" not '
    #                    f'detected by sdl2. Attempting to force driver...')
    #     return default_device
    # logger.info(f'"{device}" found on host and '
    #             f'will be used for audio playback.')
    default_device = 'default'
    return default_device


def set_audio_engine(*args):
    """Ensure audio driver exists and initialise the Pygame mixer."""
    global audio_active, audio_analysis
    if config['audio']['enabled']:
        if audio_active:
            if 'force' in args:
                close_audio_system()
            else:
                logger.debug('Audio system already active. '
                             'Use "force" arg to reinitialise audio system. '
                             'Ignoring request to start audio.')
                return None
        # Begin initialisation
        device = check_audio_device()
        if device is None:
            logger.error('Audio device could not be detected.\
                Disabling audio system.')
            return None
        # NOTE: It seems that the pg.mixer initialisation doesn't check
        # for a valid audio device. This may be good, but might be bad.
        # Will do some tests to check what happens with and without
        # an audio loopback device active.
        # pg.mixer.pre_init(
        #     frequency=config['audio']['sample_rate'],
        #     size=config['audio']['bit_size'],
        #     channels=1,
        #     buffer=config['audio']['buffer'],
        #     devicename=device)
        pg.mixer.pre_init(
            frequency=config['audio']['sample_rate'],
            size=config['audio']['bit_size'],
            channels=1,
            buffer=config['audio']['buffer'])
        pg.mixer.init()
        pg.init()
        audio_active = True
        logger.debug(f'Audio output device: "{device}" with {pg.mixer.get_init()}')
        if config['audio']['analysis']:
            logger.debug('Audio analysis stream active.')
            audio_analysis = Analyser(config['audio'])
            audio_analysis.setDaemon(True)
            audio_analysis.start()
        time.sleep(1)
    else:
        if audio_active:
            close_audio_system()
        else:
            logger.debug('Audio system is not active. '
                         'Ingnoring request to disable audio system.')
    logger.info(f'Audio system active: {audio_active}')
    print()


#    _________.__            __      .___
#   /   _____/|  |__  __ ___/  |_  __| _/______  _  ______
#   \_____  \ |  |  \|  |  \   __\/ __ |/  _ \ \/ \/ /    \
#   /        \|   Y  \  |  /|  | / /_/ (  <_> )     /   |  \
#  /_______  /|___|  /____/ |__| \____ |\____/ \/\_/|___|  /
#          \/      \/                 \/                 \/

def stop_scheduler():
    logger.debug(f'({len(schedule.get_jobs())}) active jobs will be stopped.')
    schedule.clear()


def close_audio_system():
    global audio_active, audio_analysis
    logger.info('Closing audio system...')
    if pg.get_init() is True and pg.mixer.get_init() is not None:
        stop_all_clips()
        while pg.mixer.get_busy():
            time.sleep(0.1)
        pg.quit()
    if audio_analysis is not None:
        if audio_analysis.is_alive():
            audio_analysis.terminate()
            logger.debug('Audio Stream thread closed.')
    audio_active = False
    logger.info('Audio system now inactive.')


class ExitHandler:
    signals = {signal.SIGINT: 'SIGINT', signal.SIGTERM: 'SIGTERM'}

    def __init__(self):
        self.exiting = False
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, *args):
        print()
        self.exiting = True
        logger.info('Shutdown sequence started.')
        stop_scheduler()
        arduino.set_state(ArduinoState.close)
        close_audio_system()
        logger.info("Signifier shutdown complete.")
        print()
        sys.exit()


jobs_dict = {
    'collection': get_collection,
    'composition': automate_composition,
    'volume': modulate_volumes
}


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
    time.sleep(1)

    set_audio_engine()

    arduino = Siguino(config['arduino'])
    arduino.open_serial()

    init_clip_manager()
    get_collection(restart_jobs=False)

    start_job('collection', 'composition', 'volume')
    automate_composition(start_num=config['jobs']['collection']['parameters']['start_clips'])

    while True:
        arduino.callback_tick()
        schedule.run_pending()
        manage_audio_events()
        audio_amplitude = audio_analysis.get_descriptors()
        time.sleep(0.1)