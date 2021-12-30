

#  _________ .__  .__         .____    ._____.                              
#  \_   ___ \|  | |__|_____   |    |   |__\_ |______________ _______ ___.__.
#  /    \  \/|  | |  \____ \  |    |   |  || __ \_  __ \__  \\_  __ <   |  |
#  \     \___|  |_|  |  |_> > |    |___|  || \_\ \  | \// __ \|  | \/\___  |
#   \______  /____/__|   __/  |_______ \__||___  /__|  (____  /__|   / ____|
#          \/        |__|             \/       \/           \/       \/     

"""Module to manage a Library of audio Clips."""


import logging, os, random, bisect
from pygame.mixer import Sound, Channel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CATEGORIES = [('oneshot', 0), ('short', 5), ('medium', 10), ('loop', 30)]
CATEGORY_LOOP = 2

class Clip:
    """Clip objects hold sound file information, its Sound object 
    and its associated Channel, once playback has been triggerd."""

    @staticmethod
    def get_category(length):
        """Return matching category based on input length vs category breakpoints."""
        index = bisect.bisect_right(list(cat[1] for cat in CATEGORIES), length) - 1
        return CATEGORIES[index][0]

    def remove_channel(self):
        if (chan := self.channel) is None:
            logger.warn(f'No Channel object assigned to [{self.name}], cannot remove. Skipping request.')
            return None
        self.channel = None
        logger.inf(f'Channel object removed from [{self.name}].')
        return chan

    def assign_channel(self) -> Channel:
        self.channel = Channel()

    def build_sound(self) -> str:
        """Loads the Clip's audio file into memory as a new Sound object."""
        self.sound = Sound(self.path)
        logger.debug(f'Loaded clip into memory as new Sound object: {self}.')
        return self.name

    def __init__(self, id:int, root:str, name:str, load=False) -> None:
        """Initialises a new Clip object.\nUse additional {True} arguement to load audio 
        file into memory as new Sound object."""
        self.id = id
        self.root = root
        self.name = name
        self.path = os.path.join(root, name)
        sound_object = Sound(self.path)
        self.length = sound_object.get_length()
        self.category = self.get_category(self.length)
        self.looping = self.category >= CATEGORIES[CATEGORY_LOOP][0]
        self.sound = sound_object if load else None
        self.channel = None
        pass

    def __str__(self) -> str:
        details = (f'{self.name} [{self.category}{", looping" if self.looping else ""}] '
                   f'{self.length:.2f}s ({"LOADED" if self.sound else "NOT LOADED"})')
        return details

