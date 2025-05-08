# -*- coding: utf-8 -*-

import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon

""" Just a bunch of very handy Kodi constants """

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_AUTHOR = ADDON.getAddonInfo('author')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_ARGUMENTS = f'{sys.argv}'
CWD = ADDON.getAddonInfo('path')
LANGUAGE = ADDON.getLocalizedString
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
LOG_PATH = xbmcvfs.translatePath('special://logpath')
KODI_VERSION = xbmc.getInfoLabel('System.BuildVersion')
try:
    KODI_MAJOR_VERSION = int(xbmc.getInfoLabel('System.BuildVersionCode').split('.')[0])
except (ValueError, IndexError):
    KODI_MAJOR_VERSION = 21
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"
HOME_WINDOW = xbmcgui.Window(10000)
WEATHER_WINDOW = xbmcgui.Window(12600)
