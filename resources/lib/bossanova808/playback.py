import json
from dataclasses import dataclass, asdict
from typing import Optional

import xbmc
import xbmcgui

# noinspection PyPackages
from .utilities import clean_art_url, send_kodi_json
# noinspection PyPackages
from .logger import Logger


@dataclass
class Playback:
    """
    Stores whatever data can be determined about the currently playing (video) item in Kodi -
    what it is, where it's from (library/PVR/addon/file), and enough metadata to identify and
    resume it later. Video only - no audio/song support.
    """
    file: Optional[str] = None
    path: Optional[str] = None
    type: Optional[str] = None  # episode, movie, musicvideo, video (per Kodi types)
    source: Optional[str] = None  # kodi_library, pvr_live, pvr_recording, addon, file
    dbid: Optional[int] = None
    tvshowdbid: Optional[int] = None
    totalseasons: Optional[int] = None
    title: Optional[str] = None
    label: Optional[str] = None
    label2: Optional[str] = None
    thumbnail: Optional[str] = None
    fanart: Optional[str] = None
    poster: Optional[str] = None
    icon: Optional[str] = None
    year: Optional[int] = None
    showtitle: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    resumetime: Optional[int] = None
    totaltime: Optional[int] = None
    duration: Optional[int] = None
    channelname: Optional[str] = None
    channelnumberlabel: Optional[str] = None
    channelgroup: Optional[str] = None

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

        # Method 5: Conservative HTTP fallback for local addon proxies only
        if path_lower.startswith(('http://', 'https://')):
            # Exclude known WebDAV/cloud storage patterns
            webdav_patterns = [
                    '/dav/', 'webdav', '.nextcloud.', 'owncloud', '/remote.php/', 'dropbox', 'googledrive', 'onedrive',
            ]

            if not any(pattern in path_lower for pattern in webdav_patterns):
                # Additional check: look for typical addon URL structures
                if any(indicator in path_lower for indicator in ('plugin', 'addon')):
                    Logger.debug("Classified as addon via HTTP fallback heuristic", path_lower)
                    return True
            # If we still have an Addon.ID or container is a plugin, treat as addon
            addon_id_http = xbmc.getInfoLabel('ListItem.Property(Addon.ID)')
            container_path_lower_http = xbmc.getInfoLabel('Container.FolderPath').lower()
            if addon_id_http or container_path_lower_http.startswith('plugin://'):
                return True
            # Accept loopback hosts commonly used by addon proxy/resolvers
            if any(host in path_lower for host in ('127.0.0.1', 'localhost', '[::1]')):
                Logger.debug("Classified as addon via localhost HTTP fallback", path_lower)
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
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def update_playback_details(self, file: str, item: xbmcgui.ListItem) -> None:
        """
        Update the Playback object with details from a playing Kodi ListItem object and InfoLabels

        :param file: the current file Kodi is playing (from xbmc.Player().getPlayingFile())
        :param item: the current Kodi playing item (from xbmc.Player().getPlayingItem())
        """

        self.path = item.getPath()
        self.file = file
        self.label = item.getLabel()
        self.label2 = item.getLabel2()

        # Callers may update resumetime/totaltime themselves as playback progresses, but initialise
        # here in case of early exits etc.
        if self.source != "pvr_live":
            # Getting from the player directly is more reliable than using item.getVideoInfoTag() etc
            self.totaltime = self.duration = int(xbmc.Player().getTotalTime())
            self.resumetime = int(xbmc.Player().getTime())

        # Determine the Playback source - Kodi Library (...get DBID), PVR, Addon, or Non-Library file?
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
            Logger.debug("Not from Kodi library, PVR, or addon - treating as a non-library media file")
            self.source = "file"

        # TITLE
        if self.source != "pvr_live":
            self.title = xbmc.getInfoLabel('VideoPlayer.Title')
        else:
            self.title = xbmc.getInfoLabel('VideoPlayer.ChannelName')

        # MEDIA TYPE (see also source above, e.g. to distinguish PVR from non library video)
        if xbmc.getInfoLabel('VideoPlayer.TVShowTitle'):
            self.type = "episode"
            tvshowdbid_label = xbmc.getInfoLabel('VideoPlayer.TvShowDBID')
            try:
                self.tvshowdbid = int(tvshowdbid_label) if tvshowdbid_label else None
            except ValueError:
                self.tvshowdbid = None

        elif self.dbid:
            # A dbid alone doesn't distinguish movie from musicvideo - both live in the video
            # library with a dbid. Musicvideos carry artist metadata that movies don't.
            self.type = "musicvideo" if xbmc.getInfoLabel('VideoPlayer.Artist') else "movie"
        elif xbmc.getInfoLabel('VideoPlayer.ChannelName'):
            self.type = "video"  # use standard mediatype; PVR tracked via self.source
        else:
            self.type = "video"

        # ARTWORK - POSTER, FANART THUMBNAIL and ICON
        self.poster = clean_art_url(xbmc.getInfoLabel('Player.Art(tvshow.poster)') or xbmc.getInfoLabel('Player.Art(poster)') or xbmc.getInfoLabel('Player.Art(thumb)'))
        self.fanart = clean_art_url(xbmc.getInfoLabel('Player.Art(fanart)'))
        thumbnail = xbmc.getInfoLabel('Player.Art(thumb)') or (item.getArt('thumb') or '')
        self.thumbnail = clean_art_url(thumbnail)
        icon = xbmc.getInfoLabel('Player.Art(icon)') or (item.getArt('icon') or '')
        self.icon = clean_art_url(icon)

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
        # Episodes -> we also want the number of seasons so callers can force-browse to the
        # appropriate spot after a resumed playback
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
