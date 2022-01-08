

#  _________ .__  .__         .____    ._____.                              
#  \_   ___ \|  | |__|_____   |    |   |__\_ |______________ _______ ___.__.
#  /    \  \/|  | |  \____ \  |    |   |  || __ \_  __ \__  \\_  __ <   |  |
#  \     \___|  |_|  |  |_> > |    |___|  || \_\ \  | \// __ \|  | \/\___  |
#   \______  /____/__|   __/  |_______ \__||___  /__|  (____  /__|   / ____|
#          \/        |__|             \/       \/           \/       \/     

"""Module to manage a Library of audio Clips."""


from __future__ import annotations
import logging, os, random, bisect, time, copy
from sys import exc_info
from pygame import fastevent
import pygame.event as Event
from pygame.constants import USEREVENT
import pygame.mixer as Mixer
from pygame.mixer import Sound, Channel

from test_scripts.pygame_test import CLIP_LIBRARY

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CLIP_END_EVENT = USEREVENT + 1

CATEGORIES = [('oneshot', 0), ('short', 5), ('medium', 10), ('loop', 30)]
LOOP_CATEGORIES = ['medium','loop']
LOOP_RANGE = [0, 6]


# WARNING: Excessively Opulent Logging Utility
def plural(value) -> str:
    """Return "s" or "" pluralise strings based on supplied (int) value or len(!int)."""
    if value is None:
        return ""
    try:
        num = int(value)
    except TypeError:
        num = len(value)
    except:
        return ""
    return "" if num == 1 else "s"



class Clip:
    """Clip objects hold sound file information, its Sound object 
    and its associated Channel, once playback has been triggerd."""

    #-----------------
    # Playback methods
    #-----------------
    def play(self, volume, event, fade) -> Clip:
        """Starts playback of Clip's Sound object with optional "fade=(int)" in ms
        and "event=(int)" to produce an end of clip callback. Returns itself if successful."""
        if self.channel is None:
            logger.warn(f'Cannot play Clip "{self.name}". Not assigned to Channel.')
            return None
        elif self.channel.get_busy():
            logger.warn(f'Cannot play Channel "{self.index}" assigned to "{self.name}". Already playing audio.')
            return None
        else:
            loop_num = -1 if self.looping else random.randint(LOOP_RANGE[0], LOOP_RANGE[1])
            self.channel.play(self.sound, fade_ms=fade, loops=loop_num)
            self.sound.set_volume(volume)
            self.started = time.time()
            if event is not None:
                self.channel.set_endevent(event)
            logger.info(f'Playing clip "{self.name}" on channel ({self.index}) (volume={self.get_volume()}, '
                        f'loops={loop_num}, fade={fade}ms).')
            return self

    def stop(self, fade) -> Clip:
        """Stops the sound playing from the Clip immediately, otherwise supply "fade_time=(int)" in ms."""
        if self.channel is None:
            logger.warn(f'Cannot stop "{self.name}". Not assigned to Channel.')
            return None
        elif not self.channel.get_busy():
            logger.warn(f'Cannot stop "{self.name}"  Channel ({self.index}) assigned to . Not playing audio.')
            return None
        else:
            if fade > 0:
                self.sound.fadeout(fade)
                logger.debug(f'Clip "{self.name}" playing on Channel ({self.index}) is now fading out over {fade}ms.')
                return self
            else:
                self.sound.stop()
                logger.debug(f'Clip "{self.name}" playing on Channel ({self.index}) has been stopped imediately.')
                return self

    def get_volume(self) -> float:
        if self.sound is None:
            logger.warn(f'Cannot get volume of "{self.name}". Not assigned to Sound object.')
        else:
            return self.channel.get_volume()

    def set_volume(self, volume:float):
        if self.sound is None:
            logger.warn(f'Cannot set volume of "{self.name}". Not assigned to Sound object.')
        else:
            self.channel.set_volume(volume)

    #----------------
    # Clip management
    #----------------
    def set_channel(self, chan:tuple) -> Channel:
        """Binds supplied (index, Channel) tuple to Clip."""
        if chan[1].get_sound():
            logger.warn(f'Channel "{chan[0]}" already assigned to "{chan[1].get_sound()}".')
            return None
        self.index = chan[0]
        self.channel = chan[1]
        return self.channel

    def remove_channel(self) -> Channel:
        """Removes Channel and index number from Clip, returning the Channel object."""
        if (chan := self.channel) is None:
            logger.warn(f'No Channel object assigned to "{self.name}", cannot remove. Skipping request.')
            return None
        self.index = None
        self.channel = None
        logger.debug(f'Channel object and index removed from "{self.name}".')
        return chan

    def build_sound(self, chan:tuple) -> Clip:
        """Loads the Clip's audio file into memory as a new Sound object and assign it a mixer Channel."""
        self.sound = Sound(self.path)
        self.index = chan[0]
        self.set_channel(chan)
        if not self.sound or not self.channel:
            logger.warn(f'Could not build "{self.name}"!')
            return None
        logger.debug(f'Loaded clip: {self}.')
        return self

    #---------------------
    # Magic/static methods
    #---------------------
    def __init__(self, root:str, name:str, load=False) -> None:
        """Initialises a new Clip object.\nUse additional {True} arguement to load audio 
        file into memory as new Sound object."""
        self.root = root
        self.name = name
        self.path = os.path.join(root, name)
        sound_object = Sound(self.path)
        self.length = sound_object.get_length()
        self.sound = sound_object if load else None
        self.category = get_category(self.length)
        self.looping = self.category in LOOP_CATEGORIES
        self.channel = None
        self.index = None
        pass

    def __str__(self) -> str:
        details = (f'{self.name}, "{self.category}", "{"looping" if self.looping else "one-shot"}", '
                   f'{self.length:.2f}s on chan ({"NONE" if self.channel is None else self.index}).')
        return details


