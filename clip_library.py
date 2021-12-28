

#  _________ .__  .__         .____    ._____.                              
#  \_   ___ \|  | |__|_____   |    |   |__\_ |______________ _______ ___.__.
#  /    \  \/|  | |  \____ \  |    |   |  || __ \_  __ \__  \\_  __ <   |  |
#  \     \___|  |_|  |  |_> > |    |___|  || \_\ \  | \// __ \|  | \/\___  |
#   \______  /____/__|   __/  |_______ \__||___  /__|  (____  /__|   / ____|
#          \/        |__|             \/       \/           \/       \/     

"""Module for a Library containing Collections of audio clips."""


import logging, os, random, bisect
from pygame.mixer import Sound


CATEGORIES = [('oneshot', 0), ('short', 5), ('medium', 10), ('loop', 30)]
CATEGORY_LOOP = 2

class Clip:
    @staticmethod
    def get_category(length):
        """Return lowest matching length of category based on input length."""
        index = bisect.bisect_right(list(cat[1] for cat in CATEGORIES), length) - 1
        return CATEGORIES[index][0]

    def __init__(self, root:str, name:str) -> None:
        self.root = root
        self.name = name
        self.path = os.path.join(root, name)
        self.sound = Sound(self.path)
        self.length = self.sound.get_length()
        self.category = self.get_category(self.length)
        self.looping = self.category >= CATEGORIES[CATEGORY_LOOP][0]
        pass


class Collection:
    """Houses a set of clips as a collection within a library.\n
    Requires root path and set of clip file names as arguments on creation."""

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    path = ''
    names = []
    clips = set()
    title = 'default'

    def category_contents(self) -> dict:
        """Return dictionary to describe the category contents of the Collection"""
        contents = {}
        for clip in self.clips:
            cat = clip.category
            if contents.get(cat) is None:
                contents[cat] = 1
            else:
                contents[cat] = contents[cat] + 1
        return contents

    def specific_clip(self, name:str) -> Clip:
        """Return specific audio clip based on string argument as name."""
        for c in self.clips:
            if c.name == name:
                return self.remove_clip(c)
        return None

    def clip_at_random(self) -> Clip:
        """Return random clip from entire Collection."""
        return self.remove_clip(random.choice(tuple(self.clips)))

    def clip_from_category(self, category:str) -> dict:
        """Return random clip from specific category."""
        clips = [clip for clip in self.clips if category is clip.category]
        return self.remove_clip(random.choice(tuple(clips)))

    def add_clip(self, clip:Clip) -> Clip:
        """Add clip if it's name is registered but the Clip object itself isn't found in the Collection."""
        if clip not in self.clips[clip] and clip.name in [name for name in self.clips[clip.name]]:
            self.clips.add(clip)
            self.logger.info(f'Added clip {clip.name} to {self.title} Collection.')
            return clip
        else:
            self.logger.debug(f'Cannot add clip {clip.name} to {self.title}, as it not an original member.')
            return None
    
    def remove_clip(self, clip:Clip) -> Clip:
        """Remove clip from Collection.\nThis does not remove its name from the registry, allowing it to be re-added."""
        if clip in self.clips:
            self.clips.remove(clip)
            self.logger.info(f'Removed clip {clip.name} from {self.title} Collection.')
            return clip
        else:
            self.logger.debug(f'Clip {clip.name} does not exist in {self.title}. Cannot remove.')
            return None

    def load(self, path: str, names: list):
        self.path = path
        self.names = names
        self.clips = set()
        for name in self.names:
            self.clips.add(Clip(self.path, name))
        return self

    def __init__(self, logger=logger, title='default') -> None:
        self.logger = logger
        self.title = title
        pass

    def __str__(self) -> str:
        return f'{self.path} with {self.category_contents()}'


class Library:
    """An object for managing Collections of audio clips for playback."""

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    def __init__(self, base_path, valid_ext:list, logger=logger) -> None:
        """Create a new library."""
        if not os.path.isdir(base_path):
            raise OSError
        self.base_path = base_path
        self.valid_ext = valid_ext
        self.collections = []
        self.logger = logger
        pass

    def init_library(self):
        """Gather all subfolders containing audio files from the root path to create Collections for the library."""
        for (root, dirs, files) in sorted(os.walk(self.base_path)):
            audio_clip_paths = []
            # Only inlclude valid file extensions
            for f in files:
                if os.path.splitext(f)[1] in self.valid_ext:
                    audio_clip_paths.append(f)
            # If the clip set is not empty, add it to the library as a new collection
            if len(audio_clip_paths) > 0:
                new_collection = Collection(self.logger)
                new_collection.load(root, audio_clip_paths)
                self.collections.append(new_collection)
                self.logger.debug(f'[{len(self.collections)-1}] {root} added to clip library with {len(new_collection.names)} audio files.')

    def get_collection(self, index=None) -> Collection:
        """Return a collection from within the library.\n
        Will randomly select a Collection if valid index is not supplied."""
        
        print()

        try:
            collection = self.collections[index]
        except TypeError:
            self.logger.debug('Collection index not supplied or is invalid. One will be randomly selected.')
        except IndexError:
            self.logger.error('Supplied collection index is out of range. One will be randomly selected.')
        finally:
            collection = random.choice(self.collections)

        self.logger.debug(f'Collection selected: {collection}')

        return collection

