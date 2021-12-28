

#  _________ .__  .__         .____    ._____.                              
#  \_   ___ \|  | |__|_____   |    |   |__\_ |______________ _______ ___.__.
#  /    \  \/|  | |  \____ \  |    |   |  || __ \_  __ \__  \\_  __ <   |  |
#  \     \___|  |_|  |  |_> > |    |___|  || \_\ \  | \// __ \|  | \/\___  |
#   \______  /____/__|   __/  |_______ \__||___  /__|  (____  /__|   / ____|
#          \/        |__|             \/       \/           \/       \/     

"""Module for a Library containing Collections of audio clips."""


import logging, os, random, sys

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

    class Collection:
        """Houses a set of clips as a collection within a library.\n
        Requires root path and set of clip file names as arguments on creation."""

        path = ''
        clips = set()

        def __init__(self, path: str, clips: set) -> None:
            self.path = path
            self.clips = clips
            pass

        def get_paths(self) -> set:
            """Return completed file paths to all clips within the collection."""
            clip_paths = set()
            for clip in self.clips:
                clip_paths.add(os.path.join(self.path, clip))
            return clip_paths


    def init_library(self):
        """Gather all subfolders containing wav files as a Collection for the library."""

        for (root, dirs, files) in sorted(os.walk(self.base_path)):
            audio_clips = set()
            # Only inlclude valid file extensions
            for f in files:
                if os.path.splitext(f)[1] in self.valid_ext:
                    audio_clips.add(f)
            # If the clip set is not empty, add it to the library as a new collection
            if len(audio_clips) > 0:
                new_collection = Library.Collection(root, audio_clips)
                self.collections.append(new_collection)
                self.logger.debug(f'[{len(self.collections)-1}] {root} added to clip library with {len(new_collection.clips)} audio files.')


    def get_collection(self, index=None) -> Collection:
        """Return a set of absolute audio file paths from a collection within the library.\n
        Will randomly select a set if no index argument is supplied."""

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