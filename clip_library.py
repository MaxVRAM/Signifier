

#  _________ .__  .__         .____    ._____.                              
#  \_   ___ \|  | |__|_____   |    |   |__\_ |______________ _______ ___.__.
#  /    \  \/|  | |  \____ \  |    |   |  || __ \_  __ \__  \\_  __ <   |  |
#  \     \___|  |_|  |  |_> > |    |___|  || \_\ \  | \// __ \|  | \/\___  |
#   \______  /____/__|   __/  |_______ \__||___  /__|  (____  /__|   / ____|
#          \/        |__|             \/       \/           \/       \/     

"""Module to manage a Library of audio Clips."""


import logging, os, random, bisect, time, copy
from pygame.mixer import Sound, Channel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CATEGORIES = [('oneshot', 0), ('short', 5), ('medium', 10), ('loop', 30)]
LOOP_CATEGORIES = ['medium','loop']
LOOP_RANGE = [0, 6]


# Opulent logging utility
def plural(num:int) -> str:
    return "" if num == 0 else "s"


class Clip:
    """Clip objects hold sound file information, its Sound object 
    and its associated Channel, once playback has been triggerd."""

    default_fade = (3000, 2000)
    #-----------------
    # Playback methods
    #-----------------
    def play(self, volume=0.5, event=None, fade=default_fade[1]):
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

    def stop(self, fade=default_fade[0]):
        """Stops the sound playing from the Clip immediately, otherwise supply "fade_time=(int)" in ms."""
        if self.channel is None:
            logger.warn(f'Cannot stop "{self.name}". Not assigned to Channel.')
            return None
        elif not self.channel.get_busy():
            logger.warn(f'Cannot stop Channel "{self.index}" assigned to "{self.name}". Not playing audio.')
            return None
        else:
            if fade > 0:
                self.channel.fadeout(fade)
                return self
            else:
                self.channel.stop()
                return self

    def get_volume(self) -> float:
        if self.sound is None:
            logger.warn(f'Cannot get volume of "{self.name}". Not assigned to Sound object.')
        else:
            return self.sound.get_volume()

    def set_volume(self, volume:float):
        if self.sound is None:
            logger.warn(f'Cannot set volume of "{self.name}". Not assigned to Sound object.')
        else:
            self.sound.set_volume(volume)

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

    def remove_channel(self):
        """Removes Channel and index number from Clip, returning the Channel object."""
        if (chan := self.channel) is None:
            logger.warn(f'No Channel object assigned to "{self.name}", cannot remove. Skipping request.')
            return None
        self.index = None
        self.channel = None
        logger.debug(f'Channel object and index removed from "{self.name}".')
        return chan

    def build_sound(self, chan:tuple):
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
    @staticmethod
    def get_category(length):
        """Return matching category based on input length vs category breakpoints."""
        index = bisect.bisect_right(list(cat[1] for cat in CATEGORIES), length) - 1
        return CATEGORIES[index][0]

    def __init__(self, root:str, name:str, load=False, fade=default_fade) -> None:
        """Initialises a new Clip object.\nUse additional {True} arguement to load audio 
        file into memory as new Sound object."""
        self.root = root
        self.name = name
        self.path = os.path.join(root, name)
        sound_object = Sound(self.path)
        self.length = sound_object.get_length()
        self.category = self.get_category(self.length)
        self.looping = self.category in LOOP_CATEGORIES
        self.sound = sound_object if load else None
        self.channel = None
        self.index = None
        self.default_fade = fade
        pass

    def __str__(self) -> str:
        details = (f'{self.name}, "{self.category}", "{"looping" if self.looping else "one-shot"}", '
                   f'{self.length:.2f}s on '
                   f'chan ({"NONE" if self.channel is None else self.index}), fade ({self.default_fade})')
        return details