class Collection:
    """Houses a set of clips as a collection within a library."""

    path = ''
    names = []
    clips = set()
    title = 'default'

    # Clip selection mechanics
    #-------------------------
    @staticmethod
    def clip_by_name(name:str, clip_set:set):
        """Return specific Clip by name from given set of Clips. If no clip is found, will silently return None."""
        for clip in clip_set:
            if clip.name == name:
                return clip
        return None

    def get_clip(self, name=None, category=None, num_clips=1):
        """Return specific clip by name if supplied in arguements, otherwise a random clip will be returned.\n
        The category and number of clips to return can be specified with "category=(str)" and "num_clips=(int)", respectively."""  
        clips = self.clips
        if name is not None:
            if (clip := Collection.clip_by_name(name, clips)) is None:
                logger.warn(f'[{name}] not available from [{self.title}]. Skipping request.')
                return None
            return self.pull_clip(clip)
        if category:
            contents = self.get_contents()
            if category not in contents:
                logger.warn(f'Category [{category}] not found in [{self.title}]. Skipping request.')
                return None
            clips = contents.get(category)
        num = len(clips)
        if num_clips > num:
            logger.debug(f'Requested [{num_clips}] clips from {("[" + category + "] in ") if category is not None else ""}'
                         f'[{self.title}] with [{num}] clip{"s" if num != 1 else ""}. '
                         f'{("Returning [" + num + "] instead") if num > 0 else "Skipping request"}.')
        if num == 0:
            return None
        return set(self.pull_clip(clip) for clip in random.sample(clips, min(num_clips, num)))

    def get_from_category(self, category:str, num_clips=1):
        """Get random clip from a specific category, or several as a set if "num_clips=(int)" argument supplied."""
        clips = self.get_contents()[category]
        if len(clips) == 0:
            logger.warn(f'{category} in {self.title} is empty. Cannot get random Clip.')
            return None
        if num_clips == 1:
            return self.pull_clip(random.choice(tuple(clips)))
        else:
            if num_clips > len(clips):
                logger.debug(f'Cannot pull {num_clips} clips from {category} in {self.title}. '
                             f'Only {len(clips)} clips availalbe. Pulling {len(clips)} instead.')
            return set(self.pull_clip(c) for c in random.sample(clips, min(num_clips, len(clips))))

    def get_distributed(self, num_clips=12) -> set:
        """Return an evenly distributed set of clips based on Collection's categories."""
        contents = self.get_contents()
        selection = set()
        clips_per_cat = int(num_clips / len(contents))
        for category in contents:
            selection.update(self.get_clip(category=category, num_clips=clips_per_cat))
        logger.info(f'{self.title} returned the following distributed clips: {self.get_contents(clip_set=selection, count=True)}.')
        return selection
    
    # Clip management
    #----------------

    # def release_finished(self) -> list:
    #     """Removes Channels from finished or invalid associations Clips.
    #     Returns a list of (clip, channel) tuples of removed associations."""
    #     clips, chans = []
    #     for clip in self.clips:
    #         if (chan := clip.channel) is not None:
    #             if chan.get_busy() and chan.get_sound() == clip.sound:
    #                 continue 
    #             if chan.get_sound() != clip.sound:
    #                 logger.info(f'{clip.name} no longer assigned to its associated Channel. Removing Channel from Clip object.')
    #             elif not chan.get_busy():
    #                 logger.info(f'No playback on Channel associated to {clip.name}. Removing Channel from Clip object.')
    #             clips.append(clip)
    #             chans.append(clip.remove_channel())
    #     if len(clips) == 0 or len(chans) == 0:
    #         return None
    #     logger.debug(f'[{len(chans)}] Channel{"" if len(chans) == 1 else "s"} removed from '
    #                  f'[{len(clips)}] Clip{"" if len(clips) == 1 else "s"} in [{self.title}].')
    #     return list(zip(clips, chans))
        

    def push_clip(self, clip:Clip, force=False) -> Clip:
        """Add Clip object to Collection if it is not currently in the Collections {clips} set.\n
        The Clip name must be registered with the Collection unless "force=True" argument is supplied to add it."""
        if clip in self.clips:
            logger.warn(f'{clip.name} already in {self.title} Clip set. Skipping.')
            return None
        if clip.name in [name for name in self.names]:
            self.clips.add(clip)
            #logger.info(f'{clip.name} pushed into {self.title}.')
            return clip
        elif force:
            self.names.append(clip.name)
            self.clips.add(clip)
            logger.info(f'{clip.name} not in {self.title}. Clip has been forced and filename now registered.')
            return clip
        else:
            logger.debug(f'{clip.name} not registered to {self.title}. Use "force=True" argument to register it.')
            return None
    
    def pull_clip(self, clip:Clip) -> Clip:
        """Pull clip from Collection.\nThis does not remove its name from the registry, allowing it to be re-added."""
        if clip.name not in self.names:
            logger.warn(f'{clip.name} is not registered with {self.title}. Skipping request.')
            return None
        try:
            self.clips.remove(clip)
            return clip
        except KeyError:
            logger.debug(f'{clip.name} is not currently available from {self.title}. Skipping request.')
            return None

    def purge_clip(self, clip:Clip):
        """Remove Clip and unregister it from Collection."""
        try:
            self.clips.remove(clip)
        except KeyError:
            pass
        try:
            self.names.remove(clip.name)
        except KeyError:
            logger.warn(f'Clip {clip.name} is not registered with {self.title}, so cannot be purged.')
            pass

    def get_contents(self, clip_set=None, count=False) -> dict:
        """Return dictionary of categories as keys and a list of its clips as values.\n
        Providing additional argument "count=True" returns clip count instead of clip list.\n
        Supplying "clip_set=(set)" returns categorised content of supplied clip set instead of this Collection."""
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

    def initialise_sounds(self, names=None):
        """Defines a new Sound and Channel object for each Clip in the Collection.\n
        If {names} list argument is supplied, only Sounds with a matching clip name will be built."""
        clips = []
        for clip in self.clips:
            if names is None or clip.name in names:
                if (c := clip.build_sound()) is not None:
                    clips.append(c)
        logger.debug(f'Built {len(clips)} Sound objects.')
        if names is not None and len(diff := names - clips) > 0:
            logger.warn(f'Unable to build {len(diff)} Sound objects from supplied list: {diff}.')

    def initialise_clips(self, names=None):
        """Initialises the Clip object for each audio file in the Collection.\n
        If a "names=[str,]" list argument is supplied, only matching file names will be built."""
        logger.debug(f'{self.title} is building {len(self.names)} Clips objects from audio files.')
        for name in self.names:
            if names is None or name in names:
                self.clips.add(Clip(self.path, name))
            else:
                logger.warn(f'{name} from {self.title} could not be built. Either no match was found or something went wrong.')

    def get_copy(self, title:str, clip_set=None):
        """Returns a copy of this Collection a new Collection object with a different title.\n
        A custom set of clips can be supplied in the "clip_set=" argument if a different selection of clips is desired."""
        return Collection(title=title, path=self.path, names=self.names, clips=self.clips if clip_set is None else clip_set)

    # Magic methods
    #--------------
    def __init__(self, title=title, path=path, names=names, clips=clips) -> None:
        self.title = title
        self.path = path
        self.names = names
        self.clips = clips
        pass

    def __str__(self) -> str:
        return f'{self.title} Collection {self.path} contains {self.get_contents(count=True)}.'


