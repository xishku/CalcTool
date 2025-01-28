#!/usr/bin/env python
# _*_ coding:utf-8 _*_

import logging
import datetime
import time
import os
import threading
import logging.config
import yaml

from .setting import LoggerSetting


class LoggerConfig:
    _loaded = None
    _lock = threading.Lock()

    @staticmethod
    def load_config():
        if LoggerConfig._loaded:
            return

        with LoggerConfig._lock:
            if LoggerConfig._loaded:
                return

            file_name = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), 'logging.yaml')
            
            print("file_name=", file_name)

            with open(file_name, 'r') as f:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)

            LoggerConfig._loaded = True


class Logger():
    MAX_BYTES = 0x1000000
    BACKUP_COUNT = 50
    _log = None

    @staticmethod
    def log_maker():

        file_name = os.path.join(LoggerSetting.get_log_path(),
            "trace.log")
        return logging.handlers.RotatingFileHandler(
            file_name, 'w', Logger.MAX_BYTES, Logger.BACKUP_COUNT, "utf-8")

    @staticmethod
    def log():
        if Logger._log is None:
            LoggerConfig.load_config()
            Logger._log = logging.getLogger("root")
        return Logger._log

if __name__== "__main__" :
    Logger.log().info("test")