class Collection:
    """Houses a set of clips as a collection within a Library."""
    path = ''
    names = []
    clips = set()
    title = 'default'
    default_fade = (3000, 2000)


    #-------------------------
    # Collection Clip playback
    #-------------------------
    def play_clip(self, name=None, category=None, num_clips=1, volume=0.5, fade=default_fade[1], event=None) -> set:
        """Return set of clip(s) by name, category, or at random, remove from Collection and begin playback.\n
        Specify clip ""name=(str)" or "category=(str)" by name and/or amount with "num_clips=(int)"."""
        clips = self.get_clip(name=name, category=category, num_clips=num_clips, keep=False)
        for clip in clips:
            clip.play(volume=volume, event=event, fade=fade)
        return clips
        
    #-------------------------
    # Clip selection mechanics
    #-------------------------
    @staticmethod
    def clip_by_name(name:str, clip_set:set):
        """Return specific Clip by name from given set of Clips. If no clip is found, will silently return None."""
        for clip in clip_set:
            if clip.name == name:
                return clip
        return None

    def clip_by_channel(self, chan:Channel):
        """Looks for a specific Channel and returns the Clip its attached to."""
        for clip in self.clips:
            if clip.channel == chan:
                return clip
        return None

    def get_clip(self, name=None, category=None, num_clips=1, keep=True) -> set:
        """Return clip(s) by name, category, or at random and remove it from the Collection.\n
        Specify clip ""name=(str)" or "category=(str)" by name and/or amount with "num_clips=(int)"."""
        #clips_to_get = set()
        clips = self.clips
        if name is not None:
            if (clip := Collection.clip_by_name(name, clips)) is None:
                logger.warn(f'"{name}" not available from "{self.title}". Skipping request.')
            return self.pull_clip(set(clip), keep=keep)
        if category:
            contents = self.get_contents()
            if category not in contents:
                logger.warn(f'Category "{category}" not found in "{self.title}". Failed to get clips.')
                return None
            clips = contents.get(category)
        num = len(clips)
        if num == 0:
            logger.warn(f'No clips in "{self.title}" available! Skipping request.')
            return None
        if num_clips > num:
            logger.debug(f'Requested "{num_clips}" clip{plural(num_clips)} from {("[" + category + "] in ") if category is not None else ""}'
                         f'"{self.title}" with "{num}" Clip{plural(num)}. '
                         f'{("Returning [" + str(num) + "] instead") if num > 0 else "Skipping request"}.')

        #clips_to_get.add(set([(clip) for clip in random.sample(clips, min(num_clips, num))]))
        clip_set = set([clip for clip in random.sample(clips, min(num_clips, num))])
        return self.pull_clip(clip_set, keep=keep)
        #return self.pull_clip(clips_to_get)

    def get_finished(self, num_clips=1, keep=True) -> set:
        """Return any finished clips, removing them from the current Collection."""
        finished = set()
        for clip in self.clips:
            if not clip.channel.get_busy():
                logger.info(f'Clip "{clip.name}" finished. Removing from Collection.')
                finished.add(self.pull_clip(set(clip), keep))
            if len(finished) >= num_clips:
                return finished
        return finished

    def get_distributed(self, num_clips=12, keep=True) -> set:
        """Return an evenly distributed set of clips based on Collection's categories. Use "keep=False" to pull clips from Collection."""
        if num_clips > len(self.clips):
            logger.warn(f'Requesting "{num_clips}" Clips from "{self.title}" which has only "{len(self.clips)}"! '
                        f'Will return all available Clips from the Collection.')
            selection = self.get_clip(num_clips=len(self.clips))
        else:
            contents = self.get_contents()
            selection = set()
            clips_per_cat = int(num_clips / len(contents))
            if clips_per_cat == 0:
                logger.info(f'Cannot select number of clips less than the number of categories. '
                            f'Rounding up to {len(contents)}.')
                clips_per_cat = 1
            for category in contents:
                selection.update(self.get_clip(category=category, num_clips=clips_per_cat))
        logger.info(f'Returned {self.get_contents(clip_set=selection, count=True)} distributed from "{self.title}".')
        return selection
    
    #----------------
    # Clip management
    #----------------
    def push_clip(self, clip_set:set, force=False) -> set:
        """Add set of Clip object(s) to Collection if it is not currently in the Collections {clips} set.\n
        Clip must be registered with the Collection unless "force=True" argument is supplied."""
        failed = set()
        for clip in clip_set:
            if clip in self.clips:
                logger.warn(f'"{clip.name}" already in "{self.title}" Clip set. Skipping.')
                failed.add(clip)
            elif clip.name in [name for name in self.names]:
                self.clips.add(clip)
                logger.debug(f'"{clip.name}" pushed into "{self.title}".') # TODO uncomment when done dev
            elif force:
                self.names.append(clip.name)
                self.clips.add(clip)
                logger.debug(f'"{clip.name}" not in "{self.title}". Clip has been forced and filename now registered.')
            else:
                logger.debug(f'"{clip.name}" not registered to "{self.title}". Use "force=True" argument to register it.')
                failed.add(clip)
        return failed
    
    def pull_clip(self, clip_set:set, keep=True) -> set:
        """Supply Clip object(s) to pull from the Collection.\n
        This does not remove them from the registry, allowing them to be re-added."""
        pulled = set()
        for clip in clip_set:
            if clip.name not in self.names:
                logger.warn(f'"{clip.name}" is not registered with "{self.title}". Skipping.')
            try:
                if keep == False:
                    self.clips.remove(clip)
                    logger.debug(f'"{clip.name}" has been removed from "{self.title}".') # TODO uncomment when done dev
                pulled.add(clip)
            except KeyError:
                logger.info(f'"{clip.name}" is not currently available in "{self.title}". Skipping request.')
        return pulled

    def purge_clip(self, clip:Clip):
        """Remove Clip and unregister it from Collection."""
        try:
            self.clips.remove(clip)
        except KeyError:
            pass
        try:
            self.names.remove(clip.name)
        except KeyError:
            logger.warn(f'Clip "{clip.name}" is not registered with "{self.title}", so cannot be purged.')
            pass

    def get_contents(self, clip_set=None, count=False) -> dict:
        """Return dictionary of categories as keys and a list of its clips as values.\n
        - "clip_set=(set)" returns categorised content of supplied clip set instead of this Collection.\n
        - "count=True" returns clip count instead of clip list."""
        contents = {}
        clip_set = self.clips if clip_set is None else clip_set
        for clip in clip_set:
            category = clip.category
            if count:
                num = contents.get(category, 0) + 1
                contents[category] = num
            else:
                if category in contents:
                    contents[category].append(clip)
                else:
                    contents[category] = [clip]
        return contents

    def init_sounds(self, channels:list, spec_clips=None) -> dict:
        """Initialises the Sound object for each Clip in the Collection. Sounds are loaded into memory 
        and assigned with provided mixer channels. "spec_clips=set(clips) can be used to specify clips.
        Returns a dictionary of any unused channels and/or clip that failed to build."""
        done = []
        remaining = set(spec_clips if spec_clips is not None else self.clips)
        if len(channels) < len(self.clips):
            logger.warn(f'Trying to initialise {len(self.clips)} sound{plural(len(self.clips))} '
                        f'with only {len(channels)} channel{plural(len(channels))}. Clips not assigned a '
                        f'channel will be pulled from this collection!')
        for clip in remaining:
            if len(channels) == 0:
                logger.warn(f'Ran out of channels to assign!')
                break
            if clip in self.clips:
                if clip.build_sound(channels.pop(0)) is not None:
                    done.append(clip)

        remaining = list(remaining.difference(done))

        logger.info(f'"{len(done)}" Sound object{plural(len(done))} initialised for "{self.title}".')
        if len(remaining) > 0:
            logger.warn(f'Unable to build "{len(remaining)}" Sound object{plural(len(remaining))}! '
                        f'Removing them from "{self.title}".')
            for clip in remaining:
                self.pull_clip(clip, keep=False)
            logger.warn(f'"{self.title}" now has "{len(self.clips)}" Clip{plural(len(self.clips))}.')           
        return {'unused_chans':channels, 'failed_clips':remaining}

    def init_clips(self):
        """Initialises the Clip object for each audio file in the Collection. Sounds are not load into memory."""
        clips = []
        for clip in self.clips:
            clip = Clip(self.path, clip.name, fade=self.default_fade)
            clips.append(clip)
            self.clips.add(clip)
        logger.info(f'{len(clips)} Clip object{plural(len(clips))} initialised for {self.title}.')

    def get_copy(self, title:str, keep_clips=False):
        """Returns a copy of this Collection a new Collection object with a different title.\n
        No clips will be returned unless "keep_clips=True" is supplied."""
        return Collection(title=title, path=self.path, names=self.names, fade=self.default_fade, clips=self.clips if keep_clips else set())


    #--------------
    # Magic methods
    #--------------
    def __init__(self, title=title, path=path, names=names, clips=clips, fade=default_fade) -> None:
        self.title = title
        self.path = path
        self.names = names
        self.clips = clips
        Collection.default_fade = fade
        pass

    def __str__(self) -> str:
        return f'"{self.title}" contains: {self.get_contents(count=True)}.'


