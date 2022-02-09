
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
import sys
import time
import random
import logging
import schedule
import multiprocessing as mp

# Silence PyGame greeting mesage
stdout = sys.__stdout__
stderr = sys.__stderr__
sys.stdout = open(os.devnull,'w')
sys.stderr = open(os.devnull,'w')
import pygame as pg
sys.stdout = stdout
sys.stderr = stderr

from src.utils import plural
from src.clipUtils import *
from src.clip import Clip
from src.metrics import MetricsPusher

logger = logging.getLogger(__name__)



class Composition():
    """
    Audio playback composition manager module.
    """

    registry = None

    def __init__(self, name:str, config:dict, *args, **kwargs) -> None:
        self.module_name = name
        self.config = config[self.module_name]
        self.log_level = logging.DEBUG if self.config.get(
                        'debug', True) else logging.INFO 
        logger.setLevel(self.log_level)
        logging.getLogger("clip.py").setLevel(self.log_level)
        logging.getLogger("clipUtils.py").setLevel(self.log_level)
        self.enabled = self.config.get('enabled', False)
        self.active = False
        self.clip_event = pg.USEREVENT + 1
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        # Process management
        self.manager = None
        self.state_q = mp.Queue(maxsize=1)
        self.source_in, self.source_out = mp.Pipe()
        self.destination_in, self.destination_out = mp.Pipe()
        self.metrics_q = kwargs.get('metrics_q', None)

        schedule.logger.setLevel(logging.DEBUG if self.config.get(
                                'debug', True) else logging.INFO)

        if self.enabled:
            self.initialise()


    def update_config(self, config:dict):
        """
        Updates the state and parameters which drive the Clip Manager.
        """
        logger.info(f'Updating Composition module configuration...')
        if self.enabled:
            self.config = config[self.module_name]
            if self.config.get('enabled', False) is False:
                self.stop()
            else:
                self.stop()
                self.initialise()
                self.start()
        else:
            self.config = config[self.module_name]
            if self.config.get('enabled', False) is True:
                self.start()
            else:
                pass

    def initialise(self):
        """
        Initialises a new Clip Manager object.
        """
        if self.enabled:
            if self.manager is None:
                try:
                    self.manager = self.ClipManager(self)
                except OSError:
                    self.enabled = False
                    self.stop()
                logger.debug(f'Clip Manager module initialised.')
            else:
                logger.warning(f'Clip Manager module already initialised!')
        else:
            logger.warning(f'Cannot create Clip Manager, module not enabled!')


    def start(self):
        """
        Starts the Clip Manager routine.
        """
        if self.enabled:
            if self.manager is not None:
                if self.manager is not None:
                    self.manager.collection_job()
                    self.active = True
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
            schedule.clear()
            self.manager.stop_all_clips()
            self.manager.wait_for_silence()
            pg.quit()
            self.manager = None
            logger.info(f'Composition module stopped.')
        else:
            logger.debug('Ignoring request to stop Composition, module is not enabled.')
        self.active = False


    def tick(self):
        """
        Call regularly to execute the scheduled jobs and clean up old clips.
        """
        if self.enabled and self.manager is not None:
            schedule.run_pending()
            self.manager.manage_audio_events()


    #  _________ .__  .__            _____                                             
    #  \_   ___ \|  | |__|_____     /     \ _____    ____ _____     ____   ___________ 
    #  /    \  \/|  | |  \____ \   /  \ /  \\__  \  /    \\__  \   / ___\_/ __ \_  __ \
    #  \     \___|  |_|  |  |_> > /    Y    \/ __ \|   |  \/ __ \_/ /_/  >  ___/|  | \/
    #   \______  /____/__|   __/  \____|__  (____  /___|  (____  /\___  / \___  >__|   
    #          \/        |__|             \/     \/     \/     \//_____/      \/       

    class ClipManager():
        """
        Clip Manager class to manage "collections" of audio clips for playback.
        """
        def __init__(self, parent:Composition, *args, **kwargs) -> None:
            """
            Create a new Clip Manager object.
            """
            if not os.path.isdir(parent.config['base_path']):
                logger.error(f'Invalid root path for library: {parent.config["base_path"]}.')
                raise OSError
            self.config = parent.config
            self.module_name = parent.module_name
            self.mixer = pg.mixer
            self.clip_event = parent.clip_event
            self.channels = None
            self.collections = {}
            self.current_collection = {}
            self.inactive_pool = set()
            self.active_pool = set()
            self.active_jobs = {}
            self.jobs = self.config['jobs']
            self.jobs_dict = {
                'collection': self.collection_job,
                'clip_selection': self.clip_selection_job,
                'volume': self.volume_job
            }
            # Metrics and mapping
            self.metrics = MetricsPusher(parent.metrics_q)
            self.destination_out = parent.destination_out
            self.destinations = {}
            self.source_in = parent.source_in
            self.source_values = {}

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
            logger.debug(f'Library path: {self.config["base_path"]}...')
            titles = [d for d in os.listdir(self.config['base_path']) \
                if os.path.isdir(os.path.join(self.config['base_path'], d))]
            for title in sorted(titles):
                path = os.path.join(self.config['base_path'], title)
                names = []
                for f in os.listdir(path):
                    if os.path.splitext(f)[1][1:] in self.config['valid_extensions']:
                        names.append(f)
                if len(names) != 0:
                    self.collections[title] = {'path':path, 'names':names}
            logger.info(f'Clip Manager initialised with ({len(self.collections)}) '
                        f'collection{plural(self.collections)}.')


        def select_collection(self, **kwargs):
            """
            Selects a collection from the library, prepares clips and playback pools.\n
            Will randomly select a collection if valid name is not supplied.
            """
            name = kwargs.get('name', None)
            num_clips = kwargs.get('num_clips', self.config['default_pool_size'])
            logger.debug(f'Importing {"random " if name is None else ""}collection '
                        f'{(str(name) + " ") if name is not None else ""}from library.')
            if name is not None and name not in self.collections:
                logger.warning('Requested collection name does not exist. '
                               'One will be randomly selected.')
                name = None
            if name is None:
                name = random.choice(list(self.collections.keys()))
            path, names = (self.collections[name]['path'], self.collections[name]['names'])
            logger.info(f'Collection "{name}" selected with ({len(names)}) '
                        f'audio file{plural(names)}')
            self.current_collection = {'title':name, 'path':path, 'names':names}
            # Build clips from collection to populate clip manager
            self.clips = set([Clip(path, name,
                                    self.config['categories']) for name in names])
            self.active_pool = set()
            if (pool := get_distributed(
                            self.clips, num_clips,
                            strict=self.config.get(
                            'strict_distribution', False))) is not None:
                self.inactive_pool = pool
                self.channels = self.get_channels(self.inactive_pool)
                init_sounds(self.inactive_pool, self.channels)
                self.metrics.update(f'{self.module_name}_collection', name)
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


        def stop_all_clips(self, **kwargs):
            """
            Tell all active clips to stop playing, emptying the mixer of\
            active channels.\n `fade_time=(int)` the number of milliseconds active\
            clips should take to fade their volumes before stopping playback.\
            If no parameter is provided, the clip_manager's `fade_out`\
            value from the config.json will be used.\n Use 'disable_events=True'\
            to prevent misfiring audio jobs that use clip end events to launch more.
            """
            fade_time = kwargs.get('fade_time', self.config.get('fade_out', 0))
            if pg.mixer.get_init():
                if pg.mixer.get_busy():
                    logger.info(f'Stopping audio clips: {fade_time}ms fade...')
                    if kwargs.get('disable_events', False) is True:
                        self.clear_events()
                    pg.mixer.fadeout(fade_time)


        def manage_audio_events(self):
            """
            Check for audio playback completion events,
            call the clip manager to clean them up.
            """
            for event in pg.event.get():
                if event.type == self.clip_event:
                    logger.info(f'Clip end event: {event}')
                    self.check_finished()


        def wait_for_silence(self):
            """
            Stops the main thread until all channels have faded out.
            """
            logger.debug('Waiting for audio mixer to release all channels...')            
            if pg.mixer.get_init():
                while pg.mixer.get_busy():
                    time.sleep(0.1)
            logger.debug('Mixer empty.')


        def move_to_inactive(self, clips: set):
            """
            Supplied list of Clip(s) are moved from active to inactive pool.
            """
            for clip in clips:
                self.active_pool.remove(clip)
                self.inactive_pool.add(clip)
                logger.debug(f'MOVED: {clip.name} | active >>> INACTIVE.')


        def move_to_active(self, clips: set):
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
            fade = kwargs.get('fade', self.config.get('fade_out', 0))
            if len(clips) == 0:
                # Finds the category with the greatest number of active clips.
                if 'balance' in args:
                    contents = get_contents(self.active_pool)
                    clips = contents[max(contents, key = contents.get)]
                    kwargs.update('category', None)
                clips = get_clip(self.active_pool, kwargs)
            stopped = set([c for c in clips if c.stop(kwargs.get('fade',
                        self.config.get('fade_out', 0))) is not None])
            self.move_to_inactive(stopped)
            return stopped


        def modulate_volumes(self, **kwargs):
            """
            Randomly modulate the Channel volumes for all Clip(s) in the active pool.\n 
            - "speed=(int)" is the maximum volume jump per tick as a percentage of the total 
            volume. 1 is slow, 10 is very quick.\n - "weight=(float)" is a signed normalised 
            float (-1.0 to 1.0) that weighs the random steps towards either direction.
            """
            speed = kwargs.get('speed', 5) / 100
            weight = kwargs.get('weight', 1) * speed
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

        def collection_job(self, **kwargs):
            """
            Select a new collection from the clip manager, replacing any\
            currently loaded collection.
            """
            job_params = self.jobs['collection']['parameters']
            pool_size = kwargs.get('pool_size',
                        job_params.get('pool_size',
                        self.config['default_pool_size']))
            start_clips = kwargs.get('start_clips',
                            job_params.get('start_clips', 1))
            self.stop_job(ignore='collection')
            self.stop_all_clips()
            self.wait_for_silence()
            while self.select_collection(
                    name=kwargs.get('collection'),
                    pool_size=pool_size) is None:
                logger.warning('Trying another collection in 2 seconds.')
                time.sleep(2)
                self.select_collection(pool_size=pool_size)
            self.start_job()
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
            job_params = self.jobs['clip_selection']['parameters']
            quiet_level = kwargs.get('quiet_level', job_params['quiet_level'])
            busy_level = kwargs.get('busy_level', job_params['busy_level'])
            start_num = kwargs.get('start_num', 1)
            self.check_finished()
            if self.clips_playing() < quiet_level:
                self.play_clip(num_clips=start_num)
            elif self.clips_playing() > busy_level:
                self.stop_clip('balance')


        def volume_job(self, **kwargs):
            """
            Randomly modulate the Channel volumes for all Clip(s) in the\
            active pool.\n - `speed=(int)` is the maximum volume jump per tick
            as a percentage of the total volume. 1 is slow, 10 is very quick.\n -
            "weight=(float)" is a signed normalised float (-1.0 to 1.0) that
            weighs the random steps towards either direction.
            """
            job_params = self.jobs['volume']['parameters']
            speed = kwargs.get('speed', job_params['speed'])
            weight = kwargs.get('weight', job_params['weight'])
            self.modulate_volumes(speed=speed, weight=weight)


        def start_job(self, *args):
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
            jobs.intersection_update(
                set(k for k, v in self.jobs.items() if v['enabled']))
            for job in jobs:
                self.active_jobs[job] = schedule.every(self.jobs[job]['timer'])\
                                    .seconds.do(self.jobs_dict[job])
            logger.debug(f'({len(self.active_jobs)}) jobs currently scheduled.')


        def stop_job(self, *args, **kwargs):
            """
            Stop jobs matching names provided as an interable of string arguments.\n
            Providing no string args will stop ALL jobs.\n
            `ignore=(str)` will prevent the job with provided name from being stopped.\n
            Jobs will only be stopped if they are found in the active pool.
            """
            if len(args) == 0:
                jobs = set(self.jobs_dict.keys())
            else:
                jobs = set(args)
            if (ignore := kwargs.get('ignore', None)) is not None:
                jobs.remove(ignore)
            jobs.intersection_update(self.active_jobs.keys())
            logger.debug(f'Stopping jobs: {jobs}')
            for job in jobs:
                schedule.cancel_job(self.active_jobs.pop(job))
