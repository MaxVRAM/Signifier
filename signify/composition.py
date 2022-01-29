
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

import os
import time
import random
import logging
import schedule
import pygame as pg

from signify.utils import plural
from signify.clipUtils import *
from signify.clip import Clip

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Composition():
    """
    Audio playback composition manager module.
    """
    def __init__(self, config:dict, args=(), kwargs=None) -> None:
        self.config = config
        self.enabled = self.config.get('enabled', False)
        self.event = pg.USEREVENT + 1
        self.manager = None
        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Clip Manager.
        """
        logger.info(f'Updating Composition module configuration...')
        if self.enabled:
            if config.get('enabled', False) is False:
                self.config = config
                self.stop()
            else:
                self.stop()
                self.config = config
                self.initialise()
                self.start()
        else:
            if config.get('enabled', False) is True:
                self.config = config
                self.start()
            else:
                self.config = config


    def initialise(self):
        """
        Initialises a new Clip Manager object.
        """
        if self.enabled:
            if self.manager is None:
                self.manager = self.ClipManager(self)
                logger.debug(f'Clip Manager module initialised.')
            else:
                logger.warning(f'Clip Manager module already initialised!')
        else:
            logger.warning(f'Cannot create Clip Manager process, module not enabled!')


    def start(self):
        """
        Starts the Clip Manager routine.
        """
        if self.enabled:
            if self.manager is not None:
                if self.manager is not None:
                    self.get_collection()
                    logger.info(f'Clip Manager started.')
                else:
                    logger.warning(f'Cannot start Clip Manager, already running!')
            else:
                logger.warning(f'Trying to start Clip Manager but module not initialised!')
        else:
            logger.debug(f'Ignoring request to start Clip Manager, module is not enabled.')


    def stop(self):
        """
        Shuts down the Composition module.
        """
        if self.manager is not None:
            logger.debug(f'Composition module shutting down...')
            self.stop_scheduler()
            self.stop_all_clips()
            self.wait_for_silence()
            self.manager = None
            logger.info(f'Composition module stopped.')
        else:
            logger.debug('Ignoring request to stop Composition, module is not enabled.')


    def stop_scheduler():
        """
        Simply calls `schedule.clear()`. Placeholder in case more needs to be added.
        """
        schedule.clear()



    class ClipManager():
        """
        Clip Manager class to manage "collections" of audio clips for playback.
        """
        def __init__(self, parent:Composition) -> None:
            """
            Create a new Clip Manager object.
            """
            if not os.path.isdir(parent.config['base_path']):
                logger.error(f'Invalid root path for library: {parent.config["base_path"]}.')
                raise OSError
            self.config = parent.config
            self.mixer = pg.mixer
            self.event = parent.event
            self.channels = None
            self.collections = {}
            self.current_collection = {}
            self.inactive_pool = set()
            self.active_pool = set()
            self.active_jobs = {}
            self.jobs = parent.config['jobs']
            self.jobs_dict = {
                'collection': self.get_collection,
                'clip_selection': self.automate_composition,
                'volume': self.modulate_volumes
            }

            self.init_mixer()
            self.init_library()


        def init_mixer(self):
            """
            Initialises PyGame audio mixer.
            """
            logger.info('Initialising audio mixer...')
            pg.mixer.pre_init(
                frequency=self.config['sample_rate'],
                size=self.config['bit_size'],
                channels=1,
                buffer=self.config['buffer'])
            pg.mixer.init()
            pg.init()
            logger.debug(f'Audio mixer parameters: {pg.mixer.get_init()}')


        def init_library(self):
            """
            Initialises the Clip Manager with a library of Clips.
            """
            logger.debug(f'Building clip library from base path {self.config["base_path"]}...')
            titles = [d for d in os.listdir(self.config['base_path']) \
                if os.path.isdir(os.path.join(self.config['base_path'], d))]
            for title in sorted(titles):
                path = os.path.join(self.config['base_path'], title)
                names = []
                for f in os.listdir(path):
                    if os.path.splitext(f)[1] in self.config['valid_extensions']:
                        names.append(f)
                if len(names) != 0:
                    self.collections[title] = {'path':path, 'names':names}
            logger.debug(f'Clip Manager initialised with ({len(self.collections)}) '
                        f'collection{plural(self.collections)}.')


        def select_collection(self, name=None, num_clips=12):
            """
            Selects a collection from the library, prepares clips and playback pools.\n
            Will randomly select a collection if valid name is not supplied.
            """
            logger.debug(f'Importing {"random " if name is None else ""}collection '
                        f'{(str(name) + " ") if name is not None else ""}from library.')
            if name is not None and name not in self.collections:
                logger.warn('Requested collection name does not exist. One will be randomly selected.')
                name = None
            if name is None:
                name = random.choice(list(self.collections.keys()))
            path, names = (self.collections[name]['path'], self.collections[name]['names'])
            logger.info(f'Collection "{name}" selected with ({len(names)}) audio file{plural(names)} from: {path}')
            self.current_collection = {'title':name, 'path':path, 'names':names}
            # Build clips from collection to populate clip manager and initialise the clip pools 
            self.clips = set([Clip(path, name, self.config['categories']) for name in names])
            self.active_pool = set()
            if (pool := get_distributed(self.clips, num_clips, self.config['strict_distribution'])) is not None:
                self.inactive_pool = pool
                self.channels = self.get_channels(self.inactive_pool)
                failed = init_sounds(self.inactive_pool, self.channels) # TODO Keeping failed in case they're useful
                return self.current_collection
            else:
                logger.error(f'Failed to retrieve a collection "{name}"! Audio files might be corrupted.')
                return None


        def get_channels(self, clip_set:set) -> dict:
            """
            Return dict with Channel indexes keys and Channel objects as values.
            Updates the mixer if there aren't enough channels
            """
            channels = {}
            num_chans = self.mixer.get_num_channels()
            num_wanted = len(clip_set)
            # Update the audio mixer channel count if required
            if num_chans != num_wanted:
                self.mixer.set_num_channels(num_wanted)
                num_chans = self.mixer.get_num_channels()
                logger.debug(f'Mixer now has {num_chans} channels.')
                print()
            for i in range(num_chans):
                channels[i] = self.mixer.Channel(i)
            return channels


        #----------------
        # Clip management
        #----------------


        def stop_random_clip(self):
            """
            Stop a randomly selected audio clip from the active pool.
            """
            self.stop_clip()


        def stop_all_clips(self, fade_time=None, disable_events=True):
            """
            Tell all active clips to stop playing, emptying the mixer of\
            active channels.\n `fade_time=(int)` the number of milliseconds active\
            clips should take to fade their volumes before stopping playback.\
            If no parameter is provided, the clip_manager's `fade_out`\
            value from the config.json will be used.\n Use 'disable_events=True'\
            to prevent misfiring audio jobs that use clip end events to launch more.
            """
            fade_time = self.config['fade_out'] if fade_time is None\
                else fade_time
            if pg.mixer.get_init():
                if pg.mixer.get_busy():
                    logger.info(f'Stopping audio clips: {fade_time}ms fade...')
                    if disable_events is True:
                        self.clear_events()
                    pg.mixer.fadeout(fade_time)


        def manage_audio_events(self):
            """
            Check for audio playback completion events,
            call the clip manager to clean them up.
            """
            for event in pg.event.get():
                if event.type == self.event:
                    logger.info(f'Clip end event: {event}')
                    self.check_finished()


        def wait_for_silence(self):
            """
            Stops the main thread until all challens have faded out.
            """
            logger.debug('Waiting for audio mixer to release all channels...')
            while pg.mixer.get_busy():
                time.sleep(0.1)
            logger.info('Mixer empty.')



        def move_to_inactive(self, clips:set):
            """
            Supplied list of Clip(s) are moved from active to inactive pool.
            """
            for clip in clips:
                self.active_pool.remove(clip)
                self.inactive_pool.add(clip)
                logger.debug(f'MOVED: {clip.name} | active >>> INACTIVE.')


        def move_to_active(self, clips:set):
            """
            Supplied list of Clip(s) are moved from inactive to active pool.
            """
            for clip in clips:
                self.inactive_pool.remove(clip)
                self.active_pool.add(clip)
                logger.debug(f'MOVED: {clip.name} | inactive >>> ACTIVE.')


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


        def play_clip(self, clips=set(), name=None, category=None, num_clips=1, volume=None, fade=None, event=None) -> set:
            """
            Start playback of Clip(s) from the inactive pool, selected by object, name, category, or at random.
            Clips started are moved to the active pool and are returned as a set.
            """
            volume = self.config['volume'] if volume is None else volume
            fade = self.config['fade_in'] if fade is None else fade
            event = self.event if event is None else event
            if len(clips) == 0:
                clips = get_clip(self.inactive_pool, name=name, category=category, num_clips=num_clips)
            started = set([c for c in clips if c.play(volume, event, fade) is not None])
            self.move_to_active(started)
            return started


        def stop_clip(self, clips=set(), name=None, category=None, num_clips=1, fade=None, *args) -> set:
            """
            Stop playback of Clip(s) from the active pool, selected by object, name, category, or at random.
            Clips stopped are moved to the inactive pool and are returned as a set. `'balance'` in args will
            remove clips based on the most active category, overriding category in arguments if provided.
            """
            fade = self.config['fade_out'] if fade is None else fade
            if len(clips) == 0:
                if 'balance' in args:
                    cats = get_contents(self.active_pool)
                    clips = cats[max(cats, key = cats.get)]
                    category = None
                clips = get_clip(self.active_pool, name=name, category=category, num_clips=num_clips)
            stopped = set([c for c in clips if c.stop(fade) is not None])
            self.move_to_inactive(stopped)
            return stopped


        def modulate_volumes(self, speed, weight):
            """
            Randomly modulate the Channel volumes for all Clip(s) in the active pool.\n 
            - "speed=(int)" is the maximum volume jump per tick as a percentage of the total 
            volume. 1 is slow, 10 is very quick.\n - "weight=(float)" is a signed normalised 
            float (-1.0 to 1.0) that weighs the random steps towards either direction.
            """
            speed = speed / 100
            weight = weight * speed
            new_volumes = []
            for clip in self.active_pool:
                vol = clip.channel.get_volume()
                vol *= random.triangular(1-speed,1+speed,1+weight)
                vol = max(min(vol,0.999),0.1)
                clip.channel.set_volume(vol)
                new_volumes.append(f'({clip.index}) @ {clip.channel.get_volume():.2f}')


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

        def get_collection(self):
            """
            Select a new collection from the clip manager, replacing any\
            currently loaded collection.
            """
            job_params = self.jobs['collection']['parameters']
            pool_size = job_params['pool_size']
            self.stop_job([j for j in self.jobs_dict if j != 'collection'])
            self.stop_all_clips()
            self.wait_for_silence()
            while self.select_collection() is None:
                logger.warning('Trying another collection in 2 seconds.')
                time.sleep(2)
                self.select_collection()
            self.start_job([j for j in self.jobs_dict if j != 'collection'])
            self.automate_composition(start_num=job_params['start_clips'])


        def automate_composition(self, quiet_level=None, busy_level=None, start_num=1):
            """
            Ensure the clip manager is playing an appropriate number of clips,\
            and move any finished clips still lingering in the active pool to
            the inactive pool.\n - `quiet_level=(int)` the lowest number of
            concurrent clips playing before looking for more to play.\n -
            `busy_level=(int)` the highest number of concurrent clips playing
            before stopping active clips.
            """
            job_params = self.jobs['clip_selection']['parameters']
            quiet_level = job_params['quiet_level']\
                if quiet_level is None else quiet_level
            busy_level = job_params['busy_level']\
                if busy_level is None else busy_level
            self.check_finished()
            if self.clips_playing() < quiet_level:
                self.play_clip(num_clips=start_num)
            elif self.clips_playing() > busy_level:
                self.stop_clip('balance')


        def modulate_volumes(self, speed=None, weight=None):
            """
            Randomly modulate the Channel volumes for all Clip(s) in the\
            active pool.\n - `speed=(int)` is the maximum volume jump per tick
            as a percentage of the total volume. 1 is slow, 10 is very quick.\n -
            "weight=(float)" is a signed normalised float (-1.0 to 1.0) that
            weighs the random steps towards either direction.
            """
            speed = self.jobs['volume']['parameters']['speed']\
                if speed is None else speed
            weight = self.jobs['volume']['parameters']['weight']\
                if weight is None else weight
            self.modulate_volumes(speed, weight)


        def start_job(self, *args):
            """
            Start jobs matching names provided as string arguments.\n
            Jobs will only start if it is registered in the jobs dict,\
            not in the active jobs pool, and where it's tagged service\
            and the job ifself are both enabled in config file.
            """
            jobs = set(args)
            jobs.intersection_update(self.jobs_dict.keys())
            jobs.difference_update(self.active_jobs.keys())
            jobs.intersection_update(
                set(k for k, v in self.jobs.items() if v['enabled']))
            for job in jobs:
                self.active_jobs[job] = schedule.every(self.jobs[job]['timer'])\
                                    .seconds.do(self.jobs_dict[job])
            logger.debug(f'({len(self.active_jobs)}) jobs scheduled!')


        def stop_job(self, *args):
            """
            Stop jobs matching names provided as string arguments.\n
            Jobs will only be stopped if they are found in the active pool.
            """
            jobs = set(args)
            jobs.intersection_update(self.active_jobs.keys())
            for job in jobs:
                schedule.cancel_job(self.active_jobs.pop(job))