
#  _________ .__  .__          ____ ___   __  .__.__          
#  \_   ___ \|  | |__|_____   |    |   \_/  |_|__|  |   ______
#  /    \  \/|  | |  \____ \  |    |   /\   __\  |  |  /  ___/
#  \     \___|  |_|  |  |_> > |    |  /  |  | |  |  |__\___ \ 
#   \______  /____/__|   __/  |______/   |__| |__|____/____  >
#          \/        |__|                                  \/ 

"""
Abstracted static functions to help manage audio clip sets.
"""

import logging, random
from signify.utils import plural

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def init_sounds(clips:set, channels:dict) -> dict:
    """
    Initialises a Sound object for each Clip in provided Clip set.\n
    Sounds are loaded into memory and assigned mixer Channels from the provided argument.
    Returns a dictionary of any unused channels and clips that failed to build.
    """
    done = set()
    if len(channels) < len(clips):
        logger.warn(f'Trying to initialise {len(clips)} Sound{plural(clips)} '
                    f'from {len(channels)} Channel{plural(channels)}. Clips not assigned a '
                    f'channel will be pulled from this collection!')
    for clip in clips:
        if len(channels) == 0:
            logger.warn(f'Ran out of channels to assign!')
            break
        if clip.build_sound(channels.popitem()) is not None:
            done.add(clip)
    remaining = list(clips.difference(done))
    logger.info(f'{get_contents(done, True)} initialised.')
    if len(remaining) > 0:
        logger.warn(f'Unable to build ({len(remaining)}) Sound object{plural(remaining)}! ')   
    return {'channels':channels, 'clips':remaining}

def get_distributed(clips:set, num_clips:int, strict=False) -> set:
    """
    Return an evenly distributed set of clip based on categories.
    """
    if num_clips > len(clips):
        logger.warn(f'Requesting ({num_clips}) clip{plural(num_clips)} but only ({len(clips)}) in set! '
                    f'Will return entire set.')
        selection = clips
    else:
        contents = get_contents(clips)
        logger.debug(f'Requesting ({num_clips}) clips from {get_contents(clips, True)}')
        selection = set()
        clips_per_category = int(num_clips / len(contents))
        if clips_per_category == 0:
            logger.info(f'Cannot select number of clips less than the number of categories. '
                        f'Rounding up to {len(contents)}.')
            clips_per_category = 1
        for category in contents:
            try:
                selection.update(random.sample(contents[category], clips_per_category))
            except ValueError as exception:
                logger.warning(f'Could not obtain ({clips_per_category}) clip{plural(clips_per_category)} from '
                            f'"{category}" with ({len(contents[category])}) clip{plural(contents[category])}! '
                            f'Exception: "{exception}"')
                if strict is True:
                    return None
                else:
                    failed = clips_per_category - len(contents[category])
                    logger.info(f'Clip distribution not set to "strict" mode. ({failed}) unassigned clip '
                                f'slot{plural(failed)} will be selected at random.')
                    selection.update(random.sample(contents[category], len(contents[category])))
        if (unassigned := num_clips - len(selection)) > 0:
            selection.update(random.sample(clips.difference(selection), unassigned))
    logger.info(f'Returned: {get_contents(selection, count=True)}".')
    return selection

def get_contents(clips:set, count=False) -> dict:
    """
    Return dictionary of category:clips (key:value) pairs from a set of Clips.\n
    - "count=True" returns number of clips instead of a list of Clips.
    """
    contents = {}
    for clip in clips:
        category = clip.category
        if count:
            contents[category] = contents.get(category, 0) + 1
        else:
            if category in contents:
                contents[category].append(clip)
            else:
                contents[category] = [clip]
    return contents

def clip_by_name(clips:set, name:str):
    """
    Return specific Clip by name from given set of Clips.
    If no clip is found, will silently return None.
    """
    for clip in clips:
        if clip.name == name:
            return clip
    return None

def clip_by_channel(clips:set, chan) -> set:
    """
    Looks for a specific Channel attached to provided set of Clips.
    """
    found = set()
    for clip in clips:
        if clip.channel == chan:
            found.add(clip)
    if len(found) > 1:
        logger.warn(f'Channel {chan} is assigned to multiple Clip objects: {[c.name for c in found]}')
    return found

def get_clip(clips:set, name=None, category=None, num_clips=1) -> set:
    """
    Return clip(s) by name, category, or total random from provided set of clips.
    """
    if name is not None:
        if (clip := clip_by_name(name, clips)) is None:
            logger.warn(f'Requested clip "{name}" not in provided set. Skipping.')
            return None
        return set(clip)
    if category:
        contents = get_contents(clips)
        if (clips := contents.get(category)) is None:
            logger.warn(f'Category "{category}" not found in set. Ignoring request.')
            return None
    available = len(clips)
    if available == 0:
        logger.warn(f'No clips available. Skipping request.')
        return None
    if num_clips > available:
        logger.debug(f'Requested ({num_clips}) clip{plural(num_clips)} from '
                    f'{("[" + category + "] in ") if category is not None else ""} with '
                    f'({available}) Clip{plural(available)}. '
                    f'{("Returning (" + str(available) + ") instead") if available > 0 else "Skipping request"}.')
    return set([clip for clip in random.sample(clips, min(num_clips, available))])
