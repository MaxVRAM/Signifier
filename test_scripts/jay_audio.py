'''
sudo apt-get install git curl libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0
'''
import os
import sys
import time
import math
import signal
import random
import logging
import operator
from pathlib import Path
from threading import Timer
from itertools import groupby
#from pyo import *
from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
import pygame as pg

AUDIOCHANNELS = 20
SAMPLERATE = 48000
BUFFERSIZE = 2048
DEFAULT_MAXTIME = 300000

CLIP_PATH = '/home/pi/Signifier/audio'

pg.mixer.pre_init(buffer=2048)
pg.mixer.init(frequency=SAMPLERATE)
pg.init()
pg.mixer.set_num_channels(AUDIOCHANNELS)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

ip = "127.0.0.1"
serverport = int(os.getenv("OSC_SERVER_PORT", 10000))
server = OSCThreadServer()
serverecho = OSCClient(ip, 10000)
server.listen(address=ip, port=10000, default=True)



sample_collection = {}
sample_lengths = {'oneshot':(0,5),'short':(5,10),'medium':(10, 30),'loop':(30,999)}
sounds = []
TRACK_END = pg.USEREVENT+1

previous_time = time.time()


def fade_down_all(time_ms, exit=True):
    #global server
    logger.info(f"Stopping server")
    #server.stop_all()
    for channel in range(AUDIOCHANNELS):
        logger.info(f"Fading down channel: {channel}")
        pg.mixer.Channel(channel).fadeout(time_ms)
    if exit:
        time_s = (time_ms * 0.001) + 1
        logger.info(f"Delaying exit for {time_s} secs while channels fade..")
        time.sleep(time_s)

def distribtute_sounds(sample_collection):
    sounds = []
    transpose = {}
    for o,d in sample_collection.items():
        d.setdefault("obj", o)
        print(d)
        transpose.setdefault(d['length_type'], []).append(d)
    for t in transpose:
        print(f'{t}: {len(t)}')
    avail_chans = int(12 / len(transpose.keys()))
    logger.info(f"channels available per category : {avail_chans}")

    # This is the primary method of selected K number of samples per length category
    for k,v in transpose.items():
        sounds += random.sample(v, min(avail_chans, len(v)))

    for channel_idx, sound in enumerate(sounds):
        sample_collection[sound['obj']]['loaded'] = True
        sample_collection[sound['obj']]['channel'] = channel_idx
        logger.info(f"added to channel {channel_idx}: {sound} \n")

    return sounds

def load_samples(sample_collection_idx):
    """ load audio """
    global server, sounds, sample_collection
    fade_down_all(5000, exit=False)
    logger.info(f"loading sample collection S{sample_collection_idx}")
    for (root, dirs, files) in os.walk(f'{CLIP_PATH}/S{sample_collection_idx}', topdown=True):
        for wav in files:
            if wav[-3:] == 'wav':
                filepath = os.path.join(root, wav)
                obj = pg.mixer.Sound(filepath)
                length = obj.get_length()
                #logger.info(f"{wav} : {length} seconds")
                lenstr = [k for k,v in sample_lengths.items() if int(length) in range(*v)][0]
                print(lenstr)
                looping = lenstr in ['medium', 'loop']
                sample_collection.setdefault(obj,
                {
                    'fn': wav,
                    'length': length,
                    "playcount" : 0,
                    'loaded': False,
                    'looping': looping,
                    'channel': None,
                    'length_type': lenstr
                })
                logger.info(sample_collection[obj])

    sounds = distribtute_sounds(sample_collection)
    logger.info(f"loaded {len(sounds)} / {len(sample_collection)} sounds from collection S{sample_collection_idx}..")
    #server.listen()
    #logger.info(f"Server rebooted")
    #return sample_collection

def init_channel_volume():
    for channel in range(AUDIOCHANNELS):
        vol = pg.mixer.Channel(channel).get_volume()
        logger.info(f"setting current volume on channel {channel} to 100%")
        pg.mixer.Channel(channel).set_volume(1.0)

