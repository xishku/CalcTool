#!/usr/bin/env python
# _*_ coding:utf-8 _*_

import sys
import os

import yaml

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

class TdxSetting:
    _instance = None
    _config_data = None
    _lock = False  # 用于模拟简单的线程安全，实际高并发可用 threading.Lock

    def __new__(cls):
        """单例模式的__new__方法"""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化，确保配置只加载一次"""
        if not self._lock:
            self._load_config()
            TdxSetting._lock = True
    
    def _load_config(self):
        """内部方法：加载配置文件"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "setting.yaml")
            print(f"配置文件路径: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as file:
                TdxSetting._config_data = yaml.safe_load(file)
                
            if not TdxSetting._config_data:
                TdxSetting._config_data = {}
                print("警告: 配置文件为空或格式不正确")
                
        except FileNotFoundError:
            print(f"错误: 配置文件未找到: {config_path}")
            TdxSetting._config_data = {}
        except yaml.YAMLError as e:
            print(f"错误: YAML解析失败: {e}")
            TdxSetting._config_data = {}
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            TdxSetting._config_data = {}
    
    @classmethod
    def get_config(cls):
        """获取完整配置（类方法）"""
        if cls._config_data is None:
            # 如果尚未初始化，创建实例
            cls()
        return cls._config_data.copy()  # 返回副本以防意外修改
    
    @classmethod
    def get_tdx_config(cls):
        """获取TDX特定配置（向后兼容您原来的方法名）"""
        config = cls.get_config()
        
        # 确保返回标准化的TDX配置
        tdx_config = {
            'tdx_server': config.get('tdx_server', ''),
            'tdx_port': config.get('tdx_port', 7709)
        }
        return tdx_config
    
    @classmethod
    def get_value(cls, key, default=None):
        """获取指定配置项的值"""
        config = cls.get_config()
        
        # 支持嵌套键，如 'database.host'
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value


# class TdxSetting:
#     @staticmethod
#     def get_tdx_config():
#         # 打开并读取YAML文件
#         file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "setting.yaml")
#         print("file", file)
#         with open(file, 'r', encoding='utf-8') as file:
#             config_data = yaml.safe_load(file)  # 安全加载，避免执行任意代码

#             # 访问数据
#             # print(config_data)
#             # 输出: {'tdx_server': '115.238.56.198', 'tdx_port': 7709, 'database': {'host': 'localhost', 'port': 3306}}

#             # print(f"服务器地址: {config_data['tdx_server']}")
#             # print(f"端口号: {config_data['tdx_port']}")
#             return config_data