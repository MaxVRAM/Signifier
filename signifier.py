
#    _________.__              .__       .__    .__              
#   /   _____/|__| ____   ____ |__|_____ |  |__ |__| ___________ 
#   \_____  \ |  |/ ___\ /    \|  \____ \|  |  \|  |/ __ \_  __ \
#   /        \|  / /_/  >   |  \  |  |_> >   φ  \  \  ___/|  | \/
#  /_______  /|__\___  /|___|  /__|   __/|___|  /__|\___  >__|   
#          \/   /_____/      \/   |__|        \/        \/


# ARDUINO SCRIPT CURRENTLY LOADED:
# - purple_volume.ino



# Displaying audio hardware:
# aplay -l

# Create a virtual audio loopback device:
# sudo modprobe snd-aloop

# For resolving error 'ALSA lib pcm_direct.c:1846:(_snd_pcm_direct_get_slave_ipc_offset) Invalid value for card'??
# sudo usermod -aG audio $USER
# Or you know... hardcode? :(

from ctypes import c_byte, c_char
import logging, os, signal, sys, time, schedule, json, random, queue, threading
import pygame as pg
from signify.clip_manager import ClipManager
from pySerialTransfer import pySerialTransfer as txfer

# Initialise logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

os.environ["SDL_VIDEODRIVER"] = "dummy"

arduino = None
clip_manager = None
CLIP_EVENT = pg.USEREVENT+1

CONFIG_FILE = 'config.json'
with open(CONFIG_FILE) as c:
    config = json.load(c)


arduino_okay = False
arduino = txfer.SerialTransfer('/dev/ttyACM0')
receive_thread = None
q = queue.Queue()





class BaseThread(threading.Thread):
    """Modified Thread class for executing callback functions on completion."""
    def __init__(self, callback=None, callback_args=None, *args, **kwargs):
        target = kwargs.pop('target')
        super(BaseThread, self).__init__(target=self.target_with_callback, *args, **kwargs)
        self.callback = callback
        self.method = target
        self.callback_args = callback_args

    def target_with_callback(self):
        self.method()
        if self.callback is not None:
            self.callback(*self.callback_args)


class ArduinoCmd(object):
    def __init__(self, command:str, value:int, duration=0) -> None:
        self.command = command
        self.value = value
        self.duration = duration
    #
    # TYPES:
    # - (char) name
    # - (uint8_t) value
    # - (uint16_t) value
    #
    # COMMANDS:
    # - b = set strip brightness
    # - m = set max brightness
    # - h = set strip hue
    # - s = set strip saturation



#  _________                __                .__   
#  \_   ___ \  ____   _____/  |________  ____ |  |  
#  /    \  \/ /  _ \ /    \   __\_  __ \/  _ \|  |  
#  \     \___(  <_> )   |  \  |  |  | \(  <_> )  |__
#   \______  /\____/|___|  /__|  |__|   \____/|____/
#          \/            \/                         

def new_collection(pool_size=None, start_jobs=True):
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
    if start_jobs is True:
        time.sleep(1)
        set_jobs(True)
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


def prepare_clip_manager():
    """Load Clip Manager with audio library and initialise the clips."""
    global clip_manager
    try:
        clip_manager = ClipManager(config['clip_manager'], pg.mixer, CLIP_EVENT)
    except OSError:
        exit_handler.shutdown()
    clip_manager.init_library()

def wait_to_start():
    print()
    start_delay = config["general"]["start_delay"]
    logger.info(f'Signifier ready! Starting in ({start_delay}) seconds...')
    time.sleep(1)
    for i in range(1, start_delay):
        print(f'...{start_delay-i}')
        time.sleep(1)
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
        if receive_thread is not None:
            logger.debug(f'Attempting to stop threads.')
            q.put(['thread', 'shutdown'])
            receive_thread.join(2)
            if receive_thread.is_alive():
                logger.warning(f'Thread "{receive_thread.name}" join timeout! An error will be raised.')
        arduino.close()
        schedule.clear()
        stop_all_clips()
        while pg.mixer.get_busy():
            time.sleep(0.1)
        pg.mixer.quit()
        logger.info("Signifier shutdown complete.")
        print()
        sys.exit()




def led_command(command:c_byte, value:int, duration:int) -> bool:
    """Sends a command to the Arduino via serial. Commands should be formatted using ArduinoCmd objects."""
    # https://github.com/PowerBroker2/pySerialTransfer/blob/master/examples/data/Python/tx_data.py
    sendSize = 0
    sendSize = arduino.tx_obj(command, start_pos=sendSize)
    sendSize = arduino.tx_obj(value, start_pos=sendSize)
    sendSize = arduino.tx_obj(duration, start_pos=sendSize)
    success = arduino.send(sendSize)
    print(f'Sent Arduino "{command}" with value ({value}) and ({duration})... success? {success}')
    return success