class Collection:
    """Stores basic information about an audio collection."""
    def __init__(self, title:str, path:str, names:list) -> None:
        self.title = title
        self.path = path
        self.names = names
        pass


class ClipManager:
    """Used to create Collections of audio clips for playback."""
    def __init__(self, mixer:Mixer, config:dict) -> None:
        """Create a new clip Library object.\n- (required) "base_path=(str)" to define root path to search for collection subdirectories.
        \n- (optional) "valid_ext=(list)" to specify accepted file types."""
        base_path = config['base_path']
        if not os.path.isdir(base_path):
            logger.error(f'Invalid root path for library: {base_path}.')
            raise OSError
        self.mixer = mixer
        self.channels = None

        self.base_path = config['base_path']
        self.valid_ext = config['valid_extensions']
        self.strict = config['strict_distribution']
        self.default_volume =  config['volume']
        self.default_fade_in = config['fade_in']
        self.default_fade_out = config['fade_out']
        
        self.collections = {}
        self.current = Collection
        self.inactive_pool = set()
        self.active_pool = set()
        pass

    def init_library(self):
        """Initialises the Library with Collections of Clips from the base path's subdirectories."""
        logger.debug(f'Initialising Library from base path {self.base_path}...')
        titles = [d for d in os.listdir(self.base_path) if os.path.isdir(os.path.join(self.base_path, d))]
        for title in sorted(titles):
            path = os.path.join(self.base_path, title)
            names = []
            for f in os.listdir(path):
                if os.path.splitext(f)[1] in self.valid_ext:
                    names.append(f)
            if len(names) != 0:
                self.collections[title] = {'path':path, 'names':names}
                logger.debug(f'"{title}" added to Library with "{len(names)}" audio files.')
        logger.info(f'Sound Library initialised with ({len(self.collections)}) collection{plural(self.collections)}.')

    def select_collection(self, name=None, num_clips=12) -> Collection:
        """Selects a collection from within the library, prepares clips and playback pools.\n
        Will randomly select a Collection if valid name is not supplied."""
        logger.debug(f'Importing {"random " if name is None else ""}collection '
                    f'{str(name) + " " if name is not None else ""}from Library.')
        if name is not None and name not in self.collections:
            logger.warn('Requested collection name does not exist. One will be randomly selected.')
            name = None
        if name is None:
            name = random.choice(list(self.collections.keys()))
        path, names = (self.collections[name]['path'], self.collections[name]['names'])
        logger.info(f'Collection "{name}" selected with ({len(names)}) audio file{plural(names)} from: {path}')
        self.collection = Collection(title=name, path=path, names=names)
        self.clips = init_clips(self.collection)
        self.active_pool = set()
        if (pool := get_distributed(self.clips, num_clips, self.strict)) is not None:
            self.inactive_pool = pool
            self.channels = self.get_channels(self.inactive_pool)
            failed = init_sounds(self.inactive_pool, self.channels) # TODO Keeping failed returns in case they're useful
            return self.collection
        else:
            logger.error(f'Failed to retrieve a collection "{name}"! Audio files might be corrupted.')
            return None

    def get_channels(self, clip_set:set) -> dict:
        """Return dict with Channel indexes keys and Channel objects as values.
        Updates the mixer if there aren't enough channels"""
        channels = {}
        num_chans = self.mixer.get_num_channels()
        num_wanted = len(clip_set)
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

    # TODO look into callbacks instead of calling this regularly
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
        volume = self.default_volume if volume is None else volume
        fade = self.default_fade_in if fade is None else fade
        event = CLIP_END_EVENT if event is None else event
        if len(clips) == 0:
            clips = get_clip(self.inactive_pool, name=name, category=category, num_clips=num_clips)
        started = set([c for c in clips if c.play(volume, event, fade) is not None])
        self.move_to_active(started)
        return started

    def stop_clip(self, clips=set(), name=None, category=None, num_clips=1, fade=None) -> set:
        """Stop playback of Clip(s) from the active pool, selected by object, name, category, or at random.
        Clips stopped are moved to the inactive pool and are returned as a set."""
        fade = self.default_fade_out if fade is None else fade
        if len(clips) == 0:
            clips = get_clip(self.active_pool, name=name, category=category, num_clips=num_clips)
        stopped = set([c for c in clips if c.stop(fade) is not None])
        self.move_to_inactive(stopped) # TODO This should probably be done using a callback to get the end of the fadeout
        return stopped

    def modulate_volumes(self, speed=5):
        """Randomly modulate the Channel volumes for all Clip(s) in the active pool by "speed=(int)" argument as a percentage.\n
        "speed=1" is a very slow modulation, and "speed=10" would be quick, but cause noticable jumps in volume."""
        speed = speed / 100
        new_volumes = []
        for clip in self.active_pool:
            vol = clip.channel.get_volume()
            vol *= random.triangular(1-speed,1+speed,1)
            vol = max(min(vol,0.999),0.1)
            clip.channel.set_volume(vol)
            new_volumes.append(f'({clip.index}) "{clip.name}" @ {clip.channel.get_volume():.2f}')
        logger.debug(f'Channel volumes updated: {new_volumes})')

    def clips_playing(self) -> int:
        return len(self.active_pool)