class Library:
    """Used to create Collections of audio clips for playback."""
    def __init__(self, base_path:str, fade:tuple, valid_ext=['.wav']) -> None:
        """Create a new clip Library object.\n- (required) "base_path=(str)" to define root path to search for collection subdirectories.
        \n- (optional) "valid_ext=(list)" to specify accepted file types."""
        if not os.path.isdir(base_path):
            logger.error(f'Invalid root path for library: {base_path}.')
            raise OSError
        self.base_path = base_path
        self.valid_ext = valid_ext
        self.default_fade = fade
        self.collections = []
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
            # Ignore subdirectory if it doesn't contain any audio files
            if len(names) != 0:
                new_collection = Collection(title=title, path=path, names=names)
                self.collections.append(new_collection)
                # TODO uncomment when done dev
                logger.debug(f'"{title}" added to Library with "{len(names)}" audio files.')
        logger.info(f'Library initialised with "{len(self.collections)}" collection{plural(len(self.collections))}.')
        print()

    def select_collection(self, index=None, num_clips=12) -> Collection:
        """Selects a collection from within the library and assigns it to the Collection pools.\n
        Will randomly select a Collection if valid index is not supplied."""
        logger.debug(f'Importing {"random " if index is None else ""}Collection '
                    f'{("[" + index + "] ") if index is not None else ""}from Library.')
        try:
            new_col = self.collections[index]
        except TypeError:
            pass
        except IndexError:
            logger.warn('Supplied collection index is out of range. One will be randomly selected.')
        finally:
            new_col = random.choice(self.collections)

        logger.info(f'{new_col}')

        # Copy Collection into instance then select and initialise
        self.collection = copy.deepcopy(new_col)
        self.collection.clips = self.collection.get_distributed(num_clips)
        self.collection.init_clips()
        self.active_pool = None
        self.inactive_pool = self.collection.clips

        return self.collection


    