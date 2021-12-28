

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
CAT_LOOP = 2

class Collection:
    """Houses a set of clips as a collection within a library.\n
    Requires root path and set of clip file names as arguments on creation."""

    @staticmethod
    def get_category(length):
        index = bisect.bisect_right(list(cat[1] for cat in CATEGORIES), length) - 1
        return CATEGORIES[index][0]

    def get_contents(self) -> dict:
        """Return dictionary to describe the category contents of the Collection"""
        contents = {}
        for clip in self.clips.keys():
            cat = self.clips[clip]['category']
            if contents.get(cat) is None:
                contents[cat] = 1
            else:
                contents[cat] = contents[cat] + 1
        return contents

    def get_clips(self) -> dict:
        """Return dictionary containing clip dictionaries with Sound objects and all necessary clip data."""
        clips = {}
        for name in self.names:
            sound = Sound(os.path.join(self.path, name))
            length = sound.get_length()
            category = Collection.get_category(length)            
            clips[name] = {'sound':sound, 'category':category, 'length':length, 'looping': length > CATEGORIES[CAT_LOOP][1]}
        return clips

    def get_random_clip(self) -> Sound:
        return random.choice(self.clips)

    def get_random_from_cats(self) -> dict:
        

    def __init__(self, path: str, names: list) -> None:
        self.path = path
        self.names = names
        self.clips = self.get_clips()
        self.contents = self.get_contents()
        pass

    def __str__(self) -> str:
        return str(self.contents)


class Library:
    """An object for managing Collections of audio clips for playback."""

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    def __init__(self, base_path, valid_ext: list, logger=logger) -> None:
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
                new_collection = Collection(root, audio_clip_paths)
                self.collections.append(new_collection)
                self.logger.debug(f'[{len(self.collections)-1}] {root} added to clip library with {len(new_collection.names)} audio files.')

    def get_collection(self, index=None) -> Collection:
        """Return a collection from within the library.\n
        Will randomly select a Collection if valid index is not supplied."""

        try:
            collection = self.collections[index]
        except TypeError:
            self.logger.debug('Collection index not supplied or is invalid. One will be randomly selected.')
        except IndexError:
            self.logger.error('Supplied collection index is out of range. One will be randomly selected.')
        finally:
            collection = random.choice(self.collections)

        self.logger.debug(f'Collection {collection.path} selected containing {len(collection.clips)} clips.')

        return collection

