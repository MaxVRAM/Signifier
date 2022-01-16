
#  _________ .__  .__        
#  \_   ___ \|  | |__|_____  
#  /    \  \/|  | |  \____ \ 
#  \     \___|  |_|  |  |_> >
#   \______  /____/__|   __/ 
#          \/        |__|    

"""Module hosting the audio clip object."""

from __future__ import annotations
import logging, os, random, bisect, time
from pygame.mixer import Sound, Channel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
            loop_num = -1 if self.looping else random.randint(self.loop_range[0], self.loop_range[1])
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
            logger.warn(f'Cannot stop "{self.name}". Channel ({self.index}) reporting idle state.')
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

    #---------------
    # Clip utilities
    #---------------
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
        #logger.debug(f'Loaded clip: {self}.')
        return self

    def determine_category(self, categories:dict):
        """Determine clip category and loop properties from its length bisected against category breakpoints."""
        cats = [(k, categories[k]['threshold']) for k in categories.keys()]
        cats.sort(key=lambda x: x[1])
        self.category = cats[bisect.bisect_right(list(c[1] for c in cats), self.length)-1][0]
        self.looping = categories[self.category]['is_loop']
        self.loop_range = categories[self.category]['loop_range']

    #---------------------
    # Magic/static methods
    #---------------------
    def __init__(self, root:str, name:str, categories:dict) -> None:
        """Initialises a new Clip object.\nUse additional {True} arguement to load audio 
        file into memory as new Sound object."""
        self.root = root
        self.name = name
        self.path = os.path.join(root, name)
        self.length = Sound(self.path).get_length()
        self.category = None
        self.looping = None
        self.sound = None
        self.channel = None
        self.index = None
        self.determine_category(categories)
        pass

    def __str__(self) -> str:
        details = (f'{self.name}, "{self.category}", "{"looping" if self.looping else "one-shot"}", '
                   f'{self.length:.2f}s on chan ({"NONE" if self.channel is None else self.index}).')
        return details