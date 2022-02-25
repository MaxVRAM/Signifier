#  _________                                    .__  __  .__
#  \_   ___ \  ____   _____ ______   ____  _____|__|/  |_|__| ____   ____
#  /    \  \/ /  _ \ /     \\____ \ /  _ \/  ___/  \   __\  |/  _ \ /    \
#  \     \___(  <_> )  Y Y  \  |_> >  <_> )___ \|  ||  | |  (  <_> )   |  \
#   \______  /\____/|__|_|  /   __/ \____/____  >__||__| |__|\____/|___|  /
#          \/             \/|__|              \/                        \/

"""
Signifier module to manage the audio clip playback.
"""

from __future__ import annotations
from src.sigprocess import ModuleProcess
from src.sigmodule import SigModule
from src.clip import Clip
from src.clipUtils import *
from src.utils import validate_library
from src.utils import plural
import pygame as pg

import os
import sys
import time
import random
import logging
import schedule

from threading import Thread

# Allows PyGame to run without a screen
os.environ["SDL_VIDEODRIVER"] = "dummy"
# Silence PyGame greeting mesage
stdout = sys.__stdout__
stderr = sys.__stderr__
sys.stdout = open(os.devnull, "w")
sys.stderr = open(os.devnull, "w")
sys.stdout = stdout
sys.stderr = stderr


class Composition(SigModule):
    """
    Audio playback composition manager module.
    """

    def __init__(self, name: str, config: dict, *args, **kwargs) -> None:
        super().__init__(name, config, *args, **kwargs)
        self.clip_event = pg.USEREVENT + 1

    def create_process(self):
        """
        Called by the module's `initialise()` method to return a
        module-specific object.
        """
        self.process = CompositionProcess(self)