class Library:
    """An object for managing Collections of audio clips for playback."""

    def __init__(self, base_path:str, valid_ext=['.wav']) -> None:
        """Create a new audio playback Library.\n- (required) "base_path=(str)" to define root path to search for collection subdirectories.
        \n- (optional) "valid_ext=(list)" to specify accepted file types."""
        assert os.path.isdir(base_path)
        self.base_path = base_path
        self.valid_ext = valid_ext
        self.collections = []
        pass

    def init_library(self):
        """Gather all subfolders containing audio files from the root path as Collections with their containing audio files."""
        logger.debug(f'Initialising Library from root path {self.base_path}...')
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
                logger.debug(f'[{title}] added to Library with [{len(names)}] audio files.')
        print()
        logger.info(f'Library initialised with [{len(self.collections)}] collections from base path [{self.base_path}].')
        print()

    def get_collection(self, index=None) -> Collection:
        """Return a collection from within the library.\n
        Will randomly select a Collection if valid index is not supplied."""
        logger.info(f'Importing {"random " if index is None else ""}Collection '
                    f'{("[" + index + "] ") if index is not None else ""}from Library.')
        try:
            collection = self.collections[index]
        except TypeError:
            logger.info(f'Collection index {"not supplied" if index is None else ("[" + index + "] not valid")}. '
                        f'One will be randomly selected.')
        except IndexError:
            logger.warn('Supplied collection index is out of range. One will be randomly selected.')
        finally:
            collection = random.choice(self.collections)
        collection.build_clips()
        logger.debug(f'{collection}')
        return collection

