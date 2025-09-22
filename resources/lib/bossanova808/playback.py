import os
import json
from dataclasses import dataclass, asdict
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
    file: str | None = None
    path: str | None = None
    type: str | None = None  # episode, movie, video (per Kodi types) - song is the other type, but Switchback supports video only
    # Seems to be a newer version of the above, but unclear how/when to use, and what about music??
    # mediatype: str | None = None # mediatype: string - "video", "movie", "tvshow", "season", "episode" or "musicvideo"
    source: str | None = None  # kodi_library, pvr_live, pvr_recording, addon, file
    dbid: int | None = None
    tvshowdbid: int | None = None
    totalseasons: int | None = None
    title: str | None = None
    label: str | None = None
    label2: str | None = None
    thumbnail: str | None = None
    fanart: str | None = None
    poster: str | None = None
    year: int | None = None
    showtitle: str |None = None
    season: int | None = None
    episode: int | None = None
    resumetime: float | None = None
    totaltime: float | None = None
    duration: float | None = None
    channelname: str | None = None
    channelnumberlabel: str | None = None
    channelgroup: str | None = None

    @property
    def pluginlabel(self) -> str:
        """
        Create a more full label, e.g. Showname (2x03) - Episode title

        :return: The Switchback label for display in the plugin list
        """
        label = self.title or self.label or self.channelname or (os.path.basename(self.path) if self.path else None) or "Unknown"
        if self.showtitle:
            if (self.season is not None and self.season >= 0) and (self.episode is not None and self.episode >= 0):
                label = f"{self.showtitle} ({self.season}x{self.episode:02d}) - {self.title or label}"
            elif self.season is not None and self.season >= 0:
                label = f"{self.showtitle} ({self.season}x?) - {self.title or label}"
            else:
                label = f"{self.showtitle} - {self.title or label}"
        elif self.channelname:
            if self.source == "pvr_live":
                label = f"{self.channelname} (PVR Live)"
            else:
                label = f"{label} (PVR Recording {self.channelname})"

        if self.source == "addon":
            label = f"{label} (Addon)"
        return label

    def _is_addon_playback(self) -> bool:
        """
        Determine if playback originates from an addon

        :return: True if playback is from an addon, False otherwise
        """
        path_lower = (self.path or '').lower()

        # Method 1: Check for plugin:// URLs (most reliable)
        if path_lower.startswith('plugin://'):
            return True

        # Method 2: Check ListItem.Path infolabel for plugin URLs
        listitem_path_lower = xbmc.getInfoLabel('ListItem.Path').lower()
        if listitem_path_lower.startswith('plugin://'):
            return True

        # Method 3: Check if an addon ID is associated with the current item
        addon_id = xbmc.getInfoLabel('ListItem.Property(Addon.ID)')
        if addon_id:
            return True

        # Method 4: Check container path (for addon-generated content)
        container_path_lower = xbmc.getInfoLabel('Container.FolderPath').lower()
        if container_path_lower.startswith('plugin://'):
            return True

        # Method 5: Improved HTTP detection with WebDAV exclusions (fallback only)
        if path_lower.startswith(('http://', 'https://')):
            # Exclude known WebDAV/cloud storage patterns
            webdav_patterns = [
                    '/dav/',
                    'webdav',
                    '.nextcloud.',
                    'owncloud',
                    '/remote.php/',
                    'dropbox',
                    'googledrive',
                    'onedrive'
            ]

            if not any(pattern in path_lower for pattern in webdav_patterns):
                # Additional check: look for typical addon URL structures
                if any(indicator in path_lower for indicator in ['plugin', 'addon', 'stream']):
                    return True

        return False

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
        return json.dumps(asdict(self))

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
        try:
            self.dbid = int(dbid_label) if dbid_label else None
        except ValueError:
            self.dbid = None

        if self.dbid:
            self.source = "kodi_library"
        elif xbmc.getCondVisibility('PVR.IsPlayingTV') or xbmc.getCondVisibility('PVR.IsPlayingRadio'):
            self.source = "pvr_live"
        elif (self.path or '').lower().startswith('pvr://recordings/'):
            self.source = "pvr_recording"
        elif self._is_addon_playback():
            self.source = "addon"
        else:
            Logger.info("Not from Kodi library or PVR or addon – treating as a non-library media file")
            self.source = "file"

        # TITLE
        if self.source != "pvr_live":
            self.title = xbmc.getInfoLabel('VideoPlayer.Title')
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
            if video_tag:
                total = video_tag.getResumeTimeTotal()
                self.totaltime = self.duration = (None if total == 0.0 else total)
                # This will get updated as playback progresses (see switchback_service.py), but might as well initialise here
                resume = video_tag.getResumeTime()
                self.resumetime = (None if resume == 0.0 else resume)
            else:
                self.totaltime = self.duration = None
                self.resumetime = None

        # ARTWORK - POSTER, FANART and THUMBNAIL
        self.poster = clean_art_url(xbmc.getInfoLabel('Player.Art(tvshow.poster)') or xbmc.getInfoLabel('Player.Art(poster)') or xbmc.getInfoLabel('Player.Art(thumb)'))
        self.fanart = clean_art_url(xbmc.getInfoLabel('Player.Art(fanart)'))
        thumbnail_value = xbmc.getInfoLabel('Player.Art(thumb)') or (item.getArt('thumb') or '')
        self.thumbnail = clean_art_url(thumbnail_value)

        # OTHER DETAILS
        # PVR Live/Recordings
        self.channelname = xbmc.getInfoLabel('VideoPlayer.ChannelName')
        self.channelnumberlabel = xbmc.getInfoLabel('VideoPlayer.ChannelNumberLabel')
        self.channelgroup = xbmc.getInfoLabel('VideoPlayer.ChannelGroup')
        # Episodes & Movies
        year_label = xbmc.getInfoLabel('VideoPlayer.Year')
        try:
            self.year = int(year_label) if year_label else None
        except ValueError:
            self.year = None
        # Episodes
        self.showtitle = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
        season_label = xbmc.getInfoLabel('VideoPlayer.Season')
        episode_label = xbmc.getInfoLabel('VideoPlayer.Episode')
        try:
            self.season = int(season_label) if season_label else None
        except ValueError:
            self.season = None
        try:
            self.episode = int(episode_label) if episode_label else None
        except ValueError:
            self.episode = None
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
                self.totalseasons = None
                # Continue without seasons info
                return

            if 'error' in properties_json:
                Logger.error("VideoLibrary.GetSeasons returned error:", properties_json['error'])
                self.totalseasons = None
                return
            properties = properties_json['result']

            # {'limits': {'end': 2, 'start': 0, 'total': 2}, 'seasons': [...]}
            total_limit = properties.get('limits', {}).get('total')
            self.totalseasons = total_limit if isinstance(total_limit, int) else None
            if self.totalseasons is None and 'seasons' in properties:
                self.totalseasons = len(properties['seasons'])

    # noinspection PyMethodMayBeStatic
    def create_list_item_from_playback(self, offscreen: bool = False) -> xbmcgui.ListItem:
        """
        Create a Kodi ListItem object from a Playback object

        :param offscreen: whether to create the list item in offscreen mode (faster) - default False
        :return: ListItem: a Kodi ListItem object constructed from the Playback object
        """

        Logger.debug("Creating list item from playback:", self)

        path = self.path
        list_item = xbmcgui.ListItem(label=self.pluginlabel, path=path, offscreen=offscreen)
        art = {k:v for k, v in {"thumb":self.thumbnail, "poster":self.poster, "fanart":self.fanart}.items() if v}
        if art:
            list_item.setArt(art)
        list_item.setProperty('IsPlayable', 'true')

        # if "pvr" in self.source:
        #     # use a proxy plugin url to actually trigger resuming live PVR playback...
        #     # (TODO: remove this hack when setResolvedUrl/ListItems are fixed to properly handle PVR links in listitem.path)
        #     args = urlencode({'mode': 'pvr_hack', 'path': self.path})
        #     list_item.setPath(f"plugin://plugin.switchback/?{args}")
        #     Logger.debug("Playback was PVR - override ListItem path to point to plugin proxy URL for PVR playback hack", list_item.getPath())
        #

        # PVR channels are not really videos! See: https://forum.kodi.tv/showthread.php?tid=381623&pid=3232826#pid3232826
        # So that's all we need to do for PVR playbacks

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
                'duration': (
                    int(self.duration) if self.duration is not None
                    else (int(self.totaltime) if self.totaltime is not None else None)
                ),
        }

        Logger.debug("^^^ Setting infolabels with:", infolabels)

        tag.set_info(infolabels)
        # Required, otherwise immediate Switchback mode won't resume properly
        # These keys are correct, even if CodeRabbit says they are not - see https://github.com/jurialmunkey/script.module.infotagger/blob/f138c1dd7201a8aff7541292fbfc61ed7b3a9aa1/resources/modules/infotagger/listitem.py#L204
        tag.set_resume_point({'ResumeTime':float(self.resumetime or 0.0), 'TotalTime':float(self.totaltime or 0.0)})
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
        with open(self.file, 'w', encoding='utf-8') as switchback_list_file:
            switchback_list_file.write('[]')

    def load_or_init(self) -> None:
        """
        Load a JSON-formatted PlaybackList from the PlaybackList file
        """
        Logger.info("Try to load PlaybackList from file:", self.file)
        # Ensure we start from a clean slate before loading from disk
        self.list = []
        try:
            with open(self.file, 'r', encoding='utf-8') as switchback_list_file:
                switchback_list_json = json.load(switchback_list_file)
                if not isinstance(switchback_list_json, list):
                    Logger.error(f"PlaybackList file [{self.file}] did not contain a JSON array — reinitialising")
                    self.init()
                    return
                for playback in switchback_list_json:
                    self.list.append(Playback(**playback))

        except FileNotFoundError:
            Logger.warning(f"Could not find: [{self.file}] - creating empty PlaybackList & file")
            self.init()
        except json.JSONDecodeError:
            Logger.error(f"JSONDecodeError - Unable to parse PlaybackList file [{self.file}] -  creating empty PlaybackList & file")
            self.init()
        # Let unexpected exceptions propagate

        Logger.info("PlaybackList is:", self.list)

    def save_to_file(self) -> None:
        """
        Save the PlaybackList to the PlaybackList file (as JSON)
        """
        Logger.info(f"Saving PlaybackList to file: {self.file}")
        import tempfile
        directory_name = os.path.dirname(self.file)
        temp_dir = None
        directory_name = os.path.dirname(self.file)
        if directory_name:
            xbmcvfs.mkdirs(directory_name)
            temp_dir = directory_name
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', dir=temp_dir) as temp_file:
            temp_file.write(self.toJson())
            temporary_name = temp_file.name
        os.replace(temporary_name, self.file)

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