class CompositionProcess(ModuleProcess, Thread):
    """
    Controls the playback of an audio clip library.
    """

    def __init__(self, parent: Composition) -> None:
        super().__init__(parent)
        # Composition assets
        self.clip_event = parent.clip_event
        self.channels = None
        self.collections = {}
        self.current_collection = {}
        self.base_path = self.config.get("base_path")
        self.fade_in = self.config.get("fade_in_ms", 1000)
        self.fade_out = self.config.get("fade_out_ms", 2000)
        self.mix_volume = self.config.get('mix_volume', 0.5)
        self.inactive_pool = set()
        self.active_pool = set()
        self.active_jobs = {}
        self.jobs = self.config["jobs"]
        self.jobs_dict = {
            "collection": self.collection_job,
            "clip_selection": self.clip_selection_job,
            "volume": self.volume_job,
        }
        if self.init_mixer() and self.init_library():
            schedule.logger.setLevel(
                logging.DEBUG if self.config.get("debug", True) else logging.INFO
            )
            if self.parent_pipe.writable:
                self.parent_pipe.send("initialised")

    def init_mixer(self) -> bool:
        """
        Initialises PyGame audio mixer.
        """
        self.logger.debug("Initialising audio mixer...")
        pg.mixer.pre_init(
            frequency=self.config["sample_rate"],
            size=self.config["bit_size"],
            channels=1,
            buffer=self.config["buffer"],
        )
        try:
            pg.mixer.init()
        except pg.error as exception:
            self.failed(f'[init_mixer] {exception}')
            return False
        pg.init()
        mix = pg.mixer.get_init()
        logger.info(f"Audio mixer initialised with {mix[1]}-bit samples "
                    f"@ {mix[0]} Hz over {mix[2]} channel{plural(mix[2])}.")
        return True

    def init_library(self) -> bool:
        """
        Initialises the Clip Manager with a library of Clips.
        """
        self.logger.debug(f"Library path: {self.base_path}...")
        if not validate_library(self.config):
            self.failed("Specified audio library path is invalid.")
            return False
        titles = [
            d
            for d in os.listdir(self.base_path)
            if os.path.isdir(os.path.join(self.base_path, d))
        ]
        for title in sorted(titles):
            path = os.path.join(self.base_path, title)
            names = []
            for f in os.listdir(path):
                if os.path.splitext(f)[1][1:] in self.config["valid_extensions"]:
                    names.append(f)
            if len(names) != 0:
                self.collections[title] = {"path": path, "names": names}
        self.logger.debug(
            f"[{self.module_name}] initialised with "
            f"({len(self.collections)}) "
            f"collection{plural(self.collections)}."
        )
        return True

    def pre_run(self) -> bool:
        """
        Module-specific Process run preparation.
        """
        self.collection_job()
        return True

    def mid_run(self):
        """
        Module-specific Process run commands. Where the bulk of the module's
        computation occurs.
        """
        try:
            pg.mixer.get_init()
        except pg.error as exception:
            self.failed(exception)
        schedule.run_pending()
        self.manage_audio_events()


    def pre_shutdown(self):
        """
        Module-specific shutdown preparation.
        """
        schedule.clear()
        try:
            pg.mixer.get_init()
            self.stop_all_clips()
            self.wait_for_silence()
        except pg.error:
            pass
        pg.mixer.quit()
        pg.quit()
        if pg.mixer.get_init() is None:
            self.logger.info(f'[{self.module_name}] audio mixer released.')

    def select_collection(self, **kwargs):
        """
        Selects a collection from the library, prepares clips and playback pools.\n
        Will randomly select a collection if valid name is not supplied.
        """
        name = kwargs.get("name", None)
        num_clips = kwargs.get("num_clips", self.config["default_pool_size"])
        self.logger.debug(
            f'Importing {"random " if name is None else ""}collection '
            f'{(str(name) + " ") if name is not None else ""}from library.'
        )
        if name is not None and name not in self.collections:
            self.logger.warning(
                "Requested collection name does not exist. "
                "One will be randomly selected."
            )
            name = None
        if name is None:
            print(f'Collection "keys": {self.collections.keys()}')
            name = random.choice(list(self.collections.keys()))
        path, names = (self.collections[name]["path"], self.collections[name]["names"])
        self.logger.info(
            f'Collection "{name}" selected with ({len(names)}) '
            f"audio file{plural(names)}"
        )
        self.current_collection = {"title": name, "path": path, "names": names}
        # Build clips from collection to populate clip manager
        self.clips = set(
            [Clip(path, name, self.config["categories"]) for name in names]
        )
        self.active_pool = set()
        if (
            pool := get_distributed(
                self.clips,
                num_clips,
                strict=self.config.get("strict_distribution", False),
            )
        ) is not None:
            self.inactive_pool = pool
            self.channels = self.get_channels(self.inactive_pool)
            init_sounds(self.inactive_pool, self.channels)
            self.metrics_pusher.update(f"{self.module_name}_collection", name)
            return self.current_collection
        else:
            self.logger.error(
                f'Failed to retrieve a collection "{name}"! '
                f"Audio files might be corrupted."
            )
            return None

    def get_channels(self, clip_set: set) -> dict:
        """
        Return dict with Channel indexes keys and Channel objects as values.
        Updates the mixer if there aren't enough channels
        """
        channels = {}
        num_chans = pg.mixer.get_num_channels()
        num_wanted = len(clip_set)
        # Update the audio mixer channel count if required
        if num_chans != num_wanted:
            pg.mixer.set_num_channels(num_wanted)
            num_chans = pg.mixer.get_num_channels()
            self.logger.debug(f"Mixer now has {num_chans} channels.")
        for i in range(num_chans):
            channels[i] = pg.mixer.Channel(i)
            channels[i].set_volume(self.mix_volume)
        return channels

    # ----------------
    # Clip management
    # ----------------

    def stop_random_clip(self):
        """
        Stop a randomly selected audio clip from the active pool.
        """
        self.stop_clip()

    def stop_all_clips(self, **kwargs):
        """
        Tell all active clips to stop playing, emptying the mixer of\
        active channels.\n `fade_time=(int)` the number of milliseconds active\
        clips should take to fade their volumes before stopping playback.\
        If no parameter is provided, the clip_manager's `fade_out`\
        value from the config.json will be used.\n Use 'disable_events=True'\
        to prevent misfiring audio jobs that use clip end events to launch more.
        """
        fade = kwargs.get("fade_time", self.fade_out)
        if pg.mixer.get_init():
            if pg.mixer.get_busy():
                self.logger.debug(f"Stopping audio clips: {fade}ms fade...")
                if kwargs.get("disable_events", False) is True:
                    self.clear_events()
                pg.mixer.fadeout(fade)

    def wait_for_silence(self):
        """
        Stops the main thread until all channels have faded out.
        """
        self.logger.debug("Waiting for audio mixer to release all channels...")
        if pg.mixer.get_init():
            start_time = time.time()
            while (
                time.time() < start_time + self.fade_out / 1000 + 0.1
                and pg.mixer.get_busy()
            ):
                time.sleep(0.01)
        self.logger.debug("Mixer empty.")

    def manage_audio_events(self):
        """
        Check for audio playback completion events,
        call the clip manager to clean them up.
        """
        for event in pg.event.get():
            if event.type == self.clip_event:
                self.logger.info(f"Clip end event: {event}")
                self.check_finished()

    def move_to_inactive(self, clips: set):
        """
        Supplied list of Clip(s) are moved from active to inactive pool.
        """
        for clip in clips:
            self.active_pool.remove(clip)
            self.inactive_pool.add(clip)
            self.logger.debug(f"MOVED: {clip.name} | active >>> INACTIVE.")

    def move_to_active(self, clips: set):
        """
        Supplied list of Clip(s) are moved from inactive to active pool.
        """
        for clip in clips:
            self.inactive_pool.remove(clip)
            self.active_pool.add(clip)
            self.logger.debug(f"MOVED: {clip.name} | inactive >>> ACTIVE.")

    def check_finished(self) -> set:
        """
        Checks active pool for lingering Clips finished playback, and moves them to the inactive pool.
        Returns a set containing any clips moved.
        """
        finished = set()
        for clip in self.active_pool:
            if not clip.channel.get_busy():
                finished.add(clip)
        if len(finished) > 0:
            self.move_to_inactive(finished)
        return finished

    def play_clip(self, clips=set(), **kwargs) -> set:
        """
        Start playback of Clip(s) from the inactive pool, selected by object, name, category, or at random.
        Clips started are moved to the active pool and are returned as a set.
        """
        if len(clips) == 0:
            clips = get_clip(self.inactive_pool, **kwargs)
        started = set([c for c in clips if c.play(**kwargs) is not None])
        self.move_to_active(started)
        return started

    def stop_clip(self, clips=set(), *args, **kwargs) -> set:
        """
        Stop playback of Clip(s) from the active pool, selected by object, name, category, or at random.
        Clips stopped are moved to the inactive pool and are returned as a set. `'balance'` in args will
        remove clips based on the most active category, overriding category in arguments if provided.
        """
        fade = kwargs.get("fade", self.fade_out)
        if len(clips) == 0:
            # Finds the category with the greatest number of active clips.
            if "balance" in args:
                contents = get_contents(self.active_pool)
                clips = contents[max(contents, key=contents.get)]
                kwargs.update("category", None)
            clips = get_clip(self.active_pool, kwargs)
        stopped = set([c for c in clips if c.stop(fade) is not None])
        self.move_to_inactive(stopped)
        return stopped

    def modulate_volumes(self, **kwargs):
        """
        Randomly modulate the Channel volumes for all Clip(s) in the active pool.\n
        - "speed=(int)" is the maximum volume jump per tick as a percentage of the total
        volume. 1 is slow, 10 is very quick.\n - "weight=(float)" is a signed normalised
        float (-1.0 to 1.0) that weighs the random steps towards either direction.
        """
        speed = kwargs.get("speed", 5) / 100
        weight = kwargs.get("weight", 1) * speed
        new_volumes = []
        for clip in self.active_pool:
            vol = clip.channel.get_volume()
            vol *= random.triangular(1 - speed, 1 + speed, 1 + weight)
            vol = max(min(vol, 0.999), 0.1)
            clip.channel.set_volume(vol)
            new_volumes.append(f"({clip.index}) @ {clip.channel.get_volume():.2f}")

    def clips_playing(self) -> int:
        """
        Return number of active clips.
        """
        return len(self.active_pool)

    def clear_events(self):
        """
        Clears the end event callbacks from all clips in the active pool.
        """
        for clip in self.active_pool:
            clip.channel.set_endevent()

    #       ____.     ___.
    #      |    | ____\_ |__   ______
    #      |    |/  _ \| __ \ /  ___/
    #  /\__|    (  <_> ) \_\ \\___ \
    #  \________|\____/|___  /____  >
    #                      \/     \/

    def collection_job(self, **kwargs):
        """
        Select a new collection from the clip manager, replacing any\
        currently loaded collection.
        """
        job_params = self.jobs["collection"]["parameters"]
        pool_size = kwargs.get(
            "pool_size", job_params.get("pool_size", self.config["default_pool_size"])
        )
        start_clips = kwargs.get("start_clips", job_params.get("start_clips", 1))
        self.stop_job(ignore="collection")
        self.stop_all_clips()
        self.wait_for_silence()
        if (
            self.select_collection(name=kwargs.get("collection"), pool_size=pool_size)
            is None
        ):
            self.logger.warning(
                f"Selecting collection with [{kwargs}] "
                f"returned no results. Attempting "
                f"random selection..."
            )
            if self.select_collection(pool_size=pool_size) is None:
                self.failed(f"Could not source audio clip collection.")
                return None
        self.start_jobs()
        self.clip_selection_job(start_num=start_clips)

    def clip_selection_job(self, **kwargs):
        """
        Ensure the clip manager is playing an appropriate number of clips,\
        and move any finished clips still lingering in the active pool to
        the inactive pool.\n - `quiet_level=(int)` the lowest number of
        concurrent clips playing before looking for more to play.\n -
        `busy_level=(int)` the highest number of concurrent clips playing
        before stopping active clips.
        """
        job_params = self.jobs["clip_selection"]["parameters"]
        quiet_level = kwargs.get("quiet_level", job_params["quiet_level"])
        busy_level = kwargs.get("busy_level", job_params["busy_level"])
        start_num = kwargs.get("start_num", 1)
        self.check_finished()
        if self.clips_playing() < quiet_level:
            self.play_clip(num_clips=start_num)
        elif self.clips_playing() > busy_level:
            self.stop_clip("balance")

    def volume_job(self, **kwargs):
        """
        Randomly modulate the Channel volumes for all Clip(s) in the\
        active pool.\n - `speed=(int)` is the maximum volume jump per tick
        as a percentage of the total volume. 1 is slow, 10 is very quick.\n -
        "weight=(float)" is a signed normalised float (-1.0 to 1.0) that
        weighs the random steps towards either direction.
        """
        job_params = self.jobs["volume"]["parameters"]
        speed = kwargs.get("speed", job_params["speed"])
        weight = kwargs.get("weight", job_params["weight"])
        self.modulate_volumes(speed=speed, weight=weight)

    def start_jobs(self, *args):
        """
        Start jobs matching names provided as string arguments.\n
        Jobs will only start if it is registered in the jobs dict,\
        not in the active jobs pool, and where it's tagged service\
        and the job ifself are both enabled in config file.\n
        If no args are supplied, all jobs that fit those criteria\
        will be started.
        """
        if len(args) == 0:
            jobs = set(self.jobs_dict.keys())
        else:
            jobs = set(args)
        jobs.intersection_update(self.jobs_dict.keys())
        jobs.difference_update(self.active_jobs.keys())
        jobs.intersection_update(set(k for k, v in self.jobs.items() if v["enabled"]))
        for job in jobs:
            self.active_jobs[job] = schedule.every(self.jobs[job]["timer"]).seconds.do(
                self.jobs_dict[job]
            )
        self.logger.debug(f"({len(self.active_jobs)}) jobs currently scheduled.")

    def stop_job(self, *args, **kwargs):
        """
        Stop jobs matching names provided as an interable of string arguments.
        Providing no string args will stop ALL jobs.\n
        - `ignore=(str)` will prevent the job with provided name from being stopped.\n
        - Jobs will only be stopped if they are found in the active pool.
        """
        if len(args) == 0:
            jobs = set(self.jobs_dict.keys())
        else:
            jobs = set(args)
        if (ignore := kwargs.get("ignore", None)) is not None:
            jobs.remove(ignore)
        jobs.intersection_update(self.active_jobs.keys())
        self.logger.debug(f"Stopping jobs: {jobs}")
        for job in jobs:
            schedule.cancel_job(self.active_jobs.pop(job))