#---------------
# Clip Utilities
#---------------
def init_clips(collection:Collection) -> set:
    """Initialises the Clip object for each audio file in the Collection. Sounds are not load into memory."""
    clips = set()
    for name in collection.names:
        clip = Clip(collection.path, name)
        clips.add(clip)
    #logger.debug(f'({len(clips)}) clip{plural(clips)} successfully loaded.')
    return clips

def init_sounds(clips:set, channels:dict) -> dict:
    """Initialises a Sound object for each Clip in provided Clip set.\n
    Sounds are loaded into memory and assigned mixer Channels from the provided argument.
    Returns a dictionary of any unused channels and clips that failed to build."""
    done = set()
    if len(channels) < len(clips):
        logger.warn(f'Trying to initialise {len(clips)} Sound{plural(clips)} '
                    f'from {len(channels)} Channel{plural(channels)}. Clips not assigned a '
                    f'channel will be pulled from this collection!')
    for clip in clips:
        if len(channels) == 0:
            logger.warn(f'Ran out of channels to assign!')
            break
        if clip.build_sound(channels.popitem()) is not None:
            done.add(clip)
    remaining = list(clips.difference(done))
    logger.info(f'{len(done)} Sound object{plural(done)} initialised.')
    if len(remaining) > 0:
        logger.warn(f'Unable to build {len(remaining)} Sound object{plural(remaining)}! ')
    print()
    return {'channels':channels, 'clips':remaining}

