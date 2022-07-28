# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to the OpenTimelineIO project

import glob
import json
import os
import tempfile

import unreal


class IconCache(object):
    """Icons referenced by otio_unreal_actions are standard UE Slate icons,
    which are found in the current Unreal Editor build and their paths
    are cached for reuse by future editor sessions. This class manages
    that cache in-memory and on-disk.
    """

    # All needed Slate icons are included in the Engine/Content directory
    ICON_SEARCH_DIR = os.path.abspath(unreal.Paths.engine_content_dir())

    # Icon paths are cached to a file for future reference
    CACHE_FILE_PATH = os.path.join(
        tempfile.gettempdir(), "otio_unreal_actions_icons.json"
    )

    # In-memory cache data
    icons = {
        "edit": ["edit.svg", None],
        "export": ["Export.svg", None],
        "file": ["file.svg", None],
        "folder-closed": ["folder-closed.svg", None],
        "folder-open": ["folder-open.svg", None],
        "level-sequence-actor": ["LevelSequenceActor_16.svg", None],
        "plus": ["plus.svg", None],
        "save": ["save.svg", None],
    }

    # Has cache been loaded?
    loaded = False

    @classmethod
    def load(cls):
        """Load icon paths from cache file or search for them in the UE
        content directory.
        """
        if cls.loaded:
            return

        # Load previously cached icon paths
        if os.path.exists(cls.CACHE_FILE_PATH):
            with open(cls.CACHE_FILE_PATH, "r") as json_file:
                data = json.load(json_file)

            for key, path in data.items():
                if (
                    key in cls.icons
                    and cls.icons[key][0] == os.path.basename(path)
                    and os.path.exists(path)
                ):
                    cls.icons[key][1] = path.replace("\\", "/")

        # Search for un-cached icon paths and cache them
        for key in cls.icons:
            if cls.icons[key][1] is None:
                icon_paths = glob.glob(
                    os.path.join(cls.ICON_SEARCH_DIR, "**", cls.icons[key][0]),
                    recursive=True,
                )
                if icon_paths:
                    cls.icons[key][1] = icon_paths[0].replace("\\", "/")

        # Update cache file for future reference
        cls.save()

        # Don't load again this session
        cls.loaded = True

    @classmethod
    def save(cls):
        """Save in-memory icon cache to disk, preventing the need to
        search for icons in future sessions.
        """
        data = {}
        for key in cls.icons:
            if cls.icons[key][1] is not None and os.path.exists(cls.icons[key][1]):
                data[key] = cls.icons[key][1]

        with open(cls.CACHE_FILE_PATH, "w") as json_file:
            json.dump(data, json_file, indent=4)


def get_icon_path(key):
    """
    Get a cached icon path by key.

    Args:
        key (str): Icon key

    Returns:
        str|None: Icon path, or None if key is unknown or the icon
            could not be found.
    """
    # Cache icons on first call
    if not IconCache.loaded:
        IconCache.load()

    if key in IconCache.icons:
        return IconCache.icons[key][1]
    else:
        return None