def scan_channels():
    """check for silence/no activity - trigger some sounds if asleep or server is down"""
    channels_open = [channel for channel in range(AUDIOCHANNELS) if not pg.mixer.Channel(channel).get_busy()]
    channels_busy = [i for i in range(1,12) if i not in channels_open]
    channel_playcounts = [sounds[i]['playcount'] for i in range(len(sounds))]
    logger.info(f"Open channels: {channels_open}")
    logger.info(f"Busy channels: {channels_busy}")
    #logger.info(f"Channel_playcounts: {channel_playcounts}")

    # if we are pretty quiet
    if len(channels_open) > 8:
        # pick a random channel to trigger
        ch = random.choice(channels_open)
        logger.info(f"sending trigger to {ch}")
        serverecho.send_message(b'/audio/sound', [ch, 1])

    # if we are too busy
    if len(channels_open) < 4:
        # pick a random channel to fadeout
        ch = random.choice(channels_busy)
        logger.info(f"sending fade trigger to {ch}")
        serverecho.send_message(b'/audio/sound', [ch, 0])

    # modulate volumes on busy channels
    for channel in channels_busy:
        vol = pg.mixer.Channel(channel).get_volume()
        vol *= random.triangular(0.95,1.05,1)
        vol = max(min(vol,0.999),0.1)
        logger.info(f"setting current volume on channel {channel} to {vol}")
        pg.mixer.Channel(channel).set_volume(vol)

    global previous_time
    now = (time.time() - previous_time) * 1000
    logger.info(f'{int((DEFAULT_MAXTIME - now) * 0.001)} seconds till next change..')
    # if we get stuck in a loop
    if now > DEFAULT_MAXTIME:
        # pick a random busy channel to fadeout
        ch = random.choice(channels_busy)
        logger.info(f"max time elapsed: sending fade trigger to {ch}")
        serverecho.send_message(b'/audio/sound', [ch, 0])
        previous_time = time.time()
        new_sample_set = random.randint(1,11)
        load_samples(new_sample_set)



# DONE  ---------------------------------------
@server.address(b'/audio/load')
def callback(*values):
    logger.info("/audio/load: {}".format(values))
    val, *extra = values
    val = max(min(val,11),1)
    load_samples(val)
# DONE  ---------------------------------------



@server.address(b'/audio/sound')
def callback(*values):
    logger.info("/audio/sound: {}".format(values))
    ch, val, *extra = values
    looping = -1 if sounds[ch]['looping'] else random.randint(0,6)
    if val == 1:
        pg.mixer.Channel(ch).play(sounds[ch]['obj'], loops=looping, fade_ms=2333)
        pg.mixer.Channel(ch).set_endevent(TRACK_END)
        sample_collection[sounds[ch]['obj']]['playcount'] += 1
    if val == 0:
        pg.mixer.Channel(ch).fadeout(1333)

@server.address(b'/audio/volume')
def callback(*values):
    logger.info("/audio/volume: {}".format(values))
    ch, val, *extra = values
    val = max(min(val,1),0.1)
    pg.mixer.Channel(ch).set_volume(val)


@server.address(b'/audio/mastervolume')
def callback(*values):
    logger.info("/audio/mastervolume: {}".format(values))
    val, *extra = values
    val = max(min(val,1),0.0)
    for channel in range(AUDIOCHANNELS):
        vol = pg.mixer.Channel(channel).get_volume()
        logger.info(f"setting current volume on channel {channel} to {val}")
        pg.mixer.Channel(channel).set_volume(val)
        sampleset = random.randint(1,12)
        load_samples(sampleset)



# ----------------------
class ExitHandler:
    signals = { signal.SIGINT: 'SIGINT',signal.SIGTERM: 'SIGTERM' }

    def __init__(self):
        self.exit_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.exit_now = True
        logger.info("\nReceived {} signal".format(self.signals[signum]))
        logger.info('pysigAUDIO server exiting gracefully..')
        # exit routines
        activity_monitor.cancel()
        fade_down_all(5000)
        logger.info("Ctrl-C: Shutting down..")
        sys.exit()

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

# ----------------------

if __name__ == '__main__':
    logger.info("pysig_AUDIO..")
    exit_handler = ExitHandler()
    logger.info("loading samples..")
    load_samples(random.randrange(1,11,1))
    init_channel_volume()
    activity_monitor = RepeatTimer(30, scan_channels)
    activity_monitor.start()
    while True:
        for event in pg.event.get():
            if event.type == TRACK_END:
                print(event)
                print('music end event')
        pass