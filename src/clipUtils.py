#  _________ .__  .__          ____ ___   __  .__.__
#  \_   ___ \|  | |__|_____   |    |   \_/  |_|__|  |   ______
#  /    \  \/|  | |  \____ \  |    |   /\   __\  |  |  /  ___/
#  \     \___|  |_|  |  |_> > |    |  /  |  | |  |  |__\___ \
#   \______  /____/__|   __/  |______/   |__| |__|____/____  >
#          \/        |__|                                  \/

"""
Abstracted static functions to help manage audio clip sets.
"""

from __future__ import annotations

import random
import logging

from src.utils import plural

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def init_sounds(clips: set, channels: dict) -> dict:
    """
    Initialises a Sound object for each Clip in provided Clip set.\n
    Sounds are loaded into memory and assigned mixer Channels from the
    provided argument. Returns a dictionary of any unused channels
    and clips that failed to build.
    """
    done = set()
    if len(channels) < len(clips):
        logger.warning(
            f"Trying to initialise {len(clips)} Sound{plural(clips)} "
            f"from {len(channels)} Channel{plural(channels)}. Clips not"
            f" assigned a channel will be pulled from this collection!"
        )
    for clip in clips:
        if len(channels) == 0:
            logger.warning(f"Ran out of channels to assign!")
            break
        if clip.build_sound(channels.popitem()) is not None:
            done.add(clip)
    remaining = list(clips.difference(done))
    logger.info(f"Collection selected with {get_contents(done, count=True)}.")
    if len(remaining) > 0:
        logger.warning(
            f"Unable to build ({len(remaining)}) " f"Sound object{plural(remaining)}! "
        )
    return {"channels": channels, "clips": remaining}


def get_distributed(clips: set, num_clips: int, **kwargs) -> set:
    """
    Return an evenly distributed set of clip based on categories.
    Use `strict=True` to abort and return None if an even distribution
    of clips can not be allocated from the supplied set of clips.
    """
    if num_clips > len(clips):
        logger.warning(
            f"Requesting ({num_clips}) clip{plural(num_clips)} but "
            f"only ({len(clips)}) in set! Will return entire set."
        )
        selection = clips
    else:
        contents = get_contents(clips)
        logger.debug(
            f"Requesting ({num_clips}) clips from " f"{get_contents(clips, count=True)}"
        )
        selection = set()
        clips_per_category = int(num_clips / len(contents))
        if clips_per_category == 0:
            logger.debug(
                f"Cannot select number of clips less than the number "
                f"of categories. Rounding up to {len(contents)}."
            )
            clips_per_category = 1
        for category in contents:
            try:
                selection.update(random.sample(contents[category], clips_per_category))
            except ValueError as exception:
                logger.debug(
                    f'"{category}" only has ({len(contents[category])}) '
                    f"clip{plural(clips_per_category)}, but was asked for "
                    f"({clips_per_category})."
                )
                if kwargs.get("strict", False):
                    return None
                else:
                    failed = clips_per_category - len(contents[category])
                    logger.debug(
                        f"{plural(failed)} will be selected at random. "
                        f'Set "strict" mode to enforce distribution.'
                    )
                    selection.update(
                        random.sample(contents[category], len(contents[category]))
                    )
        if (unassigned := num_clips - len(selection)) > 0:
            selection.update(random.sample(clips.difference(selection), unassigned))
    logger.debug(f'Returned: {get_contents(selection, count=True)}".')
    return selection


def get_contents(clips: set, **kwargs) -> dict:
    """
    Return dictionary of category:clips (key:value) pairs from a set of Clips.\n
    - "count=True" returns number of clips instead of a list of Clips.
    """
    contents = {}
    for clip in clips:
        category = clip.category
        if kwargs.get("count", False):
            contents[category] = contents.get(category, 0) + 1
        else:
            if category in contents:
                contents[category].append(clip)
            else:
                contents[category] = [clip]
    return contents


def get_clip(clips: set, **kwargs) -> set:
    """### Return random or specific clip(s).\n
    to return can be defined with `num_clips=1`.
    Random clip(s) will be selected unless one of the
    following kwargs are supplied to specify the request:

    - `name=(str)`\n- `channel=(Channel object)`\n- `category=(str)`
    """
    if (name := kwargs.get("name", None)) is not None:
        if (clip := next((c for c in clips if c.name == name), None)) is None:
            logger.warning(f'Requested clip "{name}" not in provided set.')
            return None
        return set(clip)
    if (channel := kwargs.get("channel", None)) is not None:
        if (clip := next((c for c in clips if c.channel == channel), None)) is None:
            logger.warning(f'Requested clip "{name}" not in provided set.')
            return None
        return set(clip)
    if (category := kwargs.get("category", None)) is not None:
        if (clips := get_contents(clips).get(category, None)) is None:
            logger.warning(f'Category "{category}" not found in set. Ignoring.')
            return None
    in_set = len(clips)
    if in_set == 0:
        logger.warning(f"No clips available. Skipping request.")
        return None
    to_get = kwargs.get("num_clips", 1)
    if to_get > in_set:
        logger.debug(
            f"Requested ({to_get}) clip{plural(to_get)} from "
            f'{("[" + category + "] in ") if category is not None else ""}'
            f" with ({in_set}) Clip{plural(in_set)}. "
            f'"Returning {str(in_set)}) instead.'
        )
    return set([clip for clip in random.sample(clips, min(to_get, in_set))])
