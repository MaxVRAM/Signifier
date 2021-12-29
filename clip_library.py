

#  _________ .__  .__         .____    ._____.                              
#  \_   ___ \|  | |__|_____   |    |   |__\_ |______________ _______ ___.__.
#  /    \  \/|  | |  \____ \  |    |   |  || __ \_  __ \__  \\_  __ <   |  |
#  \     \___|  |_|  |  |_> > |    |___|  || \_\ \  | \// __ \|  | \/\___  |
#   \______  /____/__|   __/  |_______ \__||___  /__|  (____  /__|   / ____|
#          \/        |__|             \/       \/           \/       \/     

"""Module to manage a Library of audio Clips."""


import logging, os, random, bisect
from pygame.mixer import Sound

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CATEGORIES = [('oneshot', 0), ('short', 5), ('medium', 10), ('loop', 30)]
CATEGORY_LOOP = 2

class Clip:
    """Clip objects hold sound file information and a Pygame Sound object."""

    @staticmethod
    def get_category(length):
        """Return matching category based on input length vs category breakpoints."""
        index = bisect.bisect_right(list(cat[1] for cat in CATEGORIES), length) - 1
        return CATEGORIES[index][0]

    def build_sound(self) -> str:
        """Loads the Clip's audio file into memory as a new Sound object."""
        self.sound = Sound(self.path)
        logger.debug(f'{self.name} loaded into memory as new Sound object.')
        return self.name

    def __init__(self, root:str, name:str, load=False) -> None:
        """Initialises a new Clip object.\nUse additional {True} arguement to load audio 
        file into memory as new Sound object."""
        self.root = root
        self.name = name
        self.path = os.path.join(root, name)
        sound_object = Sound(self.path)
        self.length = sound_object.get_length()
        self.category = self.get_category(self.length)
        self.looping = self.category >= CATEGORIES[CATEGORY_LOOP][0]
        self.sound = sound_object if load else None
        pass

    def __str__(self) -> str:
        details = (f'{self.name} [{self.category}{", looping" if self.looping else ""}] '
                   f'{self.length}s ({"LOADED" if self.sound else "NOT LOADED"})')
        return details

class Collection:
    """Houses a set of clips as a collection within a library."""

    path = ''
    names = []
    clips = set()
    title = 'default'

    # Clip selection mechanics
    #-------------------------
    def get_clip(self, name=None) -> Clip:
        """Pull specific clip by name if supplied in arguements, otherwise pick one at random."""
        if len(self.clips) == 0:
            logger.warn(f'Cannot get Clip from empty {self.title} Collection.')
            return None
        if name is not None:
            for c in self.clips:
                if c.name == name:
                    return self.pull_clip(c)
        else:
            return self.pull_clip(random.choice(tuple(self.clips)))

    def get_from_category(self, category:str, num_clips=1):
        """Pull random clip from a specific category, or several as a set if {num_clips} argument supplied."""
        clips = self.get_contents()[category]
        if len(clips) == 0:
            logger.warn(f'Cannot pull random Clip from empty category {category} in {self.title} Collection.')
            return None
        if num_clips == 1:
            return self.pull_clip(random.choice(tuple(clips)))
        else:
            if num_clips > len(clips):
                logger.debug(f'Cannot pull {num_clips} clips from {category} in {self.title} with only {len(clips)} clips. Pulling {len(clips)} instead.')
            return set(self.pull_clip(c) for c in random.sample(clips, min(num_clips, len(clips))))

    def get_distributed(self, num_clips=12) -> set:
        """Return an evenly distributed set of clips based on Collection's categories."""
        contents = self.get_contents()
        selection = set()
        clips_per_cat = int(num_clips / len(contents))
        for category in contents:
            selection.update(self.get_from_category(category, clips_per_cat))
        logger.info(f'{self.title} returned the following distributed clips: {self.get_contents(clip_set=selection, count=True)}.')
        return selection
    
    # Clip management
    #----------------
    def push_clip(self, clip:Clip, force=False) -> Clip:
        """Add Clip object to Collection if it is not currently in the Collections {clips} set.\n
        The Clip name must be registered with the Collection unless "force=True" argument is supplied to add it."""
        if clip in self.clips:
            logger.warn(f'{clip.name} already in {self.title} Clip set. Skipping.')
            return None
        if clip.name in [clip.name for clip in self.clips]:
            self.clips.add(clip)
            logger.info(f'{clip.name} was pushed into {self.title}.')
            return clip
        elif force:
            self.names.append(clip.name)
            self.clips.add(clip)
            logger.info(f'{clip.name} now registered with {self.title} Collection and Clip has been pushed.')
            return clip
        else:
            logger.debug(f'{clip.name} not registered to {self.title}. Use "force=True" argument to register it.')
            return None
    
    def pull_clip(self, clip:Clip) -> Clip:
        """Pull clip from Collection.\nThis does not remove its name from the registry, allowing it to be re-added."""
        try:
            self.clips.remove(clip)
            logger.info(f'{clip.name} pulled from {self.title}.')
            return clip
        except KeyError:
            logger.debug(f'Clip {clip.name} does not exist in {self.title}. Cannot pull.')
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

    def build_sounds(self, names=None):
        """Builds the Sound object for each Clip in the Collection.\n
        If {names} list argument is supplied, only Sounds with a matching clip name will be built."""
        built = []
        for clip in self.clips:
            if names is None or clip.name in names:
                built.append(clip.build_sound())
        logger.debug(f'Successfully built {len(built)} Sound objects.')
        if names is not None and len(diff := names - built) > 0:
            logger.warn(f'Unable to built {len(diff)} Sound objects from supplied list: {diff}.')


    def build_clips(self, names=None):
        """Builds the Clip object for each audio file in the Collection.\n
        If {names} list argument is supplied, only matching file names will be built."""
        logger.debug(f'{self.title} is building {len(self.names)} Clips objects from audio files.')
        for name in self.names:
            if names is None or name in names:
                self.clips.add(Clip(self.path, name))
                logger.info(f'{self.title} created Clip object from {name}.')
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

    def __init__(self, base_path, valid_ext:list) -> None:
        """Create a new library."""
        if not os.path.isdir(base_path):
            raise OSError
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
                logger.debug(f'[{title}] added to Library with {len(names)} audio files.')
        print()
        logger.info(f'Library initialised from {self.base_path} with {len(self.collections)} collections.')
        print()

    def get_collection(self, index=None) -> Collection:
        """Return a collection from within the library.\n
        Will randomly select a Collection if valid index is not supplied."""
        logger.info(f'Importing new Collection from Library.')
        try:
            collection = self.collections[index]
        except TypeError:
            logger.info('Collection index not supplied or is invalid. One will be randomly selected.')
        except IndexError:
            logger.warn('Supplied collection index is out of range. One will be randomly selected.')
        finally:
            collection = random.choice(self.collections)
        collection.build_clips()
        logger.debug(f'{collection}')
        return collection

