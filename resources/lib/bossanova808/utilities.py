# -*- coding: utf-8 -*-

import json
import re
import xml.etree.ElementTree as ElementTree
from urllib.parse import unquote

from .constants import *
from .logger import Logger


def set_property(window, name, value=""):
    """
    Set a property on a window.
    To clear a property, provide an empty string

    :param window: Required.  The Kodi window on which to set the property.
    :param name: Required.  Name of the property.
    :param value: Optional (defaults to "").  Set the property to this value.  An empty string clears the property.
    """
    if value is None:
        window.clearProperty(name)

    value = str(value)
    if value:
        Logger.debug(f'Setting window property {name} to value {value}')
        window.setProperty(name, value)
    else:
        Logger.debug(f'Clearing window property {name}')
        window.clearProperty(name)


def clear_property(window, name):
    """
    Clear a property on a window.

    :param window:
    :param name:
    :return:
    """
    set_property(window, name, "")


def get_property(window, name):
    """
    Return the value of a window property

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property
    """
    return window.getProperty(name)


def get_property_as_bool(window, name):
    """
    Return the value of a window property as a boolean

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property in boolean form
    """
    return window.getProperty(name).lower() == "true"


def send_kodi_json(human_description, json_string):
    """
    Send a JSON command to Kodi, logging the human description, command, and result as returned.

    :param human_description: Required. A human sensible description of what the command is aiming to do/retrieve.
    :param json_string: Required. The json command to send.
    :return: the json object loaded from the result string
    """
    Logger.debug(f'KODI JSON RPC command: {human_description} [{json_string}]')
    result = xbmc.executeJSONRPC(json_string)
    Logger.debug(f'KODI JSON RPC result: {result}')
    return json.loads(result)


def get_setting(setting) -> str or None:
    """
    Helper function to get an addon setting

    :param setting: The addon setting to return
    :return: the setting value
    """
    return ADDON.getSetting(setting).strip()


def get_setting_as_bool(setting) -> bool:
    """
    Helper function to get bool type from settings

    :param setting: The addon setting to return
    :return: the setting value as boolean
    """
    return get_setting(setting).lower() == "true"


def get_kodi_setting(setting):
    """
    Get a Kodi setting value - for settings, see https://github.com/xbmc/xbmc/blob/18f70e7ac89fd502b94b8cd8db493cc076791f39/system/settings/settings.xml

    :param setting:
    :return: The value of the Kodi setting (remembers to cast to the appropriate type!)
    """
    json_dict = {"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": {"setting": setting}, "id": 1}
    query = json.dumps(json_dict)
    properties_json = send_kodi_json(f'Get Kodi setting {setting}', query)
    return properties_json['result']['value']


def get_advancedsetting(setting_path) -> str or None:
    """
    Helper function to extract a setting from Kodi's advancedsettings.xml file,
    Remember: cast the result appropriately, and provide the Kodi default value as a fallback if the setting is not found
    E.g:
    Store.ignore_seconds_at_start = int(get_advancedsetting('./video/ignoresecondsatstart')) or 180

    :param setting_path: The advanced setting, in path (section/setting) form, to look for (e.g. video/ignoresecondsatstart)
    :return: The setting value if found, None if not found/advancedsettings.xml doesn't exist
    """
    advancedsettings_file = xbmcvfs.translatePath("special://profile/advancedsettings.xml")

    if not xbmcvfs.exists(advancedsettings_file):
        return None

    root = None
    try:
        root = ElementTree.parse(advancedsettings_file).getroot()
        Logger.info("Found and parsed advancedsettings.xml")
    except IOError:
        Logger.error("Could not read advancedsettings.xml")
    except ElementTree.ParseError:
        Logger.error("Could not parse advancedsettings.xml")
        return None

    setting_element = root.find(setting_path)
    if setting_element is not None:
        return setting_element.text

    Logger.error(f"Setting [{setting_path}] not found in advancedsettings.xml")
    return None


def clean_art_url(kodi_url: str) -> str:
    """
    Return a cleaned, HTML unquoted version of the art url, removing any pre-pended Kodi stuff and any trailing slash
                   .replace("pvrchannel_tv@", "")
                   .replace("pvrrecording@", "")
                   .replace("video@", "")

    :param kodi_url:
    :return: cleaned url string
    """
    cleaned_url = unquote(kodi_url).replace("image://", "").rstrip("/")
    cleaned_url = re.sub(r'^.*?@', '', cleaned_url)  # video@, pvrchannel_tv@, pvrrecording@ etc
    return cleaned_url


def is_playback_paused() -> bool:
    """
    Helper function to return Kodi player state.
    (Odd this is needed, it should be a testable state on Player really...)

    :return: Boolean indicating player paused state
    """
    return bool(xbmc.getCondVisibility("Player.Paused"))


def footprints(startup=True, extra_message=None):
    """
    TODO - this has moved to Logger - updated all addons to use the Logger version, not this, then ultimately remove this!
    Log the startup/exit of an addon and key Kodi details that are helpful for debugging

    :param extra_message: Any extra message to log, such as "(Service)" or "(Plugin)" if it helps to identify component elements
    :param startup: Optional, default True.  If true, log the startup of an addon, otherwise log the exit.
    """
    if startup:
        Logger.info(f'Start {ADDON_NAME} {ADDON_VERSION}')
        if extra_message:
            Logger.info(extra_message)
        Logger.info(f'Kodi {KODI_VERSION} (Major version {KODI_MAJOR_VERSION})')
        Logger.info(f'Python {sys.version}')
        Logger.info(f'Run {ADDON_ARGUMENTS}')
    else:
        Logger.info(f'Finish {ADDON_NAME}')
