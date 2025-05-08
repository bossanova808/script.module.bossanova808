# -*- coding: utf-8 -*-

# noinspection PyUnresolvedReferences
import xbmc
# noinspection PyPackages
from .constants import *


class Logger:

    @staticmethod
    def log(message, level=xbmc.LOGDEBUG):
        """
        Log a message to the Kodi log file.
        If we're unit testing a module outside Kodi, print to the console instead.

        :param message: The message to log
        :param level: The kodi log level to log at, default xbmc.LOGDEBUG
        :return:
        """
        #
        if xbmc.getUserAgent():
            xbmc.log(f'### {ADDON_NAME} {ADDON_VERSION}: {str(message)}', level)
        else:
            print(str(message))

    @staticmethod
    def info(message):
        """
        Log a message to the Kodi log file at INFO level.

        :param message: The message to log
        :return:
        """
        Logger.log(message, xbmc.LOGINFO)

    @staticmethod
    def warning(message):
        """
        Log a message to the Kodi log file at WARNING level.

        :param message: The message to log
        :return:
        """
        Logger.log(message, xbmc.LOGWARNING)

    @staticmethod
    def error(message):
        """
        Log a message to the Kodi log file at ERROR level.

        :param message: The message to log
        :return:
        """
        Logger.log(message, xbmc.LOGERROR)

    @staticmethod
    def debug(*messages):
        """
        Log messages to the Kodi log file at DEBUG level.

        :param messages: The message(s) to log
        :return:
        """
        for message in messages:
            Logger.log(message, xbmc.LOGDEBUG)

    @staticmethod
    def footprints(startup=True, extra_message=None):
        """
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
            if extra_message:
                Logger.info(extra_message)

    @staticmethod
    def start(extra_message=None):
        Logger.footprints(startup=True, extra_message=extra_message)

    @staticmethod
    def stop(extra_message=None):
        Logger.footprints(startup=False, extra_message=extra_message)
