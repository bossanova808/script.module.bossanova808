import os
import json
from dataclasses import dataclass
from typing import List

import xbmc
import xbmcgui
import xbmcvfs

from bossanova808.utilities import clean_art_url, send_kodi_json
from bossanova808.logger import Logger

from infotagger.listitem import ListItemInfoTag


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
            if (self.season is not None and self.season >= 0) and (self.episode is not None and self.episode >= 0):
                label = f"{self.showtitle} ({self.season}x{self.episode:02d}) - {self.title}"
            elif self.season is not None and self.season >= 0:
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

    def update_playback_details_from_listitem(self, item: xbmcgui.ListItem) -> None:
        """
        Update the Playback object with details from a playing Kodi ListItem object and InfoLabels

        :param item: the current Kodi playing item
        """

        self.path = item.getPath()
        self.label = item.getLabel()
        self.label2 = item.getLabel2()

        # SOURCE - Kodi Library (...get DBID), PVR, or Non-Library Media?
        dbid_label = xbmc.getInfoLabel('VideoPlayer.DBID')
        self.dbid = int(dbid_label) if dbid_label else None
        if self.dbid:
            self.source = "kodi_library"
        elif xbmc.getCondVisibility('PVR.IsPlayingTV') or xbmc.getCondVisibility('PVR.IsPlayingRadio'):
            self.source = "pvr_live"
        elif 'recordings' in (self.path or ''):
            self.source = "pvr_recording"
        elif self.path and self.path.startswith(('plugin://', 'http://', 'https://')):
            self.source = "addon"
        else:
            Logger.info("Not from Kodi library, not PVR, not an http source - must be a non-library media file")
            self.source = "file"

        # TITLE
        if self.source != "pvr_live":
            self.title = xbmc.getInfoLabel(f'VideoPlayer.Title')
        else:
            self.title = xbmc.getInfoLabel('VideoPlayer.ChannelName')

        # MEDIA TYPE (see also source above, e.g. to distinguish PVR from non library video)
        # Infotagger/Kodi expect mediatype in {"video","movie","tvshow","season","episode","musicvideo"}.
        if xbmc.getInfoLabel('VideoPlayer.TVShowTitle'):
            self.type = "episode"
            self.tvshowdbid = int(xbmc.getInfoLabel('VideoPlayer.TvShowDBID')) if xbmc.getInfoLabel('VideoPlayer.TvShowDBID') else None
        elif self.dbid:
            self.type = "movie"
        elif xbmc.getInfoLabel('VideoPlayer.ChannelName'):
            self.type = "video"  # use standard mediatype; PVR tracked via self.source
        else:
            self.type = "video"

        # Initialise RESUME TIME and TOTAL TIME / DURATION
        if self.source != "pvr_live":
            video_tag = item.getVideoInfoTag()
            total = video_tag.getResumeTimeTotal()
            self.totaltime = self.duration = (None if total == 0.0 else total)
            # This will get updated as playback progresses (see switchback_service.py), but might as well initialise here
            resume = video_tag.getResumeTime()
            self.resumetime = (None if resume == 0.0 else resume)

        # ARTWORK - POSTER, FANART and THUMBNAIL
        self.poster = clean_art_url(xbmc.getInfoLabel('Player.Art(tvshow.poster)') or xbmc.getInfoLabel('Player.Art(poster)') or xbmc.getInfoLabel('Player.Art(thumb)'))
        self.fanart = clean_art_url(xbmc.getInfoLabel('Player.Art(fanart)'))
        self.thumbnail = clean_art_url(xbmc.getInfoLabel('Player.Art(thumb)') or item.getArt('thumb'))

        # OTHER DETAILS
        # PVR Live/Recordings
        self.channelname = xbmc.getInfoLabel('VideoPlayer.ChannelName')
        self.channelnumberlabel = xbmc.getInfoLabel('VideoPlayer.ChannelNumberLabel')
        self.channelgroup = xbmc.getInfoLabel('VideoPlayer.ChannelGroup')
        # Episodes & Movies
        self.year = int(xbmc.getInfoLabel(f'VideoPlayer.Year')) if xbmc.getInfoLabel(f'VideoPlayer.Year') else None
        # Episodes
        self.showtitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
        self.season = int(xbmc.getInfoLabel('VideoPlayer.Season')) if xbmc.getInfoLabel('VideoPlayer.Season') else None
        self.episode = int(xbmc.getInfoLabel('VideoPlayer.Episode')) if xbmc.getInfoLabel('VideoPlayer.Episode') else None
        # Episodes -> we also want the number of seasons so we can force-browse to the appropriate spot after a Swtichback initiated playback
        if self.tvshowdbid:
            json_dict = {
                    "jsonrpc":"2.0",
                    "id":"VideoLibrary.GetSeasons",
                    "method":"VideoLibrary.GetSeasons",
                    "params":{
                            "tvshowid":self.tvshowdbid,
                    },
            }

            properties_json = send_kodi_json(f'Get seasons details for tv show {self.showtitle}', json_dict)
            if not properties_json or 'result' not in properties_json:
                Logger.error("VideoLibrary.GetSeasons returned no result")
                return
            properties = properties_json['result']
            # {'limits': {'end': 2, 'start': 0, 'total': 2}, 'seasons': [...]}
            self.totalseasons = properties.get('limits', {}).get('total')
            if self.totalseasons is None and 'seasons' in properties:
                self.totalseasons = len(properties['seasons'])

    # noinspection PyMethodMayBeStatic
    def create_list_item_from_playback(self, offscreen: bool = False) -> xbmcgui.ListItem:
        """
        Create a Kodi ListItem object from a Playback object

        :param offscreen: whether to create the list item in offscreen mode (faster) - default False
        :return: ListItem: a Kodi ListItem object constructed from the Playback object
        """

        Logger.debug(f"Creating list item from playback:", self)

        path = self.path
        list_item = xbmcgui.ListItem(label=self.pluginlabel, path=path, offscreen=offscreen)
        list_item.setArt({"thumb":self.thumbnail})
        list_item.setArt({"poster":self.poster})
        list_item.setArt({"fanart":self.fanart})
        list_item.setProperty('IsPlayable', 'true')

        # if "pvr" in self.source:
        #     # use a proxy plugin url to actually trigger resuming live PVR playback...
        #     # (TODO: remove this hack when setResolvedUrl/ListItems are fixed to properly handle PVR links in listitem.path)
        #     args = urlencode({'mode': 'pvr_hack', 'path': self.path})
        #     list_item.setPath(f"plugin://plugin.switchback/?{args}")
        #     Logger.debug("Playback was PVR - override ListItem path to point to plugin proxy URL for PVR playback hack", list_item.getPath())
        #
        #     # PVR channels are not really videos! See: https://forum.kodi.tv/showthread.php?tid=381623&pid=3232826#pid3232826
        #     # So that's all we need to do for PVR playbacks

        if self.source == "pvr_live":
            return list_item

        # Otherwise, it's an episode/movie/file etc...set the InfoVideoTag stuff
        tag = ListItemInfoTag(list_item, "video")
        # Infotagger seems the best way to do this currently as is well tested
        # I found directly setting things on InfoVideoTag to be buggy/inconsistent
        infolabels = {
                'mediatype':self.type,
                'dbid':self.dbid,  # previously had: if self.type != 'episode' else self.tvshowdbid,
                # InfoTagger throws a Key Error on this?
                # 'tvshowdbid': self.tvshowdbid or None,
                'title':self.title,
                'path':self.path,
                'year':self.year,
                'tvshowtitle':self.showtitle,
                'episode':self.episode,
                'season':self.season,
                'duration': int(self.totaltime) if self.totaltime is not None else None,
        }
        tag.set_info(infolabels)
        # Required, otherwise immediate Switchback mode won't resume properly
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
        return json.dumps([p.__dict__ for p in self.list], ensure_ascii=False, indent=2)

    def init(self) -> None:
        """
        Initialise/reset in memory PlaybackList, and delete/re-create the empty PlaybackList file
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
        # Ensure we start from a clean slate before loading from disk
        self.list = []
        try:
            with open(self.file, 'r') as switchback_list_file:
                switchback_list_json = json.load(switchback_list_file)
                for playback in switchback_list_json:
                    self.list.append(Playback(**playback))
        except FileNotFoundError:
            Logger.warning(f"Could not find: [{self.file}] - creating empty PlaybackList & file")
            self.init()
        except json.JSONDecodeError:
            Logger.error(f"JSONDecodeError - Unable to parse PlaybackList file [{self.file}] -  creating empty PlaybackList & file")
            self.init()
        # Let unexpected exceptions propagate

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
        self.list = [x for x in self.list if x.path != path]

    def find_playback_by_path(self, path: str) -> Playback | None:
        """
        Return a playback with the matching path if found, otherwise None

        :param path: str The path to search for
        :return: Playback or None: The Playback object if found, otherwise None
        """
        Logger.debug(f"find_playback_by_path: {path}")
        for playback in self.list:
            if playback.path == path:
                return playback
        return None
