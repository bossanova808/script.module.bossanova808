import sys
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon

""" Handy Kodi constants """

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_ICON = ADDON.getAddonInfo('icon')
ADDON_AUTHOR = ADDON.getAddonInfo('author')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_ARGUMENTS = f'{sys.argv}'
ADDON_SETTINGS_PATH = PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ADDON_PATH = CWD = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
TRANSLATE = LANGUAGE = ADDON.getLocalizedString
LOG_PATH = xbmcvfs.translatePath('special://logpath')
KODI_VERSION = xbmc.getInfoLabel('System.BuildVersion')
# Fallback: try System.BuildVersion (e.g. "21.0.0") then default to 21 (Omega)
try:
    KODI_MAJOR_VERSION = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
except Exception:
    KODI_MAJOR_VERSION = 21  # explicit fallback to Kodi 21 (Omega)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"
HOME_WINDOW = xbmcgui.Window(10000)
WEATHER_WINDOW = xbmcgui.Window(12600)
