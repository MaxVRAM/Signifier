
#  _________ .__  .__         .____    ._____.                              
#  \_   ___ \|  | |__|_____   |    |   |__\_ |______________ _______ ___.__.
#  /    \  \/|  | |  \____ \  |    |   |  || __ \_  __ \__  \\_  __ <   |  |
#  \     \___|  |_|  |  |_> > |    |___|  || \_\ \  | \// __ \|  | \/\___  |
#   \______  /____/__|   __/  |_______ \__||___  /__|  (____  /__|   / ____|
#          \/        |__|             \/       \/           \/       \/     

"""Module to manage an audio clip library and playback."""

import logging, os, random
import pygame.mixer as Mixer

from signify.sig_utils import plural
from signify.clip_utils import *
from signify.clip import Clip

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ClipManager:
    """Used to create collections of audio clips for playback."""
    def __init__(self, config:dict, mixer:Mixer, event:int) -> None:
        """Create a new clip manager object.\nSee config.json file in project directory for required parameters."""
        if not os.path.isdir(config['base_path']):
            logger.error(f'Invalid root path for library: {config["base_path"]}.')
            raise OSError
        self.config = config
        self.mixer = mixer
        self.clip_event = event
        self.channels = None
        self.collections = {}
        self.current_collection = {}
        self.inactive_pool = set()
        self.active_pool = set()
        pass

    #----------------------
    # Collection management
    #----------------------
    def init_library(self):
        """Initialises the library with collections of Clips from the base path's subdirectories."""
        logger.debug(f'Initialising library from base path {self.config["base_path"]}...')
        titles = [d for d in os.listdir(self.config['base_path']) if os.path.isdir(os.path.join(self.config['base_path'], d))]
        for title in sorted(titles):
            path = os.path.join(self.config['base_path'], title)
            names = []
            for f in os.listdir(path):
                if os.path.splitext(f)[1] in self.config['valid_extensions']:
                    names.append(f)
            if len(names) != 0:
                self.collections[title] = {'path':path, 'names':names}
                logger.debug(f'"{title}" added to library with "{len(names)}" audio files.')
        logger.info(f'Audio clip library initialised with ({len(self.collections)}) collection{plural(self.collections)}.')

    def select_collection(self, name=None, num_clips=12):
        """Selects a collection from the library, prepares clips and playback pools.\n
        Will randomly select a collection if valid name is not supplied."""
        logger.debug(f'Importing {"random " if name is None else ""}collection '
                    f'{(str(name) + " ") if name is not None else ""}from library.')
        if name is not None and name not in self.collections:
            logger.warn('Requested collection name does not exist. One will be randomly selected.')
            name = None
        if name is None:
            name = random.choice(list(self.collections.keys()))
        path, names = (self.collections[name]['path'], self.collections[name]['names'])
        logger.info(f'Collection "{name}" selected with ({len(names)}) audio file{plural(names)} from: {path}')
        self.current_collection = {'title':name, 'path':path, 'names':names}
        # Build clips from collection to populate clip manager and initialise the clip pools 
        self.clips = set([Clip(path, name, self.config['categories']) for name in names])
        self.active_pool = set()
        if (pool := get_distributed(self.clips, num_clips, self.config['strict_distribution'])) is not None:
            self.inactive_pool = pool
            self.channels = self.get_channels(self.inactive_pool)
            failed = init_sounds(self.inactive_pool, self.channels) # TODO Keeping failed returns in case they're useful
            return self.current_collection
        else:
            logger.error(f'Failed to retrieve a collection "{name}"! Audio files might be corrupted.')
            return None

    def get_channels(self, clip_set:set) -> dict:
        """Return dict with Channel indexes keys and Channel objects as values.
        Updates the mixer if there aren't enough channels"""
        channels = {}
        num_chans = self.mixer.get_num_channels()
        num_wanted = len(clip_set)
        # Update the audio mixer channel count if required
        if num_chans != num_wanted:
            logger.info(f'Mixer has {num_chans} Channels but '
                        f'{num_wanted} are needed. Attempting to update mixer...')
            self.mixer.set_num_channels(num_wanted)
            num_chans = self.mixer.get_num_channels()
            logger.info(f'Mixer now has {num_chans} channels.')
            print()
        for i in range(num_chans):
            channels[i] = self.mixer.Channel(i)
        return channels

    #----------------
    # Clip management
    #----------------
    def move_to_inactive(self, clips:set):
        """Supplied list of Clip(s) are moved from active to inactive pool."""
        for clip in clips:
            self.active_pool.remove(clip)
            self.inactive_pool.add(clip)
            logger.debug(f'MOVED: {clip.name} | active >>> INACTIVE.')

    def move_to_active(self, clips:set):
        """Supplied list of Clip(s) are moved from inactive to active pool."""
        for clip in clips:
            self.inactive_pool.remove(clip)
            self.active_pool.add(clip)
            logger.debug(f'MOVED: {clip.name} | inactive >>> ACTIVE.')

    def check_finished(self) -> set:
        """Checks active pool for lingering Clips finished playback, and moves them to the inactive pool."""
        finished = set()
        for clip in self.active_pool:
            if not clip.channel.get_busy():
                logger.info(f'Clip {clip.name} finished.')
                finished.add(clip)
        if len(finished) > 0:
            print()
            self.move_to_inactive(finished)
            print()
        return finished

    def play_clip(self, clips=set(), name=None, category=None, num_clips=1, volume=None, fade=None, event=None) -> set:
        """Start playback of Clip(s) from the inactive pool, selected by object, name, category, or at random.
        Clips started are moved to the active pool and are returned as a set."""
        volume = self.config['volume'] if volume is None else volume
        fade = self.config['fade_in'] if fade is None else fade
        event = self.clip_event if event is None else event
        if len(clips) == 0:
            clips = get_clip(self.inactive_pool, name=name, category=category, num_clips=num_clips)
        started = set([c for c in clips if c.play(volume, event, fade) is not None])
        self.move_to_active(started)
        return started

    def stop_clip(self, clips=set(), name=None, category=None, num_clips=1, fade=None) -> set:
        """Stop playback of Clip(s) from the active pool, selected by object, name, category, or at random.
        Clips stopped are moved to the inactive pool and are returned as a set."""
        fade = self.config['fade_out'] if fade is None else fade
        if len(clips) == 0:
            clips = get_clip(self.active_pool, name=name, category=category, num_clips=num_clips)
        stopped = set([c for c in clips if c.stop(fade) is not None])
        self.move_to_inactive(stopped)
        return stopped

    def modulate_volumes(self, speed, weight):
        """Randomly modulate the Channel volumes for all Clip(s) in the active pool.\n 
        - "speed=(int)" is the maximum volume jump per tick as a percentage of the total volume. 1 is slow, 10 is very quick.\n 
        - "weight=(float)" is a signed normalised float (-1.0 to 1.0) that weighs the random steps towards either direction."""
        speed = speed / 100
        weight = weight * speed
        new_volumes = []
        for clip in self.active_pool:
            vol = clip.channel.get_volume()
            vol *= random.triangular(1-speed,1+speed,1+weight)
            vol = max(min(vol,0.999),0.1)
            clip.channel.set_volume(vol)
            new_volumes.append(f'({clip.index}) "{clip.name}" @ {clip.channel.get_volume():.2f}')
        if len(new_volumes) > 0:
            logger.debug(f'Channel volumes updated: {new_volumes})')

    def clips_playing(self) -> int:
        return len(self.active_pool)
