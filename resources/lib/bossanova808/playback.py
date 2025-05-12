import os
import json
from json import JSONDecodeError
from dataclasses import dataclass
from typing import List

from xbmcgui import ListItem
from infotagger.listitem import ListItemInfoTag

from bossanova808.constants import *
from bossanova808.logger import Logger


@dataclass
class Playback:
    """
    Stores whatever data we can grab about a Kodi Playback so that we can display it nicely in the Switchback list
    """

    file: str = None
    path: str = None
    type: str = None  # episode, movie, video (per Kodi types) - song is the other type, but Switchback supports video only
    # Seems to be a newer version of the above, but unclear how/when to use, and what about music??
    # mediatype: str = None # mediatype: string - "video", "movie", "tvshow", "season", "episode" or "musicvideo"
    source: str = None  # kodi_library, pvr_live, pvr_recording, addon, file
    dbid: int = None
    tvshowdbid: int = None
    totalseasons: int = None
    title: str = None
    label: str = None
    label2: str = None
    thumbnail: str = None
    fanart: str = None
    poster: str = None
    year: int = None
    showtitle: str = None
    season: int = None
    episode: int = None
    resumetime: float = None
    totaltime: float = None
    duration: float = None
    channelname: str = None
    channelnumberlabel: str = None
    channelgroup: str = None

    @property
    def pluginlabel(self) -> str:
        """
        Create a more full label, e.g. Showname (2x03) - Episode title

        :return: The Switchback label for display in the plugin list
        """
        label = self.title
        if self.showtitle:
            if self.season >= 0 and self.episode >= 0:
                label = f"{self.showtitle} ({self.season}x{self.episode:02d}) - {self.title}"
            elif self.season >= 0:
                label = f"{self.showtitle} ({self.season}x?) - {self.title}"
            else:
                label = f"{self.showtitle} - {self.title}"
        elif self.channelname:
            if self.source == "pvr_live":
                label = f"{self.channelname} (PVR Live)"
            else:
                label = f"{self.title} (PVR Recording {self.channelname})"
        if self.source == "addon":
            label = f"{label} (Addon)"
        return label

    def update(self, new_details: dict) -> None:
        """
        Update a Playback object with new details

        :param new_details: a dictionary (need not be complete) of the Playback object's new details
        """
        for key, value in new_details.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                Logger.error(f"Playback.update: Unknown key [{key}]")

    def toJson(self) -> str:
        """
        Return the Playback object as JSON

        :return: the Playback object as JSON
        """
        return json.dumps(self, default=lambda o:o.__dict__)

    # noinspection PyMethodMayBeStatic
    def create_list_item(self, offscreen: bool = False) -> ListItem:
        """
        Create a Kodi ListItem object from a Playback object

        :param offscreen: whether to create the list item in offscreen mode (faster) - default False
        :return: ListItem: a Kodi ListItem object constructed from the Playback object
        """

        Logger.debug(f"Creating list item from playback:", self)

        url = self.path
        list_item = xbmcgui.ListItem(label=self.pluginlabel, path=url, offscreen=offscreen)
        list_item.setArt({"thumb":self.thumbnail})
        list_item.setArt({"poster":self.poster})
        list_item.setArt({"fanart":self.fanart})
        list_item.setProperty('IsPlayable', 'true')

        # PVR channels are not videos! See: https://forum.kodi.tv/showthread.php?tid=381623&pid=3232826#pid3232826
        if "pvr_live" not in self.source:
            tag = ListItemInfoTag(list_item, "video")
            # Infotagger seems the best way to do this currently as is well tested
            # I found directly setting things on InfoVideoTag to be buggy/inconsistent
            infolabels = {
                    'mediatype':self.type,
                    'dbid':self.dbid if self.type != 'episode' else self.tvshowdbid,
                    # InfoTagger throws a Key Error on this?
                    # 'tvshowdbid': self.tvshowdbid or None,
                    'title':self.title,
                    'path':self.path,
                    'year':self.year,
                    'tvshowtitle':self.showtitle,
                    'episode':self.episode,
                    'season':self.season,
                    'duration':self.totaltime,
            }
            tag.set_info(infolabels)
            tag.set_resume_point({'ResumeTime':self.resumetime, 'TotalTime':self.totaltime})
            if self.tvshowdbid:
                list_item.setProperty('tvshowdbid', str(self.tvshowdbid)) 

        return list_item


@dataclass
class PlaybackList:
    """
    A list of Playback objects, with some helper methods.  Stored both in memory (accessible via .list) and on disk (filename at .file)
    Is a standard Python list, so can be iterated over, indexed, etc., and of course, all standard list methods are available.

    To create a PlaybackList::
        switchback = PlaybackList([], xbmcvfs.translatePath(os.path.join(PROFILE, "switchback_list.json")))
    """
    list: List[Playback]
    file: str

    def toJson(self) -> str:
        """
        Return the list of Playback objects as JSON

        :return: the list of Playback objects as JSON
        """
        temp_json = []
        for playback in self.list:
            temp_json.append(playback.toJson())
        temp_json = ',\n'.join(temp_json)
        return f"[\n{temp_json}\n]\n"

    def init(self) -> None:
        """
        Initialise/reset an in memory PlaybackList, and delete/re-create the empty PlaybackList file
        """
        self.list = []
        xbmcvfs.mkdirs(os.path.dirname(self.file))
        with open(self.file, 'w'):
            pass

    def load_or_init(self) -> None:
        """
        Load a JSON-formatted PlaybackList from the PlaybackList file
        """
        Logger.info("Try to load PlaybackList from file:", self.file)
        try:
            with open(self.file, 'r') as switchback_list_file:
                switchback_list_json = json.load(switchback_list_file)
                for playback in switchback_list_json:
                    self.list.append(Playback(**playback))
        except FileNotFoundError:
            Logger.warning(f"Could not find: [{self.file}] - creating empty PlaybackList & file")
            self.init()
        except JSONDecodeError:
            Logger.error(f"JSONDecodeError - Unable to parse PlaybackList file [{self.file}] -  creating empty PlaybackList & file")
            self.init()
        except:
            raise

        Logger.info(f"PlaybackList is:", self.list)

    def save_to_file(self) -> None:
        """
        Save the PlaybackList to the PlaybackList file (as JSON)
        """
        Logger.info(f"Saving PlaybackList to file: {self.file}")
        with open(self.file, 'w', encoding='utf-8') as f:
            f.write(self.toJson())

    def delete_file(self) -> None:
        """
        Deletes the PlaybackList file
        """
        if os.path.exists(self.file):
            Logger.info(f"Deleting PlaybackList file [{self.file}]")
            os.remove(self.file)

    def remove_playbacks_of_path(self, path: str) -> None:
        """
        Remove any playbacks of a given path from the PlaybackList
        """
        self.list = list(filter(lambda x:x.path == path, self.list))

    def find_playback_by_path(self, path: str) -> Playback or None:
        """
        Return a playback with the matching pth if found, otherwise None

        :param path: str The path to search for
        :return: Playback or None: The Playback object if found, otherwise None
        """
        for playback in self.list:
            if playback.path == path:
                return playback
        return None