def get_distributed(clips:set, num_clips:int, strict=False) -> set:
    """Return an evenly distributed set of clip based on categories."""
    if num_clips > len(clips):
        logger.warn(f'Requesting {num_clips} clip{plural(num_clips)} but only {len(clips)} in set! '
                    f'Will return entire set.')
        selection = clips
    else:
        contents = get_contents(clips)
        logger.debug(f'Attempting to get ({num_clips}) clips from set of {get_contents(clips, True)}')
        selection = set()
        clips_per_cat = int(num_clips / len(contents))
        if clips_per_cat == 0:
            logger.info(f'Cannot select number of clips less than the number of categories. '
                        f'Rounding up to {len(contents)}.')
            clips_per_cat = 1
        for category in contents:
            try:
                selection.update(random.sample(contents[category], clips_per_cat))
            except ValueError as exception:
                logger.error(f'Could not obtain ({clips_per_cat}) clip{plural(clips_per_cat)} from "{category}" with '
                            f'({len(contents[category])}) clip{plural(contents[category])}! Exception: "{exception}"')
                if strict is True:
                    return None
                else:
                    failed = clips_per_cat - len(contents[category])
                    logger.info(f'Clip distribution not set to "strict" mode. ({failed}) unassigned clip '
                                f'slot{plural(failed)} will be selected at random.')
                    selection.update(random.sample(contents[category], len(contents[category])))
        if (unassigned := num_clips - len(selection)) > 0:
            selection.update(random.sample(clips.difference(selection), unassigned))
    logger.info(f'Returned: {get_contents(selection, count=True)}".')
    return selection

def get_contents(clips:set, count=False) -> dict:
    """Return dictionary of category:clips (key:value) pairs from a set of Clips.\n
    - "count=True" returns number of clips instead of a list of Clips."""
    contents = {}
    for clip in clips:
        category = clip.category
        if count:
            contents[category] = contents.get(category, 0) + 1
        else:
            if category in contents:
                contents[category].append(clip)
            else:
                contents[category] = [clip]
    return contents

def clip_by_name(clips:set, name:str) -> Clip:
    """Return specific Clip by name from given set of Clips. If no clip is found, will silently return None."""
    for clip in clips:
        if clip.name == name:
            return clip
    return None

def clip_by_channel(clips:set, chan:Channel) -> set:
    """Looks for a specific Channel attached to provided set of Clips."""
    found = set()
    for clip in clips:
        if clip.channel == chan:
            found.add(clip)
    if len(found) > 1:
        logger.warn(f'Channel {chan} is assigned to multiple Clip objects: {[c.name for c in found]}')
    return found

def get_clip(clips:set, name=None, category=None, num_clips=1) -> set:
    """Return clip(s) by name, category, or total random from provided set of clips."""
    if name is not None:
        if (clip := clip_by_name(name, clips)) is None:
            logger.warn(f'Requested clip "{name}" not in provided set. Skipping.')
            return None
        return set(clip)
    if category:
        contents = get_contents(clips)
        if (clips := contents.get(category)) is None:
            logger.warn(f'Category "{category}" not found in set. Ignoring request.')
            return None
    available = len(clips)
    if available == 0:
        logger.warn(f'No clips available. Skipping request.')
        return None
    if num_clips > available:
        logger.debug(f'Requested "{num_clips}" clip{plural(num_clips)} from {("[" + category + "] in ") if category is not None else ""} '
                        f'with "{available}" Clip{plural(available)}. {("Returning [" + str(available) + "] instead") if available > 0 else "Skipping request"}.')
    return set([clip for clip in random.sample(clips, min(num_clips, available))])

def get_category(length):
    """Return matching category based on input length vs category breakpoints."""
    index = bisect.bisect_right(list(cat[1] for cat in CATEGORIES), length) - 1
    return CATEGORIES[index][0]