#!/usr/bin/env python
# _*_ coding:utf-8 _*_

import sys
import os

class Setting:
    WAIT_CIRCLE_IN_SECONDS = 5


class System:
    _is_running = True

    @staticmethod
    def is_running():
        return System._is_running

    @staticmethod
    def stopped():
        return not System._is_running

    @staticmethod
    def stop():
        System._is_running = False


class LoggerSetting:
    _log_path = None

    @staticmethod
    def get_log_path():
        if LoggerSetting._log_path is None:
            # LoggerSetting._log_path = os.path.join(os.path.dirname(
            #     os.path.realpath(__file__)), "")
            LoggerSetting._log_path = os.path.join(
                LoggerSetting._get_home_path(), 'logs')

            if not os.path.exists(LoggerSetting._log_path):
                os.mkdir(LoggerSetting._log_path)

            print("default log path:", LoggerSetting._log_path)

        return LoggerSetting._log_path

    @staticmethod
    def set_log_path(path):
        LoggerSetting._log_path = path

        if not os.path.exists(LoggerSetting._log_path):
            os.mkdir(LoggerSetting._log_path)
            print("new log path:", LoggerSetting._log_path)

    @staticmethod
    def _get_home_path():
        if sys.platform == 'win32':
            home_path = os.environ['USERPROFILE']
        elif sys.platform == 'linux':
            home_path = os.environ['HOME']
        else:
            raise Exception(f'undefined system. {sys.platform}')
        return home_path