def arduino_callback():
    recSize = 0
    command = arduino.rx_obj(obj_type='c', start_pos=recSize)
    recSize += txfer.STRUCT_FORMAT_LENGTHS['c']
    command = command.decode("utf-8")        
    value = arduino.rx_obj(obj_type='f', start_pos=recSize)
    recSize += txfer.STRUCT_FORMAT_LENGTHS['f']
    #return_value = ['main', command, value]
    print(f'From Arduino... command: "{command}", Value: ({value})')

    if command == 'r':
        random_float = random.triangular(0.0, 1.0, 0.5)
        led_command('B', (random_float * 255), 0)


# NOTE Try this thread callback example in case Serial callbacks don't work
# https://gist.github.com/amirasaran/e91c7253c03518b8f7b7955df0e954bb
def arduino_listen():
    """Thread to jump on serial data as soon as it's received from the Arduino."""
    logger.info(f'Arduino Listener Thread started.')
    q_message = None
    okay = False
    while True:
        try:
            while not arduino.available():
                # Thread queue message processing
                # try:
                #     q_message = q.get(block=False)
                # except queue.Empty:
                #     pass
                # if q_message[0] == 'thread':
                #     if q_message[1] == 'shutdown':
                #         return None
                #     if q_message[1] == 'okay':
                #         okay = True
                #         print(f'Thread got {q_message} and has set Arduino status to {okay}')

                # Arduino error processing
                if arduino.status < 0:
                    if arduino.status == txfer.CRC_ERROR:
                        logger.error('Arduino: CRC_ERROR')
                    elif arduino.status == txfer.PAYLOAD_ERROR:
                        logger.error('Arduino: PAYLOAD_ERROR')
                    elif arduino.status == txfer.STOP_BYTE_ERROR:
                        logger.error('Arduino: STOP_BYTE_ERROR')
                    else:
                        logger.error(f'Arduino: {arduino.status}')

            # NOTE: Had issues with data types while using arrays. Sticking with stucts...
            recSize = 0
            command = arduino.rx_obj(obj_type='c', start_pos=recSize)
            recSize += txfer.STRUCT_FORMAT_LENGTHS['c']
            command = command.decode("utf-8")        
            value = arduino.rx_obj(obj_type='f', start_pos=recSize)
            recSize += txfer.STRUCT_FORMAT_LENGTHS['f']
            return_value = ['main', command, value]
            print(f'Command: {command}, Value: {value}')
            q.put(return_value)
            

        except (txfer.serial.SerialException, OSError, TypeError):
            pass

def init_arduino_comms():
    receive_thread = threading.Thread(target=arduino_listen, name='Arduino Listener Thread')
    receive_thread.daemon = True
    receive_thread.start()

def arduino_setup():
    """TODO will populate with checks and timeouts for Arduino serial connection.\n
    If reaches timeout before connection, will disable Arduino/LED portion of the Signifier code."""
    arduino.set_callbacks(callback_list)
    arduino.open()
    time.sleep(1)

# Probably won't need, but will keep it here just in case
callback_list = [arduino_callback]




# def my_thread_job():
#     # do any things here
#     print("thread start successfully and sleep for 5 seconds")
#     time.sleep(5)
#     print ("thread ended successfully!")


# def cb(param1, param2):
#     # this is run after your thread end
#     print ("callback function called")
#     print (f'{param1}, {param2}')



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
    
    arduino_setup()
    prepare_playback_engine()
    prepare_clip_manager()
    new_collection(start_jobs=False)

    wait_to_start()




    # # example using BaseThread with callback
    # thread = BaseThread(
    #     name='test',
    #     target=my_thread_job,
    #     callback=cb,
    #     callback_args=("hello", "world")
    # )

    # thread.start()

    #init_arduino_comms()

    # coll_job = schedule.every(config['jobs']['collection']['timer']).seconds.do(new_collection)
    # set_jobs(True)
    # update_clips()
    

    # Main loop
    while True:
        arduino.tick()
        # q_message = None
        # try:
        #     q_message = q.get(block=False)
        # except queue.Empty:
        #     print('Queue empty.')
        #     pass
        # if q_message is not None:
        #     print('Queue is not empty.')
        #     if q_message[0] == 'main':
        #         print(f'Returned value from Arduino thread: {q_message}')
        #         if q_message[1] == 'o':
        #             arduino_okay = True
        #             print(f'Arduino status is now {arduino_okay}')
        #             q.put(['thread', 'okay'])
        #         if q_message[1] == 'r':
        #             print(f'Arduino is ready to be sent serial data.')


        # schedule.run_pending()
        # for event in pg.event.get():
        #     if event.type == CLIP_EVENT:
        #         logger.info(f'Clip end event: {event}')
        #         clip_manager.check_finished()
        #         # if clip_manager.clips_playing() == 0:
        #         #     update_clips()
        #time.sleep(1)