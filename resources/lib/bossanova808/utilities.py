import json
import re
import xml.etree.ElementTree as ElementTree
from urllib.parse import unquote

from bossanova808.constants import *
from bossanova808.logger import Logger


def set_property(window: xbmcgui.Window, name: str, value: str = None) -> None:
    """
    Set a property on a window.
    To clear a property, provide an empty string or (better) use clear_property() below, instead.

    :param window: The Kodi window on which to set the property.
    :param name:Name of the property.
    :param value: Optional (default None).  Set the property to this value.  An empty string, or None, clears the property, but better to use clear_property().
    """
    if value is None:
        window.clearProperty(name)
        return

    value = str(value)
    if value:
        Logger.debug(f'Setting window property {name} to value {value}')
        window.setProperty(name, value)
    else:
        clear_property(window, name)


def clear_property(window: xbmcgui.Window, name: str) -> None:
    """
    Clear a property on a window.

    :param window:
    :param name:
    """
    Logger.debug(f'Clearing window property {name}')
    window.clearProperty(name)


def get_property(window: xbmcgui.Window, name: str) -> str or None:
    """
    Return the value of a window property

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property, or None if not set
    """
    return window.getProperty(name)


def get_property_as_bool(window: xbmcgui.Window, name: str) -> bool or None:
    """
    Return the value of a window property as a boolean

    :param window: the Kodi window to get the property value from
    :param name: the name of the property to get
    :return: the value of the window property in boolean form, or None if not set
    """
    return window.getProperty(name).lower() == "true"


def send_kodi_json(human_description: str, json_dict_or_string: str or dict) -> dict or None:
    """
    Send a JSON command to Kodi, logging the human description, command, and result as returned.

    :param human_description: A textual description of the command being sent to KODI. Helpful for debugging.
    :param json_dict_or_string: The JSON RPC command to be sent to KODI, as a dict or string
    :return: A dictionary of the parsed JSON response returned by KODI or `None` if the response cannot be parsed successfully.
    """
    Logger.debug(f'KODI JSON RPC command: {human_description}', json_dict_or_string)
    if isinstance(json_dict_or_string, dict):
        json_dict_or_string = json.dumps(json_dict_or_string)
    result = xbmc.executeJSONRPC(json_dict_or_string)
    try:
        result = json.loads(result)
    except json.JSONDecodeError:
        Logger.error(f'Unable to parse JSON RPC result from KODI:',result)
        return None
    Logger.debug(f'KODI JSON RPC result:', result)
    return result


def get_setting(setting: str) -> str or None:
    """
    Helper function to get an addon setting

    :param setting: The addon setting to return
    :return: the setting value, or None if not found
    """
    return ADDON.getSetting(setting).strip()


def get_setting_as_bool(setting: str) -> bool or None:
    """
    Helper function to get bool type from settings

    :param setting: The addon setting to return
    :return: the setting value as boolean, or None if not found
    """
    if get_setting(setting).lower() == "true":
        return True
    elif get_setting(setting).lower() == "false":
        return False
    return None


def get_kodi_setting(setting: str) -> str or None:
    """
    Get a Kodi setting value - for settings, see https://github.com/xbmc/xbmc/blob/18f70e7ac89fd502b94b8cd8db493cc076791f39/system/settings/settings.xml

    :param setting: the Kodi setting to return
    :return: The value of the Kodi setting (remember to cast this to the appropriate type before use!)
    """
    json_dict = {"jsonrpc":"2.0", "method":"Settings.GetSettingValue", "params":{"setting":setting}, "id":1}
    properties_json = send_kodi_json(f'Get Kodi setting {setting}', json_dict)
    return properties_json['result']['value']


def get_advancedsetting(setting_path: str) -> str or None:
    """
    Helper function to extract a setting from Kodi's advancedsettings.xml file,
    Remember: cast the result appropriately and provide the Kodi default value as a fallback if the setting is not found.
    E.g.::
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
    Return a cleaned, HTML-unquoted version of the art url, removing any pre-pended Kodi stuff and any trailing slash

    :param kodi_url:
    :return: cleaned url string
    """
    cleaned_url = unquote(kodi_url).replace("image://", "").rstrip("/")
    cleaned_url = re.sub(r'^.*?@', '', cleaned_url)  # pre-pended video@, pvrchannel_tv@, pvrrecording@ etc
    return cleaned_url


def is_playback_paused() -> bool:
    """
    Helper function to return Kodi player state.
    (Odd this is needed, it should be a testable state on Player really...)

    :return: Boolean indicating player paused state
    """
    return bool(xbmc.getCondVisibility("Player.Paused"))


def footprints(startup: bool = True) -> None:
    """
    TODO - this has moved to Logger - update all addons to use Logger.start/.stop directly, then ultimately remove this!
    Log the startup/exit of an addon and key Kodi details that are helpful for debugging

    :param startup: Optional, default True.  If true, log the startup of an addon, otherwise log the exit.
    """
    if startup:
        Logger.start()
    else:
        Logger.stop()
