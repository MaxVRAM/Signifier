#  _________ .__  .__
#  \_   ___ \|  | |__|_____
#  /    \  \/|  | |  \____ \
#  \     \___|  |_|  |  |_> >
#   \______  /____/__|   __/
#          \/        |__|

"""
Signifier Clip class.
"""

from __future__ import annotations

import os
import time
import bisect
import random

from pygame.mixer import Sound, Channel

#from src.utils import SigLog
#logger = None

class Clip:
    """
    Clip objects hold sound file information, its Sound object
    and its associated Channel, once playback has been triggerd.
    """

    def __init__(self, root: str, name: str, categories: dict, logger) -> None:
        self.root = root
        self.name = name
        #self.logger = SigLog.get_logger(f'Sig.{name}')
        self.logger = logger
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
        details = (
            f'{self.name}, "{self.category}", "{"looping" if self.looping else "one-shot"}", '
            f'{self.length:.2f}s on chan ({"NONE" if self.channel is None else self.index}).'
        )
        return details

    # -----------------
    # Playback methods
    # -----------------
    def play(self, **kwargs) -> Clip:
        """
        Starts playback of Clip's Sound object with optional `fade=(int)` time in ms
        and "event=(int)" to produce an end of clip callback. Returns itself if successful.
        """
        if self.channel is None:
            self.logger.warning(f'Cannot play Clip "{self.name}". Not assigned to Channel.')
            return None
        elif self.channel.get_busy():
            self.logger.warning(
                f'Cannot play Channel "{self.index}" assigned to "{self.name}". Already playing audio.'
            )
            return None
        else:
            loop_num = (
                -1
                if self.looping
                else random.randint(self.loop_range[0], self.loop_range[1])
            )
            self.channel.play(self.sound, fade_ms=kwargs.get("fade", 0), loops=loop_num)
            self.sound.set_volume(kwargs.get("volume", 1))
            self.started = time.time()
            if (event := kwargs.get("event", None)) is not None:
                self.channel.set_endevent(event)
            self.logger.debug(f'Playing clip "{self.name}" on channel ({self.index}).')
            return self

    def stop(self, **kwargs) -> Clip:
        """
        Stops the sound playing from the Clip immediately, otherwise supply `fade=(int)` time in ms.
        """
        if self.channel is None:
            self.logger.warning(f'Cannot stop "{self.name}". Not assigned to Channel.')
            return None
        elif not self.channel.get_busy():
            self.logger.warning(
                f'Cannot stop "{self.name}". Channel ({self.index}) reporting idle state.'
            )
            return None
        else:
            if (fade := kwargs.get("fade", 0)) > 0:
                self.sound.fadeout(fade)
                self.logger.debug(
                    f'Clip "{self.name}" playing on Channel ({self.index}) is now fading out over {fade}ms.'
                )
                return self
            else:
                self.sound.stop()
                self.logger.debug(
                    f'Clip "{self.name}" playing on Channel ({self.index}) has been stopped immediately.'
                )
                return self

    def get_volume(self) -> float:
        """
        Return the volume of this audio clip object (0-1).
        """
        if self.sound is None:
            self.logger.warning(
                f'Cannot get volume of "{self.name}". Not assigned to Sound object.'
            )
        else:
            return self.channel.get_volume()

    def set_volume(self, volume: float):
        """
        Set the volume of this audio clip object (0-1).
        """
        if self.sound is None:
            self.logger.warning(
                f'Cannot set volume of "{self.name}". Not assigned to Sound object.'
            )
        else:
            self.channel.set_volume(volume)

    # ---------------
    # Clip utilities
    # ---------------
    def set_channel(self, chan: tuple) -> Channel:
        """
        Binds supplied (index, Channel) tuple to Clip.
        """
        if chan[1].get_sound():
            self.logger.warning(
                f'Channel ({chan[0]}) [{chan[1]}] busy state: {chan[1].get_busy()}".'
            )
            return None
        self.index = chan[0]
        self.channel = chan[1]
        return self.channel


    def build_sound(self, chan: tuple) -> Clip:
        """
        Loads the Clip's audio file into memory as a new Sound object and assign it a mixer Channel.
        """
        self.sound = Sound(self.path)
        self.index = chan[0]
        self.set_channel(chan)
        if not self.sound or not self.channel:
            self.logger.warning(f'Could not build "{self.name}"!')
            return None
        self.logger.debug(f'Sound "{self.path}" added to channel ({self.index}) [{self.channel}]')
        return self


    def remove_channel(self) -> Channel:
        """
        Removes Channel and index number from Clip, returning the Channel object.
        """
        if (chan := self.channel) is None:
            self.logger.warning(
                f'No Channel object assigned to "{self.name}", cannot remove. Skipping request.'
            )
            return None
        self.index = None
        self.channel = None
        self.logger.debug(f'Channel object and index removed from "{self.name}".')
        return chan


    def determine_category(self, categories: dict):
        """
        Determine clip category and loop properties from its length bisected against category breakpoints.
        """
        contents = [(k, categories[k]["threshold"]) for k in categories.keys()]
        contents.sort(key=lambda x: x[1])
        self.category = contents[
            bisect.bisect_right(list(c[1] for c in contents), self.length) - 1
        ][0]
        self.looping = categories[self.category]["is_loop"]
        self.loop_range = categories[self.category]["loop_range"]
