#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
股票回看分析工具 v0.7
======================
纯GUI操作的桌面应用，为研究员提供从文件导入观察点，
在K线图上快速回看"关注日期"前后行情走势的交互式分析。

文档编号：SRS-STOCK-REVIEW-V0.7
"""

# ==================== 导入区 ====================
import sys
import os
import json
import time
from collections import OrderedDict
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

import numpy as np
import pandas as pd

# SDK路径配置
SDK_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        "../../../src")
sys.path.append(SDK_PATH)

from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
import pyautogui
import pygetwindow as gw

# PyQt6导入
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMenu, QLabel, QStatusBar, QFileDialog, QMessageBox, QHeaderView,
    QSizePolicy, QGraphicsDropShadowEffect, QPushButton, QScrollArea,
    QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QFont, QColor, QCursor

# Matplotlib导入与PyQt6集成
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# 设置matplotlib支持中文
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei UI', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 常量配置区 ====================

# 窗口尺寸常量
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 700

# 列表面板常量
LIST_PANEL_FIXED_WIDTH = 225
LIST_COL_DATETIME = 0
LIST_COL_SYMBOL = 1
LIST_COL_FOCUS_DATE = 2

# K线画布常量
CHART_HEIGHT = 500
MAIN_CHART_RATIO = 0.50
VOL_CHART_RATIO = 0.20
MACD_CHART_RATIO = 0.20
DEFAULT_VISIBLE_BARS = 50
PRELOAD_BARS = 100
MIN_VISIBLE_BARS = 5
MAX_VISIBLE_BARS = 201

# 指标参数
MA_PERIODS = [5, 10, 20, 60]
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# 止盈止损默认参数
DEFAULT_TP_RATIO = 0.15
DEFAULT_SL_RATIO = -0.10
DEFAULT_TPSL_DAYS = 10

# 缓存常量
MAX_CACHE_SIZE = 5
DEFAULT_CACHE_TTL_MINUTES = 5

# 颜色常量 - 金融终端深色主题
COLOR_BG_PRIMARY = '#1A1D23'
COLOR_BG_SECONDARY = '#23272E'
COLOR_BG_TERTIARY = '#2C313C'
COLOR_TEXT_PRIMARY = '#E8EAED'
COLOR_TEXT_SECONDARY = '#B0B8C4'
COLOR_TEXT_MUTED = '#7A8490'
COLOR_RED_UP = '#EF4444'
COLOR_GREEN_DOWN = '#22C55E'
COLOR_MA5 = '#F59E0B'
COLOR_MA10 = '#A855F7'
COLOR_MA20 = '#22C55E'
COLOR_MA60 = '#3B82F6'
COLOR_MACD_DIF = '#E8EAED'
COLOR_MACD_DEA = '#F59E0B'
COLOR_CROSSHAIR_H = '#EF4444'
COLOR_CROSSHAIR_V = '#3B82F6'
COLOR_SELECTION = '#2E86AB'
COLOR_POPUP_BG = 'rgba(26, 29, 35, 0.95)'

# 配置文件名
CONFIG_FILENAME = 'config.json'

# ==================== 中文字符串常量 ====================
# 通用
TXT_READY = '就绪'
TXT_NO_DATA = '无数据'
TXT_LOAD_FAILED = '加载失败'
TXT_DAY = '天'
TXT_DAY_PREFIX = '第'

# 列表表头
TXT_COL_DATETIME = '日期时间'
TXT_COL_SYMBOL = '股票代码'
TXT_COL_FOCUS_DATE = '关注日期'
LIST_HEADER_LABELS = [TXT_COL_DATETIME, TXT_COL_SYMBOL, TXT_COL_FOCUS_DATE]

# 文件解析
TXT_CONFIG_READ_FAILED = '配置文件读取失败，使用默认配置'
TXT_FILE_DECODE_FAILED = '无法解码文件'
TXT_COL_INSUFFICIENT = '列数不足'
TXT_SKIPPED = '已跳过'
TXT_SYMBOL_EMPTY = '股票代码为空'
TXT_FIELD_PARSE_FAILED = '字段解析失败'
TXT_NO_VALID_DATE = '无有效关注日期，保留行'
TXT_FILE_PARSE_DONE = '文件解析完成'
TXT_TOTAL_LINES = '总行数'
TXT_VALID_ITEMS = '有效项'
TXT_SKIP_COUNT = '跳过'

# 缓存
TXT_CACHE_EXPIRED = '缓存过期'
TXT_CACHE_HIT = '缓存命中'
TXT_CACHE_LRU_EVICT = 'LRU淘汰缓存'
TXT_CACHE_WRITE = '缓存写入'
TXT_CURRENT_CACHE_COUNT = '当前缓存数'

# 数据加载
TXT_REQUEST_DATA = '请求行情数据'
TXT_NO_DATA_CHECK_LOCAL = '未获取到数据（检查本地day文件）'
TXT_DATA_LOAD_EXCEPTION = '数据加载异常'

# Popup
TXT_OPEN = '开'
TXT_HIGH = '高'
TXT_LOW = '低'
TXT_CLOSE = '收'
TXT_AMOUNT = '额'
TXT_BILLION = '亿'
TXT_VS_ATTENTION = 'vs关注日'

# K线图
TXT_PRICE = '价格'
TXT_VOLUME = '成交量'

# 止盈止损
TXT_TAKE_PROFIT = '止盈'
TXT_STOP_LOSS = '止损'
TXT_FIRST_TP = '先止盈'
TXT_FIRST_SL = '先止损'
TXT_NOT_TRIGGERED = '未触发'
TXT_TPSL_CALC_FAILED = '止盈止损计算失败'
TXT_TP_PCT = '止盈%:'
TXT_SL_PCT = '止损%:'
TXT_DAYS_LABEL = '天数:'
TXT_UPDATE = '更新'
TXT_TPSL_DAYS_MUST_POSITIVE = '止盈止损天数必须大于0'
TXT_TPSL_UPDATED = '止盈止损已更新'
TXT_PLEASE_SELECT_STOCK_DATE = '请先选择股票和关注日期'
TXT_PLEASE_SELECT_STOCK = '请先选择股票'

# 工具栏
TXT_ATTENTION_DATE = '关注日'
TXT_TONGHUASHUN = '同花顺'
TXT_JUMP_TO_THS = '跳转到同花顺查看当前股票'
TXT_TP_PCT_TOOLTIP = '止盈百分比，如15表示15%'
TXT_SL_PCT_TOOLTIP = '止损百分比（负数），如-10表示止损10%'
TXT_TPSL_DAYS_TOOLTIP = '止盈止损交易日天数，如10表示10个交易日'
TXT_TPSL_UPDATE_TOOLTIP = '根据新的止盈止损设置刷新计算结果'

# 菜单
TXT_FILE_MENU = '文件(&F)'
TXT_OPEN_FILE = '\U0001f4c1 打开文件...'
TXT_EXIT = '退出'
TXT_VIEW_MENU = '视图(&V)'
TXT_ZOOM_IN = '\U0001f50d 放大'
TXT_ZOOM_OUT = '\U0001f50b 缩小'
TXT_RESET_VIEW = '\U0001f504 重置视图'
TXT_EXPORT_PNG = '\U0001f4ce 导出PNG...'
TXT_HELP_MENU = '帮助(&H)'
TXT_ABOUT = '关于...'

# 右键菜单
TXT_ZOOM_IN_MENU = '\U0001f50d 放大 (Zoom In)'
TXT_ZOOM_OUT_MENU = '\U0001f50b 缩小 (Zoom Out)'
TXT_RESET_VIEW_MENU = '\U0001f504 重置视图 (Reset)'
TXT_EXPORT_PNG_MENU = '\U0001f4ce 导出PNG (Export)'

# 导出
TXT_EXPORT_SUCCESS = '导出成功'
TXT_CHART_EXPORTED = '图表已导出'
TXT_EXPORT_FAILED = '导出PNG失败'
TXT_PNG_IMAGE = 'PNG图片'
TXT_EXPORT_PNG_TITLE = '导出PNG'
TXT_IMAGE_SAVED = '图片已保存至'
TXT_SAVE_FAILED = '保存失败'

# 文件对话框
TXT_SELECT_FILE = '选择观察点文件'
TXT_TAB_FILE_FILTER = 'Tab分隔文件 (*.txt *.csv *.tsv);;所有文件 (*)'
TXT_ALL_FILE_FILTER = '所有文件 (*)'
TXT_FILE_LOADING = '文件加载中...'

# 加载结果
TXT_LOAD_SUCCESS = '加载成功'
TXT_VALID = '有效'
TXT_LOAD_COMPLETE = '加载完成'
TXT_VALID_RECORDS = '有效记录'
TXT_SKIPPED_LINES = '跳过行数'
TXT_LOAD_FAILED_TITLE = '加载失败'
TXT_CANNOT_PARSE = '未能解析出有效数据。\n请检查文件格式。'
TXT_KLINE_LOADING = '加载行情中...'
TXT_KLINE_LOADED = 'K线加载完成'
TXT_KLINE_DATA_LOAD_FAILED = '数据加载失败'
TXT_LOAD_ERROR = '加载错误'
TXT_CANNOT_LOAD_DATA = '的行情数据'

# 双击
TXT_DOUBLE_CLICK_LOCATE = '双击定位'
TXT_FOCUS_DAY = '焦点日'

# 同花顺
TXT_JUMPING_THS = '正在跳转同花顺'
TXT_THS_NOT_FOUND = '未找到同花顺，请手动打开后输入'
TXT_THS_JUMP = '同花顺跳转'
TXT_THS_WINDOW_NOT_FOUND = '未找到同花顺窗口，请先打开同花顺再输入'
TXT_THS_CANNOT_ACTIVATE = '同花顺已打开，但无法激活窗口'
TXT_THS_LOCATED = '已在同花顺中定位到'
TXT_DAILY_KLINE = '的日K线'
TXT_START_THS = '启动同花顺'
TXT_THS_JUMP_FAILED = '同花顺跳转失败'
TXT_THS_JUMP_EXCEPTION = '跳转失败'
TXT_INVALID_PARAMS = '无效参数'

# 关于
TXT_ABOUT_TITLE = '关于'
TXT_ABOUT_CONTENT = ('<h3>股票回看分析工具 v0.7</h3>'
                     '<p>提供K线历史回放与分析功能</p>'
                     '<p>基于PyQt6 + matplotlib</p>'
                     '<p>文档编号: SRS-STOCK-REVIEW-V0.7</p>')

# 列表
TXT_LIST_LOADED = '列表加载完成'
TXT_KLINE_COUNT = '根K线'

# 窗口标题
TXT_APP_TITLE = '股票回看分析工具 v0.7'
TXT_APP_STARTED = '股票回看分析工具启动'
TXT_PROGRAM_EXIT = '程序退出，退出码='

# 同花顺搜索关键词
THS_KEYWORDS = ['同花顺', 'THS', 'hexin']


def load_config() -> Dict[str, Any]:
    """从工作目录加载config.json配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               "../../../../../", CONFIG_FILENAME)
    default_config = {
        "api_endpoint": "https://data.service/api/v2",
        "cache_ttl_minutes": DEFAULT_CACHE_TTL_MINUTES,
        "default_window_size": [DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT],
        "log_level": "INFO"
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                default_config.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            Logger.log().warning(f"{TXT_CONFIG_READ_FAILED}: {e}")
    return default_config


# 全局配置实例
CONFIG = load_config()


# ==================== 数据层 ====================

class FileParser:
    """Tab分隔文件解析器，负责数据清洗与多关注日展开"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.parsed_data: List[List] = []
        self.total_lines = 0
        self.valid_lines = 0
        self.skipped_lines = 0

    def parse(self) -> bool:
        """解析文件并返回是否成功"""
        encodings = ['utf-8', 'gb18030', 'gbk']
        raw_lines: List[str] = []

        for encoding in encodings:
            try:
                with open(self.filepath, 'r', encoding=encoding) as f:
                    raw_lines = f.readlines()
                break
            except (UnicodeDecodeError, IOError):
                continue
        else:
            Logger.log().error(f"{TXT_FILE_DECODE_FAILED}: {self.filepath}")
            return False

        self.total_lines = len(raw_lines)
        self.parsed_data.clear()

        for line_num, raw_line in enumerate(raw_lines, 1):
            line = raw_line.strip()
            if not line:
                self.skipped_lines += 1
                continue

            fields = line.split('\t')
            if len(fields) < 2:
                Logger.log().warning(
                    f"{TXT_COL_INSUFFICIENT}({len(fields)}) {TXT_SKIPPED}")
                self.skipped_lines += 1
                continue

            dt_str = fields[0].strip()
            symbol = fields[1].strip()

            if not symbol:
                Logger.log().warning(
                    f"{TXT_SYMBOL_EMPTY} {TXT_SKIPPED}")
                self.skipped_lines += 1
                continue

            focus_dates: List[int] = []
            tp_ratio = DEFAULT_TP_RATIO
            sl_ratio = DEFAULT_SL_RATIO
            float_count = 0

            for i in range(2, len(fields)):
                fd_raw = fields[i].strip()
                if not fd_raw:
                    continue
                try:
                    fd_int = int(fd_raw)
                    focus_dates.append(fd_int)
                except ValueError:
                    try:
                        fd_float = float(fd_raw)
                        if float_count == 0:
                            tp_ratio = fd_float
                        elif float_count == 1:
                            sl_ratio = fd_float
                        float_count += 1
                    except ValueError:
                        Logger.log().warning(
                            f"{TXT_FIELD_PARSE_FAILED}[{fd_raw}]")

            if len(fields) >= 3 and not focus_dates and float_count == 0:
                has_fd_field = any(
                    fields[i].strip() for i in range(2, len(fields)))
                if has_fd_field:
                    Logger.log().warning(TXT_NO_VALID_DATE)

            if not focus_dates:
                focus_dates = [0]

            for fd in focus_dates:
                self.parsed_data.append(
                    [dt_str, symbol, fd, tp_ratio, sl_ratio])
                self.valid_lines += 1

        Logger.log().info(
            f"{TXT_FILE_PARSE_DONE}: {self.filepath} | "
            f"{TXT_TOTAL_LINES}={self.total_lines} "
            f"{TXT_VALID_ITEMS}={self.valid_lines} "
            f"{TXT_SKIP_COUNT}={self.skipped_lines}")
        return self.valid_lines > 0

    def get_data(self) -> List[List]:
        """返回解析后的数据列表 [[dt, sym, fd, tp, sl], ...]"""
        return self.parsed_data


class DataCacheManager:
    """LRU缓存管理器，管理标的行情数据缓存"""

    def __init__(self, max_size: int = MAX_CACHE_SIZE,
                 ttl_minutes: int = CONFIG.get('cache_ttl_minutes',
                                              DEFAULT_CACHE_TTL_MINUTES)):
        self.max_size = max_size
        self.ttl_seconds = ttl_minutes * 60
        self._cache: OrderedDict[str, Tuple[pd.DataFrame, float]] = OrderedDict()

    def get(self, symbol: str) -> Optional[pd.DataFrame]:
        """从缓存获取数据，返回DataFrame或None"""
        if symbol not in self._cache:
            return None

        df, timestamp = self._cache[symbol]
        if (time.time() - timestamp) > self.ttl_seconds:
            del self._cache[symbol]
            Logger.log().info(f"{TXT_CACHE_EXPIRED}: {symbol}")
            return None

        self._cache.move_to_end(symbol)
        Logger.log().info(f"{TXT_CACHE_HIT}: {symbol}")
        return df.copy()

    def put(self, symbol: str, df: pd.DataFrame) -> None:
        """写入缓存，超出上限时淘汰最旧条目"""
        if symbol in self._cache:
            del self._cache[symbol]
        elif len(self._cache) >= self.max_size:
            oldest_key, _ = self._cache.popitem(last=False)
            Logger.log().info(f"{TXT_CACHE_LRU_EVICT}: {oldest_key}")

        self._cache[symbol] = (df.copy(), time.time())
        Logger.log().debug(
            f"{TXT_CACHE_WRITE}: {symbol}, "
            f"{TXT_CURRENT_CACHE_COUNT}={len(self._cache)}")

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()

    def __contains__(self, symbol: str) -> bool:
        return symbol in self._cache

    def __len__(self) -> int:
        return len(self._cache)


class DataLoader(QThread):
    """异步数据加载线程，通过信号回调主线程更新UI"""

    data_ready = pyqtSignal(str, object)
    error_occurred = pyqtSignal(str, str)

    def __init__(self, agent: TdxDataAgent,
                 cache_mgr: DataCacheManager):
        super().__init__()
        self.agent = agent
        self.cache_mgr = cache_mgr
        self._symbol = ''
        self._start_date = 0
        self._end_date = 0
        self._running = False

    def load_data(self, symbol: str,
                  start_date: int, end_date: int) -> None:
        """设置加载参数并启动线程"""
        self._symbol = symbol
        self._start_date = start_date
        self._end_date = end_date
        self._running = True
        if not self.isRunning():
            self.start()

    def cancel(self) -> None:
        """取消当前加载"""
        self._running = False

    def run(self) -> None:
        """线程执行入口"""
        try:
            symbol = self._symbol
            cached_df = self.cache_mgr.get(symbol)
            if cached_df is not None and not cached_df.empty:
                self.data_ready.emit(symbol, cached_df)
                return

            Logger.log().info(
                f"{TXT_REQUEST_DATA}: {symbol} | "
                f"{self._start_date} ~ {self._end_date}")

            df = self.agent.read_kdata_cache(
                str(symbol),
                str(self._start_date),
                str(self._end_date))

            if not self._running:
                return

            if df is None or df.empty:
                self.error_occurred.emit(symbol, TXT_NO_DATA_CHECK_LOCAL)
                return

            self.cache_mgr.put(symbol, df)
            self.data_ready.emit(symbol, df)

        except Exception as e:
            Logger.log().error(
                f"{TXT_DATA_LOAD_EXCEPTION} [{self._symbol}]: {e}")
            self.error_occurred.emit(self._symbol, str(e))


# ==================== 业务逻辑层 ====================

class IndicatorCalc:
    """技术指标计算器（MA均线 / MACD）"""

    @staticmethod
    def calc_ma(df: pd.DataFrame,
                periods: List[int] = MA_PERIODS) -> pd.DataFrame:
        """计算移动平均线"""
        result = df.copy()
        for p in periods:
            result[f'MA{p}'] = result['r_close'].rolling(window=p).mean()
        return result

    @staticmethod
    def calc_macd(df: pd.DataFrame,
                  fast: int = MACD_FAST,
                  slow: int = MACD_SLOW,
                  signal_period: int = MACD_SIGNAL) -> pd.DataFrame:
        """计算MACD指标"""
        result = df.copy()
        close = result['r_close']
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        result['DIF'] = ema_fast - ema_slow
        result['DEA'] = result['DIF'].ewm(
            span=signal_period, adjust=False).mean()
        result['MACD'] = 2 * (result['DIF'] - result['DEA'])
        return result

    @staticmethod
    def calc_all(df: pd.DataFrame) -> pd.DataFrame:
        """计算全部指标（MA + MACD）"""
        result = IndicatorCalc.calc_ma(df)
        result = IndicatorCalc.calc_macd(result)
        return result


class ViewportController:
    """视窗控制器：管理K线可视区间、缩放、平移、焦点定位"""

    def __init__(self, total_bars: int = 0):
        self.total_bars = total_bars
        self.visible_count = DEFAULT_VISIBLE_BARS
        self.focus_index = total_bars // 2
        self.view_start: int = 0
        self._max_view_end: int = total_bars
        self._clamp_view()

    def set_total_bars(self, count: int) -> None:
        """更新总K线数量并重新约束视窗"""
        self.total_bars = max(count, 1)
        if self.focus_index >= self.total_bars:
            self.focus_index = self.total_bars - 1
        self.view_start = max(0, self.focus_index + 1 - self.visible_count)
        self._max_view_end = self.focus_index + 1
        self._clamp_view()

    def set_focus_by_index(self, index: int) -> None:
        """设置焦点索引，视窗自动跟随
        
        初始时焦点日在视窗末尾（显示前50根）。
        右移超出视窗时自动扩展；左移超出时自动收缩。
        """
        self.focus_index = max(0, min(index, self.total_bars - 1))
        self._max_view_end = self.focus_index + 1
        self._follow_focus()

    def set_focus_without_move(self, index: int) -> None:
        """设置焦点索引但不移动视窗（仅更新十字光标位置）
        
        用于鼠标单击、键盘左移等场景：只切换十字光标，
        不改变可视区间位置，不重置右边界限制。
        如果焦点超出当前可视范围，则视窗跟随到焦点可见。
        """
        self.focus_index = max(0, min(index, self.total_bars - 1))
        start, end = self.get_visible_range()
        if start <= self.focus_index < end:
            return
        if self.focus_index >= end:
            self._max_view_end = self.focus_index + 1
            self.view_start = max(
                0, self.focus_index + 1 - self.visible_count)
        elif self.focus_index < start:
            self.view_start = self.focus_index

    def set_focus_by_date(self, date_val: int, dates: List[int]) -> bool:
        """根据日期值定位焦点，返回是否成功找到"""
        try:
            idx = dates.index(date_val)
            self.set_focus_by_index(idx)
            return True
        except ValueError:
            idx = self._find_nearest_date_idx(date_val, dates)
            if idx >= 0:
                self.set_focus_by_index(idx)
                return True
            return False

    @staticmethod
    def _find_nearest_date_idx(target: int, dates: List[int]) -> int:
        """查找最接近目标日期的索引"""
        if not dates:
            return -1
        distances = [abs(d - target) for d in dates]
        return distances.index(min(distances))

    def zoom_in(self, factor: float = 0.8) -> None:
        """放大（减少可见K线数）"""
        self.visible_count = max(MIN_VISIBLE_BARS,
                                 int(self.visible_count * factor))
        self._follow_focus()

    def zoom_out(self, factor: float = 1.25) -> None:
        """缩小（增加可见K线数）"""
        self.visible_count = min(MAX_VISIBLE_BARS,
                                 int(self.visible_count * factor))
        self._follow_focus()

    def pan_left(self, bars: int = 10) -> None:
        """向左平移"""
        self.view_start = max(0, self.view_start - bars)
        self.focus_index = min(self.focus_index,
                               self.view_start + self.visible_count - 1)
        self._follow_focus()

    def pan_right(self, bars: int = 10) -> None:
        """向右平移"""
        new_start = self.view_start + bars
        max_start = max(0, self.total_bars - self.visible_count)
        self.view_start = min(new_start, max_start)
        self.focus_index = max(self.focus_index, self.view_start)
        self._follow_focus()

    def move_focus_prev(self) -> int:
        """焦点前移一根，返回新索引"""
        if self.focus_index > 0:
            self.focus_index -= 1
            self._follow_focus()
        return self.focus_index

    def move_focus_next(self) -> int:
        """焦点后移一根，返回新索引"""
        if self.focus_index < self.total_bars - 1:
            self.focus_index += 1
            self._follow_focus()
        return self.focus_index

    def get_visible_range(self) -> Tuple[int, int]:
        """返回可视区间 (start_idx, end_idx)
        
        基于view_start和visible_count计算，右边界不超过_max_view_end。
        默认_max_view_end=focus_index+1，即不显示焦点日之后的日期。
        """
        end = min(self.total_bars, self.view_start + self.visible_count,
                  self._max_view_end)
        start = max(0, end - self.visible_count)
        if end - start < self.visible_count:
            end = min(self.total_bars, start + self.visible_count,
                      self._max_view_end)
        return start, end

    def reset(self) -> None:
        """重置为默认视图：焦点日在末尾，不显示焦点日之后"""
        self.visible_count = DEFAULT_VISIBLE_BARS
        self._max_view_end = self.focus_index + 1
        self.view_start = max(0, self.focus_index + 1 - self.visible_count)
        self._follow_focus()

    def _follow_focus(self) -> None:
        """视窗跟随焦点：确保焦点在可视范围内
        
        初始加载：焦点日在视窗末尾（显示前50根），不显示焦点日之后的日期。
        右移超出：扩展_max_view_end，视窗跟随右移，显示焦点日之后的日期。
        左移超出：视窗跟随左移。
        """
        self._clamp_view()
        start, end = self.get_visible_range()
        if self.focus_index >= end:
            self._max_view_end = self.focus_index + 1
            self.view_start = max(
                0, self.focus_index + 1 - self.visible_count)
        elif self.focus_index < start:
            self.view_start = self.focus_index

    def _clamp_view(self) -> None:
        """确保视窗参数在合法范围内"""
        self.visible_count = max(MIN_VISIBLE_BARS,
                                min(MAX_VISIBLE_BARS, self.visible_count))
        self.focus_index = max(
            0, min(self.focus_index, self.total_bars - 1))


# ==================== 表现层 ====================

class PopupWidget(QWidget):
    """K线数据悬浮弹窗"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool |
                            Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(170, 180)
        self._data: Optional[Dict] = None
        self._drag_pos: Optional[QPoint] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化弹窗UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet(
            f"color:{COLOR_TEXT_PRIMARY};font-weight:bold;font-size:12px;"
            f"padding-bottom:4px;")

        price_layout = QHBoxLayout()
        price_layout.setSpacing(8)

        left_col = QVBoxLayout()
        left_col.setSpacing(1)
        self.lbl_open = QLabel()
        self.lbl_high = QLabel()
        self.lbl_low = QLabel()
        for lbl in [self.lbl_open, self.lbl_high, self.lbl_low]:
            lbl.setStyleSheet(f"color:{COLOR_TEXT_MUTED};font-size:10px;")
            left_col.addWidget(lbl)

        right_col = QVBoxLayout()
        right_col.setSpacing(1)
        self.lbl_close = QLabel()
        self.lbl_change = QLabel()
        self.lbl_change_pct = QLabel()
        for lbl in [self.lbl_close, self.lbl_change, self.lbl_change_pct]:
            lbl.setStyleSheet(f"font-size:10px;font-weight:bold;")
            right_col.addWidget(lbl)

        price_layout.addLayout(left_col)
        price_layout.addLayout(right_col)

        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(
            f"background-color:{COLOR_BG_TERTIARY};margin:4px 0;")

        self.lbl_vol = QLabel()
        self.lbl_amt = QLabel()
        self.lbl_focus_ratio = QLabel()
        for lbl in [self.lbl_vol, self.lbl_amt]:
            lbl.setStyleSheet(f"color:{COLOR_TEXT_MUTED};font-size:10px;")
        self.lbl_focus_ratio.setStyleSheet(
            f"color:{COLOR_TEXT_SECONDARY};font-size:10px;font-weight:bold;")

        layout.addWidget(self.lbl_title)
        layout.addLayout(price_layout)
        layout.addWidget(sep)
        layout.addWidget(self.lbl_vol)
        layout.addWidget(self.lbl_amt)
        layout.addWidget(self.lbl_focus_ratio)

        self.setStyleSheet(
            f"background-color:{COLOR_POPUP_BG};"
            f"border-radius:6px;"
            f"border:1px solid {COLOR_BG_TERTIARY};")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(4, 4)
        self.setGraphicsEffect(shadow)

    def show_data(self, x: int, y: int,
                  data: Dict[str, Any]) -> None:
        """显示K线数据弹窗"""
        self._data = data
        date_str = str(data.get('date', ''))
        o = data.get('open', 0)
        h = data.get('high', 0)
        l = data.get('low', 0)
        c = data.get('close', 0)
        v = data.get('volume', 0)
        amt = data.get('amount', 0)

        up_color = COLOR_RED_UP
        dn_color = COLOR_GREEN_DOWN

        self.lbl_title.setText(date_str)

        self.lbl_open.setText(f"{TXT_OPEN} {o:.2f}")
        self.lbl_high.setText(f"{TXT_HIGH} {h:.2f}")
        self.lbl_low.setText(f"{TXT_LOW} {l:.2f}")

        self.lbl_close.setText(f"{TXT_CLOSE} {c:.2f}")
        self.lbl_close.setStyleSheet(
            f"color:{up_color if c >= o else dn_color};")
        change_val = c - o
        self.lbl_change.setText(
            f"{'+' if change_val >= 0 else ''}{change_val:.2f}")
        self.lbl_change.setStyleSheet(
            f"color:{up_color if c >= o else dn_color};")
        if o > 0:
            change_pct = (c - o) / o * 100
            self.lbl_change_pct.setText(
                f"{'+' if change_pct >= 0 else ''}{change_pct:.2f}%")
        else:
            self.lbl_change_pct.setText("--")
        self.lbl_change_pct.setStyleSheet(
            f"color:{up_color if c >= o else dn_color};")

        self.lbl_vol.setText(f"Vol {v:,}")
        self.lbl_amt.setText(
            f"{TXT_AMOUNT} {amt/100000000:.2f}{TXT_BILLION}")

        # 焦点日期 vs 关注日期涨跌比
        attention_close = data.get('attention_close', 0)
        focus_date_val = data.get('focus_date', 0)
        attention_date_val = data.get('attention_date', 0)
        if attention_close > 0 and focus_date_val != attention_date_val:
            ratio_vs_att = (c - attention_close) / attention_close * 100
            self.lbl_focus_ratio.setText(
                f"{TXT_VS_ATTENTION} "
                f"{'+' if ratio_vs_att >= 0 else ''}{ratio_vs_att:.2f}%")
            self.lbl_focus_ratio.setStyleSheet(
                f"color:{COLOR_RED_UP if ratio_vs_att >= 0 else COLOR_GREEN_DOWN};"
                f"font-size:10px;font-weight:bold;")
        else:
            self.lbl_focus_ratio.setText("")
            self.lbl_focus_ratio.setStyleSheet(
                f"color:{COLOR_TEXT_SECONDARY};"
                f"font-size:10px;font-weight:bold;")

        # 定位弹窗：x, y 是相对于父窗口的坐标
        parent = self.parentWidget()
        if parent:
            global_pos = parent.mapToGlobal(QPoint(x, y))
            px = global_pos.x()
            py = global_pos.y()
        else:
            px, py = x, y

        # 确保不超出屏幕边界
        screen = QApplication.primaryScreen().geometry()
        if px + 180 > screen.width():
            px = max(0, px - 180)
        if py + 155 > screen.height():
            py = max(0, py - 155)
        if px < 0:
            px = 0
        if py < 0:
            py = 0

        self.move(px, py)
        self.show()
        self.repaint()

    def hide_popup(self) -> None:
        """隐藏弹窗"""
        self.hide()
        self._data = None

    def mousePressEvent(self, event) -> None:
        """开始拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """拖动弹窗"""
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event) -> None:
        """结束拖动"""
        self._drag_pos = None
        event.accept()


class KlineCanvas(FigureCanvas):
    """K线图画布组件，嵌入matplotlib图表到PyQt6"""

    bar_clicked = pyqtSignal(int)
    bar_double_clicked = pyqtSignal(int)
    focus_changed = pyqtSignal(int)
    zoom_changed = pyqtSignal(str)
    export_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        self.fig = Figure(figsize=(12, 6),
                          dpi=100,
                          facecolor=COLOR_BG_PRIMARY)
        self.ax_main = self.fig.add_axes([0.08, 0.47, 0.88, 0.40])
        self.ax_vol = self.fig.add_axes([0.08, 0.28, 0.88, 0.14])
        self.ax_macd = self.fig.add_axes([0.08, 0.08, 0.88, 0.16])

        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(CHART_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.df_indicator: Optional[pd.DataFrame] = None
        self.viewport = ViewportController()
        self.focus_date_val: int = 0
        self.attention_date_val: int = 0
        self._symbol_display: str = ''
        self._list_panel_width: int = LIST_PANEL_FIXED_WIDTH
        self._tpsl_text: str = ''
        self._tpsl_html: str = ''

        self.selected_index: Optional[int] = None
        self.crosshair_visible = False
        self.popup = PopupWidget(self)

        self.ch_h_line: Optional[Line2D] = None
        self.ch_v_line: Optional[Line2D] = None

        self.mpl_connect('button_press_event', self._on_mouse_press)
        self.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.fig.canvas.mpl_connect('scroll_event', self._on_scroll)

        self._apply_style()

    def _apply_style(self) -> None:
        """应用金融终端深色主题样式"""
        for ax in [self.ax_main, self.ax_vol, self.ax_macd]:
            ax.set_facecolor(COLOR_BG_PRIMARY)
            ax.tick_params(colors=COLOR_TEXT_MUTED, labelsize=8)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            for spine in ['bottom', 'left']:
                ax.spines[spine].set_color(COLOR_BG_TERTIARY)
        self.fig.patch.set_facecolor(COLOR_BG_PRIMARY)

    def load_and_draw(self, df: pd.DataFrame,
                      focus_date: int,
                      symbol: str = '',
                      tp_ratio: float = DEFAULT_TP_RATIO,
                      sl_ratio: float = DEFAULT_SL_RATIO,
                      agent: Optional[TdxDataAgent] = None,
                      tpsl_days: int = DEFAULT_TPSL_DAYS) -> Optional[int]:
        """加载带指标的DataFrame并绘制K线图，返回焦点索引"""
        self.df_indicator = df
        self.focus_date_val = focus_date
        self.attention_date_val = focus_date
        self._symbol_display = symbol
        dates = df['r_date'].tolist()

        self.viewport.set_total_bars(len(dates))
        found = self.viewport.set_focus_by_date(focus_date, dates)
        if not found and len(dates) > 0:
            self.viewport.set_focus_by_index(len(dates) // 2)

        self._calc_tpsl(
            df, focus_date, tp_ratio, sl_ratio, agent, tpsl_days)

        self.selected_index = None
        self._draw_chart()
        return self.viewport.focus_index

    def redraw_with_new_focus(self, focus_date: int) -> None:
        """切换焦点日时重绘（复用已有数据），不重算止盈止损"""
        if self.df_indicator is None or self.df_indicator.empty:
            return
        self.focus_date_val = focus_date
        dates = self.df_indicator['r_date'].tolist()
        self.viewport.set_focus_by_date(focus_date, dates)
        self.selected_index = None
        self._draw_chart()

    def _calc_tpsl(self, df: pd.DataFrame, focus_date: int,
                   tp_ratio: float, sl_ratio: float,
                   agent: Optional[TdxDataAgent] = None,
                   tpsl_days: int = DEFAULT_TPSL_DAYS) -> None:
        """计算止盈止损信息并生成显示文本"""
        self._tpsl_text = ''
        self._tpsl_html = ''
        if df is None or df.empty or focus_date <= 0:
            return
        if agent is None:
            return

        try:
            focus_rows = df[df['r_date'] == focus_date]
            if focus_rows.empty:
                return
            base_price = float(focus_rows['r_close'].values[0])

            tp_price = base_price * (1 + tp_ratio)
            sl_price = base_price * (1 + sl_ratio)

            focus_pos = df.index.get_loc(focus_rows.index[0])
            next_pos = focus_pos + 1
            if next_pos >= len(df):
                return

            start_date = int(df.iloc[next_pos]['r_date'])
            end_pos = min(next_pos + tpsl_days, len(df) - 1)
            end_date = int(df.iloc[end_pos]['r_date'])

            result = agent.get_takeprofit_stoploss_value(
                df, start_date, end_date, tp_price, sl_price)

            if result is None:
                return

            tp_days, sl_days, tp_first, sl_first, row_no, arrival_day = result

            display_day = row_no + 1
            tp_label = TXT_FIRST_TP if tp_first == 1 else ''
            sl_label = TXT_FIRST_SL if sl_first == -1 else ''
            first_label = tp_label or sl_label or TXT_NOT_TRIGGERED

            self._tpsl_text = (
                f"  |  {TXT_TAKE_PROFIT}>{tp_days}{TXT_DAY} "
                f"{TXT_STOP_LOSS}>{sl_days}{TXT_DAY}  "
                f"{first_label} {TXT_DAY_PREFIX}{display_day}{TXT_DAY}"
                f"({arrival_day})")

            if tp_first == 1:
                first_html = (
                    f"<b style='color:{COLOR_RED_UP}'>"
                    f"{TXT_FIRST_TP}</b>")
            elif sl_first == -1:
                first_html = (
                    f"<b style='color:#60A5FA'>"
                    f"{TXT_FIRST_SL}</b>")
            else:
                first_html = TXT_NOT_TRIGGERED

            self._tpsl_html = (
                f"  |  {TXT_TAKE_PROFIT}&gt;{tp_days}{TXT_DAY} "
                f"{TXT_STOP_LOSS}&gt;{sl_days}{TXT_DAY}  "
                f"{first_html} "
                f"{TXT_DAY_PREFIX}{display_day}{TXT_DAY}"
                f"({arrival_day})")
        except Exception as e:
            Logger.log().warning(f"{TXT_TPSL_CALC_FAILED}: {e}")

    def _adjust_axes_layout(self) -> None:
        """根据画布实际宽度动态调整axes左边距，使主图与左侧列表对齐"""
        canvas_w = self.width()
        if canvas_w <= 0:
            return
        total_w = canvas_w + self._list_panel_width
        left_frac = self._list_panel_width / total_w
        axis_label_frac = 40 / canvas_w
        left_frac = left_frac - axis_label_frac
        left_frac = max(0.05, min(0.20, left_frac))
        right_frac = 0.96
        width_frac = right_frac - left_frac
        self.ax_main.set_position([left_frac, 0.47, width_frac, 0.40])
        self.ax_vol.set_position([left_frac, 0.28, width_frac, 0.14])
        self.ax_macd.set_position([left_frac, 0.08, width_frac, 0.16])

    def _draw_chart(self) -> None:
        """核心绘制方法：执行全量绘制"""
        if self.df_indicator is None or self.df_indicator.empty:
            self._clear_axes()
            return

        self._adjust_axes_layout()

        df = self.df_indicator
        start_idx, end_idx = self.viewport.get_visible_range()
        view_df = df.iloc[start_idx:end_idx].copy()
        n = len(view_df)
        if n == 0:
            self._clear_axes()
            return

        self._clear_axes()
        ax_m = self.ax_main
        ax_vol = self.ax_vol
        ax_macd = self.ax_macd

        self._draw_candles(ax_m, view_df, n, start_idx)

        ma_colors = {5: COLOR_MA5, 10: COLOR_MA10,
                     20: COLOR_MA20, 60: COLOR_MA60}
        for period, color in ma_colors.items():
            col_name = f'MA{period}'
            if col_name in view_df.columns:
                valid_mask = view_df[col_name].notna()
                if valid_mask.any():
                    ax_m.plot(np.arange(n)[valid_mask],
                              view_df.loc[valid_mask, col_name],
                              color=color, linewidth=1.0,
                              label=f'MA{period}', alpha=0.85)

        self._draw_volume(ax_vol, view_df, n)
        self._draw_macd(ax_macd, view_df, n)

        ax_m.set_xlim(-0.5, n - 0.5)
        ax_vol.set_xlim(-0.5, n - 0.5)
        ax_macd.set_xlim(-0.5, n - 0.5)

        step = max(1, n // 8)
        tick_pos = list(range(0, n, step))
        tick_labels = [str(view_df.iloc[i]['r_date'])
                      if i < len(view_df) else '' for i in tick_pos]
        ax_m.set_xticks(tick_pos)
        ax_m.set_xticklabels(tick_labels, rotation=25,
                            fontsize=7, color=COLOR_TEXT_MUTED)
        ax_vol.set_xticks([])
        ax_vol.set_xticklabels([])
        ax_macd.set_xticks([])
        ax_macd.set_xticklabels([])

        ax_m.legend(loc='upper left', fontsize=7,
                    facecolor=COLOR_BG_SECONDARY,
                    edgecolor=COLOR_BG_TERTIARY,
                    labelcolor=COLOR_TEXT_SECONDARY)
        ax_m.set_ylabel(TXT_PRICE, fontsize=9, color=COLOR_TEXT_SECONDARY)
        ax_vol.set_ylabel(TXT_VOLUME, fontsize=8, color=COLOR_TEXT_SECONDARY)
        ax_vol.tick_params(labelsize=7)
        ax_macd.set_ylabel('MACD', fontsize=9, color=COLOR_TEXT_SECONDARY)
        ax_macd.axhline(y=0, color=COLOR_BG_TERTIARY,
                        linestyle='-', linewidth=0.6)

        # 关注日期虚线框
        if self.attention_date_val > 0:
            att_rows = df[df['r_date'] == self.attention_date_val]
            if not att_rows.empty:
                att_abs_idx = df.index.get_loc(att_rows.index[0])
                att_rel_idx = att_abs_idx - start_idx
                if 0 <= att_rel_idx < n:
                    for ax in [ax_m, ax_vol, ax_macd]:
                        y_lo, y_hi = ax.get_ylim()
                        for x_pos in [att_rel_idx - 0.4,
                                      att_rel_idx + 0.4]:
                            ax.plot([x_pos, x_pos], [y_lo, y_hi],
                                    linestyle='--', color=COLOR_TEXT_MUTED,
                                    linewidth=0.8, alpha=0.6)
                        ax.plot([att_rel_idx - 0.4, att_rel_idx + 0.4],
                                [y_hi, y_hi], linestyle='--',
                                color=COLOR_TEXT_MUTED, linewidth=0.8,
                                alpha=0.6)
                        ax.plot([att_rel_idx - 0.4, att_rel_idx + 0.4],
                                [y_lo, y_lo], linestyle='--',
                                color=COLOR_TEXT_MUTED, linewidth=0.8,
                                alpha=0.6)

        if self.selected_index is not None and self.crosshair_visible:
            rel_idx = self.selected_index - start_idx
            if 0 <= rel_idx < n:
                self._draw_crosshair(ax_m, view_df, rel_idx)

        self.draw()

    def _draw_candles(self, ax, view_df: pd.DataFrame,
                      n: int, start_idx: int = 0) -> None:
        """绘制OHLC蜡烛图"""
        for i in range(n):
            row = view_df.iloc[i]
            o, h, l, c = row['r_open'], row['r_high'], row['r_low'], row['r_close']

            if pd.isna(o) or pd.isna(c):
                continue

            color = COLOR_RED_UP if c >= o else COLOR_GREEN_DOWN

            body_width = max(0.5, n * 0.006)
            body_bottom = min(o, c)
            body_height = abs(c - o) if abs(c - o) > 0.001 else 0.08
            rect = mpatches.Rectangle(
                (i - body_width / 2, body_bottom),
                body_width, body_height,
                facecolor=color, edgecolor=color,
                linewidth=0.5, alpha=0.9)
            ax.add_patch(rect)

            ax.plot([i, i], [l, h], color=color,
                    linewidth=0.7, alpha=0.85)

        # 阶段最高/最低价标注
        valid_high = view_df['r_high'].dropna()
        valid_low = view_df['r_low'].dropna()
        if not valid_high.empty:
            max_price = valid_high.max()
            max_rel_idx = valid_high.idxmax() - start_idx
            if 0 <= max_rel_idx < n:
                ax.annotate(
                    f'{max_price:.2f}',
                    xy=(max_rel_idx, max_price),
                    xytext=(0, 5), textcoords='offset points',
                    color=COLOR_RED_UP, fontsize=7, fontweight='bold',
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.2',
                              facecolor=COLOR_BG_SECONDARY,
                              edgecolor=COLOR_RED_UP, alpha=0.8))
        if not valid_low.empty:
            min_price = valid_low.min()
            min_rel_idx = valid_low.idxmin() - start_idx
            if 0 <= min_rel_idx < n:
                ax.annotate(
                    f'{min_price:.2f}',
                    xy=(min_rel_idx, min_price),
                    xytext=(0, -5), textcoords='offset points',
                    color=COLOR_GREEN_DOWN, fontsize=7, fontweight='bold',
                    ha='center', va='top',
                    bbox=dict(boxstyle='round,pad=0.2',
                              facecolor=COLOR_BG_SECONDARY,
                              edgecolor=COLOR_GREEN_DOWN, alpha=0.8))

    def _draw_volume(self, ax, view_df: pd.DataFrame, n: int) -> None:
        """绘制成交量柱状图"""
        if 'volume' not in view_df.columns:
            return

        colors_vol = []
        for i in range(n):
            if i >= len(view_df):
                break
            row = view_df.iloc[i]
            o = row.get('r_open', 0)
            c = row.get('r_close', 0)
            if pd.isna(o) or pd.isna(c):
                colors_vol.append('none')
            elif c >= o:
                colors_vol.append(COLOR_RED_UP)
            else:
                colors_vol.append(COLOR_GREEN_DOWN)

        bar_width = max(0.5, n * 0.006)
        volumes = view_df['volume'].fillna(0)
        ax.bar(np.arange(n), volumes, width=bar_width,
               color=colors_vol, alpha=0.75, edgecolor='none')

    def _draw_macd(self, ax, view_df: pd.DataFrame, n: int) -> None:
        """绘制MACD附图"""
        if 'MACD' in view_df.columns:
            colors_macd = []
            for val in view_df['MACD']:
                if pd.isna(val):
                    colors_macd.append('none')
                elif val >= 0:
                    colors_macd.append(COLOR_RED_UP)
                else:
                    colors_macd.append(COLOR_GREEN_DOWN)

            bar_width = max(0.3, n * 0.015)
            valid_mask = view_df['MACD'].notna()
            ax.bar(np.arange(n)[valid_mask],
                   view_df.loc[valid_mask, 'MACD'],
                   width=bar_width, color=[colors_macd[i] for i in range(n)
                                           if valid_mask.iloc[i]],
                   alpha=0.75, edgecolor='none', linewidth=0)

        if 'DIF' in view_df.columns:
            valid_dif = view_df['DIF'].notna()
            if valid_dif.any():
                ax.plot(np.arange(n)[valid_dif],
                        view_df.loc[valid_dif, 'DIF'],
                        color=COLOR_MACD_DIF, linewidth=1.0,
                        label='DIF', alpha=0.85)

        if 'DEA' in view_df.columns:
            valid_dea = view_df['DEA'].notna()
            if valid_dea.any():
                ax.plot(np.arange(n)[valid_dea],
                        view_df.loc[valid_dea, 'DEA'],
                        color=COLOR_MACD_DEA, linewidth=1.0,
                        label='DEA', alpha=0.85)

        ax.legend(loc='upper left', fontsize=7,
                  facecolor=COLOR_BG_SECONDARY,
                  edgecolor=COLOR_BG_TERTIARY,
                  labelcolor=COLOR_TEXT_SECONDARY)

    def _draw_crosshair(self, ax, view_df: pd.DataFrame,
                        rel_idx: int) -> None:
        """在指定位置绘制十字光标"""
        row = view_df.iloc[rel_idx]
        c = row['r_close'] if not pd.isna(row['r_close']) else 0

        self._remove_crosshair()

        self.ch_h_line = ax.axhline(
            y=c, color=COLOR_CROSSHAIR_H,
            linestyle='--', linewidth=0.8, alpha=0.75)
        self.ch_v_line = ax.axvline(
            x=rel_idx, color=COLOR_CROSSHAIR_V,
            linestyle='--', linewidth=0.8, alpha=0.75)

    def _remove_crosshair(self) -> None:
        """移除十字光标元素"""
        for artist in [self.ch_h_line, self.ch_v_line]:
            if artist is not None:
                try:
                    artist.remove()
                except Exception:
                    pass
        self.ch_h_line = None
        self.ch_v_line = None

    def _clear_axes(self) -> None:
        """清除所有坐标轴内容"""
        self.ax_main.clear()
        self.ax_vol.clear()
        self.ax_macd.clear()
        self._remove_crosshair()
        self._apply_style()

    def _on_mouse_press(self, event) -> None:
        """鼠标按键事件处理"""
        if event.xdata is None:
            return
        if event.inaxes not in [self.ax_main, self.ax_vol]:
            return

        click_idx = int(round(event.xdata))
        start_idx, end_idx = self.viewport.get_visible_range()
        abs_idx = start_idx + click_idx

        if abs_idx < 0 or abs_idx >= self.viewport.total_bars:
            return

        if event.dblclick:
            self.bar_double_clicked.emit(abs_idx)
        else:
            self.bar_clicked.emit(abs_idx)

    def _on_mouse_move(self, event) -> None:
        """鼠标移动事件"""
        pass

    def _on_scroll(self, event) -> None:
        """鼠标滚轮缩放"""
        if event.inaxes is None:
            return
        if event.button == 'up':
            self.zoom_in()
        elif event.button == 'down':
            self.zoom_out()

    def select_bar(self, index: int, show_crosshair: bool = True,
                   show_popup: bool = False,
                   avoid_occlude: bool = False,
                   allow_view_move: bool = False) -> None:
        """选中某根K线：显示十字光标，Popup可选
        
        Args:
            index: K线索引
            show_crosshair: 是否显示十字光标
            show_popup: 是否显示Popup
            avoid_occlude: 是否避免Popup遮挡K线
            allow_view_move: 是否允许视窗跟随移动
        """
        start_idx, end_idx = self.viewport.get_visible_range()
        if index < 0 or index >= self.viewport.total_bars:
            return

        self.selected_index = index
        self.crosshair_visible = show_crosshair

        if allow_view_move:
            self.viewport.set_focus_by_index(index)
        else:
            self.viewport.set_focus_without_move(index)

        if show_popup and show_crosshair and self.df_indicator is not None:
            if 0 <= index < len(self.df_indicator):
                row = self.df_indicator.iloc[index]
                popup_data = {
                    'date': int(row['r_date'])
                        if pd.notna(row.get('r_date')) else 0,
                    'open': row['r_open'],
                    'high': row['r_high'],
                    'low': row['r_low'],
                    'close': row['r_close'],
                    'volume': row.get('volume', 0),
                    'amount': row.get('amount', 0),
                    'focus_date': int(row['r_date'])
                        if pd.notna(row.get('r_date')) else 0,
                    'attention_date': self.attention_date_val,
                    'attention_close': self._get_attention_close(),
                }
                start_idx, end_idx = self.viewport.get_visible_range()
                rel_idx = index - start_idx
                visible_count = end_idx - start_idx

                canvas_rect = self.geometry()
                chart_left_offset = 20
                popup_bottom_offset = 160

                if avoid_occlude:
                    if rel_idx < visible_count * 0.4:
                        px = chart_left_offset + int(
                            canvas_rect.width() * 0.55)
                    elif rel_idx > visible_count * 0.6:
                        px = chart_left_offset
                    else:
                        px = chart_left_offset + int(
                            canvas_rect.width() * 0.55)
                else:
                    if rel_idx > visible_count * 0.6:
                        px = chart_left_offset
                    else:
                        px = chart_left_offset + int(
                            canvas_rect.width() * 0.5)
                py = canvas_rect.height() - popup_bottom_offset
                self.popup.show_data(px, py, popup_data)

        self._draw_chart()

    def clear_selection(self) -> None:
        """清除选中和光标"""
        self.selected_index = None
        self.crosshair_visible = False
        self.popup.hide_popup()
        self._draw_chart()

    def zoom_in(self) -> None:
        """放大"""
        self.viewport.zoom_in()
        self.zoom_changed.emit('in')
        self._draw_chart()

    def zoom_out(self) -> None:
        """缩小"""
        self.viewport.zoom_out()
        self.zoom_changed.emit('out')
        self._draw_chart()

    def reset_view(self) -> None:
        """重置视图"""
        self.viewport.reset()
        self.zoom_changed.emit('reset')
        self._draw_chart()

    def pan_left(self) -> None:
        """向左平移"""
        self.viewport.pan_left()
        self._draw_chart()

    def pan_right(self) -> None:
        """向右平移"""
        self.viewport.pan_right()
        self._draw_chart()

    def _is_trading_day(self, index: int) -> bool:
        """判断指定索引是否为交易日（有数据，非停牌）"""
        if self.df_indicator is None:
            return True
        if index < 0 or index >= len(self.df_indicator):
            return False
        row = self.df_indicator.iloc[index]
        vol = row.get('volume', 0)
        open_p = row.get('r_open', None)
        close_p = row.get('r_close', None)
        if pd.isna(vol) or vol == 0:
            return False
        if pd.isna(open_p) or pd.isna(close_p) or open_p == 0 or close_p == 0:
            return False
        return True

    def _get_attention_close(self) -> float:
        """获取关注日期的收盘价"""
        if self.df_indicator is None or self.attention_date_val <= 0:
            return 0.0
        rows = self.df_indicator[
            self.df_indicator['r_date'] == self.attention_date_val]
        if rows.empty:
            return 0.0
        return float(rows['r_close'].values[0])

    def move_focus_prev(self) -> Optional[int]:
        """焦点前移到上一个交易日（跳过停牌），显示Popup"""
        if self.df_indicator is None or self.viewport.total_bars == 0:
            return None

        current_idx = self.viewport.focus_index
        new_idx = current_idx - 1

        while new_idx >= 0 and not self._is_trading_day(new_idx):
            new_idx -= 1

        if new_idx < 0:
            new_idx = 0

        self.select_bar(new_idx, show_popup=True, avoid_occlude=True)
        self.focus_changed.emit(new_idx)
        return new_idx

    def move_focus_next(self) -> Optional[int]:
        """焦点后移到下一个交易日（跳过停牌），显示Popup"""
        if self.df_indicator is None or self.viewport.total_bars == 0:
            return None

        current_idx = self.viewport.focus_index
        new_idx = current_idx + 1

        while new_idx < self.viewport.total_bars and not self._is_trading_day(new_idx):
            new_idx += 1

        if new_idx >= self.viewport.total_bars:
            new_idx = self.viewport.total_bars - 1

        self.select_bar(new_idx, show_popup=True, avoid_occlude=True)
        self.focus_changed.emit(new_idx)
        return new_idx

    def export_png(self, save_path: str) -> None:
        """导出图表为PNG文件"""
        try:
            self.fig.savefig(save_path, dpi=150,
                            facecolor=COLOR_BG_PRIMARY,
                            edgecolor='none',
                            bbox_inches='tight')
            Logger.log().info(f"{TXT_CHART_EXPORTED}: {save_path}")
            QMessageBox.information(
                self, TXT_EXPORT_SUCCESS,
                f'{TXT_IMAGE_SAVED}:\n{save_path}')
        except Exception as e:
            Logger.log().error(f"{TXT_EXPORT_FAILED}: {e}")
            QMessageBox.warning(self, TXT_EXPORT_FAILED,
                                f'{TXT_SAVE_FAILED}:\n{e}')

    def keyPressEvent(self, event) -> None:
        """处理键盘事件"""
        from PyQt6.QtCore import Qt
        key = event.key()

        if key == Qt.Key.Key_Left:
            self.move_focus_prev()
            event.accept()
            return
        elif key == Qt.Key.Key_Right:
            self.move_focus_next()
            event.accept()
            return
        elif key == Qt.Key.Key_Escape:
            self.clear_selection()
            event.accept()
            return

        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        """右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{COLOR_BG_SECONDARY};"
            f"border:1px solid {COLOR_BG_TERTIARY};"
            f"padding:4px;}}"
            f"QMenu::item{{padding:6px 24px;color:{COLOR_TEXT_SECONDARY};}}"
            f"QMenu::item:hover{{background:{COLOR_SELECTION};"
            f"color:{COLOR_TEXT_PRIMARY};}}")

        act_zoom_in = menu.addAction(TXT_ZOOM_IN_MENU)
        act_zoom_out = menu.addAction(TXT_ZOOM_OUT_MENU)
        menu.addSeparator()
        act_reset = menu.addAction(TXT_RESET_VIEW_MENU)
        menu.addSeparator()
        act_export = menu.addAction(TXT_EXPORT_PNG_MENU)

        action = menu.exec(event.globalPos())
        if action == act_zoom_in:
            self.zoom_in()
        elif action == act_zoom_out:
            self.zoom_out()
        elif action == act_reset:
            self.reset_view()
        elif action == act_export:
            self.export_requested.emit()


class ListPanel(QWidget):
    """左侧列表面板组件"""

    row_selected = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(LIST_PANEL_FIXED_WIDTH)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化列表UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(LIST_HEADER_LABELS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        self.table.setColumnWidth(LIST_COL_DATETIME, 80)
        self.table.setColumnWidth(LIST_COL_SYMBOL, 55)

        self._apply_dark_style()

        self.table.currentCellChanged.connect(self._on_row_changed)

        layout.addWidget(self.table)

    def _apply_dark_style(self) -> None:
        """应用深色主题表格样式"""
        self.table.setStyleSheet(
            f"QTableWidget{{"
            f"background-color:{COLOR_BG_PRIMARY};"
            f"alternate-background-color:{COLOR_BG_SECONDARY};"
            f"color:{COLOR_TEXT_SECONDARY};"
            f"outline-color:{COLOR_BG_TERTIARY};"
            f"border:none;"
            f"font-size:11px;}}"
            f"QTableWidget::item:selected{{"
            f"background-color:{COLOR_SELECTION};"
            f"color:{COLOR_TEXT_PRIMARY};}}"
            f"QTableWidget::item:hover{{"
            f"background-color:{COLOR_BG_TERTIARY};}}"
            f"QHeaderView::section{{"
            f"background-color:{COLOR_BG_SECONDARY};"
            f"color:{COLOR_TEXT_PRIMARY};"
            f"padding:4px;border:none;"
            f"border-bottom:2px solid {COLOR_SELECTION};"
            f"font-weight:bold;font-size:11px;}}")

    def load_data(self, data: List[List]) -> None:
        """加载数据到列表"""
        self.table.setRowCount(len(data))
        for row_idx, row_data in enumerate(data):
            dt_str, symbol = row_data[0], row_data[1]
            fd = row_data[2] if len(row_data) > 2 else 0

            dt_item = QTableWidgetItem(str(dt_str)[:19])
            dt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, LIST_COL_DATETIME, dt_item)

            sym_str = str(symbol).zfill(6) if symbol else ''
            sym_item = QTableWidgetItem(sym_str)
            sym_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, LIST_COL_SYMBOL, sym_item)

            fd_display = str(int(fd)) if fd and int(fd) > 0 else '-'
            fd_item = QTableWidgetItem(fd_display)
            fd_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, LIST_COL_FOCUS_DATE, fd_item)

        Logger.log().info(f"{TXT_LIST_LOADED}: {len(data)}")

    def select_row(self, row: int) -> None:
        """程序化选中某行"""
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)
            self.table.scrollToItem(
                self.table.item(row, 0),
                QTableWidget.ScrollHint.EnsureVisible)

    def current_row(self) -> int:
        """获取当前选中行号（无选中返回-1）"""
        return self.table.currentRow()

    def total_rows(self) -> int:
        """返回总行数"""
        return self.table.rowCount()

    def row_data(self, row: int) -> Tuple[str, str, int]:
        """获取指定行数据"""
        dt = self.table.item(row, LIST_COL_DATETIME).text()
        sym = self.table.item(row, LIST_COL_SYMBOL).text()
        fd_raw = self.table.item(row, LIST_COL_FOCUS_DATE).text()
        fd = int(fd_raw) if fd_raw.isdigit() else 0
        return dt, sym, fd

    def _on_row_changed(self, current_row: int,
                        current_col: int,
                        prev_row: int, prev_col: int) -> None:
        """行选择变更回调"""
        if current_row >= 0:
            self.row_selected.emit(current_row)


class MainWindow(QMainWindow):
    """主窗口：整合列表面板与K线画布"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TXT_APP_TITLE)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.window_size = tuple(CONFIG.get('default_window_size',
                                          [DEFAULT_WINDOW_WIDTH,
                                           DEFAULT_WINDOW_HEIGHT]))

        self.agent = TdxDataAgent()
        self.cache_mgr = DataCacheManager()
        self.loader = DataLoader(self.agent, self.cache_mgr)

        self.current_symbol = ''
        self.current_focus_date = 0
        self.current_attention_date = 0
        self.current_tp_ratio = DEFAULT_TP_RATIO
        self.current_sl_ratio = DEFAULT_SL_RATIO
        self.current_tpsl_days = DEFAULT_TPSL_DAYS
        self.list_data: List[List] = []

        self._setup_ui()
        self._connect_signals()
        self._apply_window_style()

    def _setup_ui(self) -> None:
        """构建主窗口UI布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.list_panel = ListPanel()
        splitter.addWidget(self.list_panel)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        toolbar_layout.setSpacing(6)

        self.lbl_stock_info = QLabel("")
        self.lbl_stock_info.setStyleSheet(
            f"color:{COLOR_TEXT_PRIMARY};font-weight:bold;font-size:12px;"
            f"padding:0px 4px;")
        self.lbl_stock_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        toolbar_layout.addWidget(self.lbl_stock_info)

        sep0 = QLabel("|")
        sep0.setStyleSheet(f"color:{COLOR_TEXT_MUTED};font-size:12px;")
        sep0.setFixedWidth(10)
        sep0.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar_layout.addWidget(sep0)

        self.btn_jump_ths = QPushButton(TXT_TONGHUASHUN)
        self.btn_jump_ths.setFixedHeight(28)
        self.btn_jump_ths.setFixedWidth(72)
        self.btn_jump_ths.setToolTip(TXT_JUMP_TO_THS)
        self.btn_jump_ths.setStyleSheet(
            f"QPushButton{{background:{COLOR_BG_TERTIARY};"
            f"color:{COLOR_TEXT_PRIMARY};border:1px solid {COLOR_SELECTION};"
            f"border-radius:4px;padding:2px 8px;font-size:12px;}}"
            f"QPushButton:hover{{background:{COLOR_SELECTION};}}"
            f"QPushButton:pressed{{background:{COLOR_BG_TERTIARY};}}")
        toolbar_layout.addWidget(self.btn_jump_ths)

        sep = QLabel("|")
        sep.setStyleSheet(f"color:{COLOR_TEXT_MUTED};font-size:12px;")
        sep.setFixedWidth(10)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar_layout.addWidget(sep)

        # 止盈百分比
        lbl_tp = QLabel(TXT_TP_PCT)
        lbl_tp.setStyleSheet(
            f"color:{COLOR_TEXT_SECONDARY};font-size:11px;")
        toolbar_layout.addWidget(lbl_tp)

        self.edit_tp = QSpinBox()
        self.edit_tp.setRange(1, 100)
        self.edit_tp.setValue(int(DEFAULT_TP_RATIO * 100))
        self.edit_tp.setFixedWidth(56)
        self.edit_tp.setFixedHeight(24)
        self.edit_tp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_tp.setSuffix('%')
        spinbox_style = (
            f"QSpinBox{{background:{COLOR_BG_TERTIARY};"
            f"color:{COLOR_TEXT_PRIMARY};border:1px solid {COLOR_BG_TERTIARY};"
            f"border-radius:3px;font-size:11px;padding:1px 2px;}}"
            f"QSpinBox:focus{{border:1px solid {COLOR_SELECTION};}}"
            f"QSpinBox::up-button{{width:14px;border:none;background:{COLOR_BG_TERTIARY};}}"
            f"QSpinBox::down-button{{width:14px;border:none;background:{COLOR_BG_TERTIARY};}}"
            f"QSpinBox::up-arrow{{width:6px;height:6px;border-left:3px solid transparent;"
            f"border-right:3px solid transparent;border-bottom:4px solid {COLOR_TEXT_MUTED};}}"
            f"QSpinBox::down-arrow{{width:6px;height:6px;border-left:3px solid transparent;"
            f"border-right:3px solid transparent;border-top:4px solid {COLOR_TEXT_MUTED};}}")
        self.edit_tp.setStyleSheet(spinbox_style)
        self.edit_tp.setToolTip(TXT_TP_PCT_TOOLTIP)
        toolbar_layout.addWidget(self.edit_tp)

        # 止损百分比
        lbl_sl = QLabel(TXT_SL_PCT)
        lbl_sl.setStyleSheet(
            f"color:{COLOR_TEXT_SECONDARY};font-size:11px;")
        toolbar_layout.addWidget(lbl_sl)

        self.edit_sl = QSpinBox()
        self.edit_sl.setRange(-100, -1)
        self.edit_sl.setValue(int(DEFAULT_SL_RATIO * 100))
        self.edit_sl.setFixedWidth(56)
        self.edit_sl.setFixedHeight(24)
        self.edit_sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_sl.setSuffix('%')
        self.edit_sl.setStyleSheet(spinbox_style)
        self.edit_sl.setToolTip(TXT_SL_PCT_TOOLTIP)
        toolbar_layout.addWidget(self.edit_sl)

        # 止盈止损交易日天数
        lbl_days = QLabel(TXT_DAYS_LABEL)
        lbl_days.setStyleSheet(
            f"color:{COLOR_TEXT_SECONDARY};font-size:11px;")
        toolbar_layout.addWidget(lbl_days)

        self.edit_tpsl_days = QSpinBox()
        self.edit_tpsl_days.setRange(1, 999)
        self.edit_tpsl_days.setValue(DEFAULT_TPSL_DAYS)
        self.edit_tpsl_days.setFixedWidth(52)
        self.edit_tpsl_days.setFixedHeight(24)
        self.edit_tpsl_days.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_tpsl_days.setStyleSheet(spinbox_style)
        self.edit_tpsl_days.setToolTip(TXT_TPSL_DAYS_TOOLTIP)
        toolbar_layout.addWidget(self.edit_tpsl_days)

        # 更新按钮
        self.btn_tpsl_update = QPushButton(TXT_UPDATE)
        self.btn_tpsl_update.setFixedHeight(24)
        self.btn_tpsl_update.setFixedWidth(48)
        self.btn_tpsl_update.setToolTip(TXT_TPSL_UPDATE_TOOLTIP)
        self.btn_tpsl_update.setStyleSheet(
            f"QPushButton{{background:{COLOR_BG_TERTIARY};"
            f"color:{COLOR_TEXT_PRIMARY};border:1px solid {COLOR_SELECTION};"
            f"border-radius:3px;padding:2px 6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{COLOR_SELECTION};}}"
            f"QPushButton:pressed{{background:{COLOR_BG_TERTIARY};}}")
        toolbar_layout.addWidget(self.btn_tpsl_update)

        # 止盈止损结果显示标签（更新按钮后面，支持富文本）
        self.lbl_tpsl_result = QLabel("")
        self.lbl_tpsl_result.setStyleSheet(
            f"color:{COLOR_TEXT_SECONDARY};font-size:11px;padding:0px 4px;")
        self.lbl_tpsl_result.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.lbl_tpsl_result.setTextFormat(Qt.TextFormat.RichText)
        toolbar_layout.addWidget(self.lbl_tpsl_result)

        toolbar_layout.addStretch()

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar_layout)
        toolbar_widget.setFixedHeight(36)
        toolbar_widget.setStyleSheet(
            f"background:{COLOR_BG_SECONDARY};"
            f"border-bottom:1px solid {COLOR_BG_TERTIARY};")
        right_layout.addWidget(toolbar_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(
            f"QScrollArea{{border:none;background:{COLOR_BG_PRIMARY};}}")

        self.kline_canvas = KlineCanvas()
        scroll_area.setWidget(self.kline_canvas)
        right_layout.addWidget(scroll_area)

        splitter.addWidget(right_widget)

        splitter.setSizes([LIST_PANEL_FIXED_WIDTH,
                          self.window_size[0] - LIST_PANEL_FIXED_WIDTH])
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle{{background:{COLOR_SELECTION};}}")

        main_layout.addWidget(splitter)

        self._create_menu_bar()
        self._create_status_bar()

        self.resize(*self.window_size)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

    def _create_menu_bar(self) -> None:
        """创建顶部菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet(
            f"QMenuBar{{background:{COLOR_BG_SECONDARY};"
            f"color:{COLOR_TEXT_PRIMARY};padding:2px;"
            f"font-size:12px;font-weight:bold;}}"
            f"QMenuBar::item:selected{{"
            f"background:{COLOR_SELECTION};}}"
            f"QMenuBar::item:pressed{{"
            f"background:{COLOR_SELECTION};}}")

        file_menu = menubar.addMenu(TXT_FILE_MENU)
        act_open = QAction(TXT_OPEN_FILE, self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_open_file)
        file_menu.addAction(act_open)
        file_menu.addSeparator()
        act_exit = QAction(TXT_EXIT, self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        view_menu = menubar.addMenu(TXT_VIEW_MENU)
        act_zoom_in = QAction(TXT_ZOOM_IN, self)
        act_zoom_in.setShortcut("Ctrl++")
        act_zoom_in.triggered.connect(self.kline_canvas.zoom_in)
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction(TXT_ZOOM_OUT, self)
        act_zoom_out.setShortcut("Ctrl+-")
        act_zoom_out.triggered.connect(self.kline_canvas.zoom_out)
        view_menu.addAction(act_zoom_out)

        act_reset = QAction(TXT_RESET_VIEW, self)
        act_reset.setShortcut("Ctrl+R")
        act_reset.triggered.connect(self.kline_canvas.reset_view)
        view_menu.addAction(act_reset)
        view_menu.addSeparator()

        act_export = QAction(TXT_EXPORT_PNG, self)
        act_export.setShortcut("Ctrl+S")
        act_export.triggered.connect(self._on_export_png)
        view_menu.addAction(act_export)

        help_menu = menubar.addMenu(TXT_HELP_MENU)
        act_about = QAction(TXT_ABOUT, self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _create_status_bar(self) -> None:
        """创建底部状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet(
            f"QStatusBar{{background:{COLOR_BG_SECONDARY};"
            f"color:{COLOR_TEXT_SECONDARY};font-size:11px;"
            f"border-top:1px solid {COLOR_BG_TERTIARY};}}")

        self.status_label = QLabel(TXT_READY)
        self.status_bar.addWidget(self.status_label, stretch=1)

    def _apply_window_style(self) -> None:
        """应用主窗口深色主题"""
        self.setStyleSheet(
            f"QMainWindow{{background:{COLOR_BG_PRIMARY};}}"
            f"QWidget{{background:{COLOR_BG_PRIMARY};"
            f"color:{COLOR_TEXT_PRIMARY};}}"
            f"QToolTip{{"
            f"background-color:{COLOR_BG_SECONDARY};"
            f"color:{COLOR_TEXT_PRIMARY};"
            f"border:1px solid {COLOR_BG_TERTIARY};"
            f"border-radius:4px;"
            f"padding:4px;"
            f"opacity:230;}}")

    def _connect_signals(self) -> None:
        """连接所有组件间信号"""
        self.list_panel.row_selected.connect(self._on_list_row_selected)

        self.loader.data_ready.connect(self._on_data_loaded)
        self.loader.error_occurred.connect(self._on_load_error)

        self.kline_canvas.bar_clicked.connect(self._on_bar_clicked)
        self.kline_canvas.bar_double_clicked.connect(
            self._on_bar_double_clicked)
        self.kline_canvas.focus_changed.connect(self._on_focus_changed)

        self.kline_canvas.export_requested.connect(self._on_export_png)

        self.btn_jump_ths.clicked.connect(self._on_jump_ths)
        self.btn_tpsl_update.clicked.connect(self._on_tpsl_update)

    def _on_open_file(self) -> None:
        """打开文件对话框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, TXT_SELECT_FILE,
            os.path.dirname(os.path.realpath(__file__)),
            TXT_TAB_FILE_FILTER)
        if not file_path:
            return

        self._load_file(file_path)

    def _load_file(self, filepath: str) -> None:
        """加载并解析文件"""
        self.status_label.setText(TXT_FILE_LOADING)
        QApplication.processEvents()

        parser = FileParser(filepath)
        success = parser.parse()

        if not success:
            QMessageBox.warning(
                self, TXT_LOAD_FAILED_TITLE,
                TXT_CANNOT_PARSE)
            self.status_label.setText(TXT_READY)
            return

        self.list_data = parser.get_data()
        self.list_panel.load_data(self.list_data)
        self.kline_canvas._clear_axes()
        self.kline_canvas.draw()
        self.current_symbol = ''
        self.current_focus_date = 0
        self.lbl_stock_info.setText("")

        msg = (f"{TXT_LOAD_SUCCESS} | {TXT_VALID}:{parser.valid_lines} "
              f"{TXT_SKIPPED}:{parser.skipped_lines}")
        self.status_label.setText(msg)
        Logger.log().info(msg)

        QMessageBox.information(
            self, TXT_LOAD_COMPLETE,
            f'{TXT_VALID_RECORDS}: {parser.valid_lines}\n'
            f'{TXT_SKIPPED_LINES}: {parser.skipped_lines}')

    def _on_list_row_selected(self, row: int) -> None:
        """列表行选中处理"""
        if row < 0 or row >= len(self.list_data):
            return

        item = self.list_data[row]
        dt, sym = item[0], item[1]
        fd = item[2] if len(item) > 2 else 0
        tp_ratio = item[3] if len(item) > 3 else DEFAULT_TP_RATIO
        sl_ratio = item[4] if len(item) > 4 else DEFAULT_SL_RATIO

        self.current_symbol = str(sym).zfill(6)
        self.current_focus_date = int(fd) if fd else 0
        self.current_attention_date = int(fd) if fd else 0
        self.current_tp_ratio = float(tp_ratio)
        self.current_sl_ratio = float(sl_ratio)
        self.edit_tp.setValue(int(self.current_tp_ratio * 100))
        self.edit_sl.setValue(int(self.current_sl_ratio * 100))
        self.edit_tpsl_days.setValue(self.current_tpsl_days)
        self.lbl_stock_info.setText(
            f"{self.current_symbol}  "
            f"{TXT_ATTENTION_DATE}:{self.current_attention_date}")

        self._request_kline_data()

    def _request_kline_data(self) -> None:
        """请求K线数据"""
        symbol = self.current_symbol
        focus_date = self.current_focus_date

        if not symbol or focus_date <= 0:
            Logger.log().warning(
                f"{TXT_INVALID_PARAMS}: symbol={symbol}, fd={focus_date}")
            return

        start_date = focus_date - PRELOAD_BARS * 2
        end_date = focus_date + PRELOAD_BARS * 2

        self.status_label.setText(f"{TXT_KLINE_LOADING} {symbol}")
        self.loader.load_data(symbol, start_date, end_date)

    def _on_data_loaded(self, symbol: str, df: pd.DataFrame) -> None:
        """数据加载成功回调"""
        if symbol != self.current_symbol:
            return

        if df.empty:
            self.status_label.setText(TXT_NO_DATA)
            return

        df_calc = IndicatorCalc.calc_all(df)
        self.kline_canvas._list_panel_width = self.list_panel.width()
        focus_idx = self.kline_canvas.load_and_draw(
            df_calc, self.current_focus_date, symbol=self.current_symbol,
            tp_ratio=self.current_tp_ratio, sl_ratio=self.current_sl_ratio,
            agent=self.agent, tpsl_days=self.current_tpsl_days)
        self.status_label.setText(
            f"{TXT_READY} | {symbol} | {len(df)} {TXT_KLINE_COUNT}")

        # 同步更新工具栏止盈止损结果标签
        self.lbl_tpsl_result.setText(
            self.kline_canvas._tpsl_html.strip())

        # 数据加载后显示Popup（避开遮挡）
        if focus_idx is not None:
            self.kline_canvas.select_bar(
                focus_idx, show_popup=True, avoid_occlude=True)

        self.setFocus()

        Logger.log().info(
            f"{TXT_KLINE_LOADED}: {symbol} | "
            f"{TXT_TOTAL_LINES}={len(df)} | "
            f"{TXT_FOCUS_DAY}={self.current_focus_date}")

    def _on_load_error(self, symbol: str, err_msg: str) -> None:
        """数据加载失败回调"""
        self.status_label.setText(TXT_LOAD_FAILED)
        Logger.log().error(f"{TXT_KLINE_DATA_LOAD_FAILED} [{symbol}]: {err_msg}")
        QMessageBox.warning(
            self, TXT_LOAD_ERROR,
            f'{TXT_CANNOT_LOAD_DATA} {symbol}:\n{err_msg}')

    def _on_bar_clicked(self, index: int) -> None:
        """K线单击处理：设临时焦点日期，显示十字光标，Popup避开遮挡"""
        self.kline_canvas.select_bar(index, show_popup=True,
                                     avoid_occlude=True)

    def _on_bar_double_clicked(self, index: int) -> None:
        """K线双击处理：定位到双击日期，显示Popup详细指标"""
        if self.kline_canvas.df_indicator is None:
            return
        row = self.kline_canvas.df_indicator.iloc[index]
        new_fd = int(row['r_date'])
        self.current_focus_date = new_fd
        self.kline_canvas.redraw_with_new_focus(new_fd)

        self.kline_canvas.select_bar(index, show_popup=True)

        self.lbl_stock_info.setText(
            f"{self.current_symbol}  "
            f"{TXT_ATTENTION_DATE}:{self.current_attention_date}")
        Logger.log().info(
            f"{TXT_DOUBLE_CLICK_LOCATE}: {self.current_symbol} -> {new_fd}")

    def _on_focus_changed(self, index: int) -> None:
        """键盘焦点变更：仅更新焦点日期和状态栏，不更新止盈止损"""
        if self.kline_canvas.df_indicator is None:
            return
        if 0 <= index < len(self.kline_canvas.df_indicator):
            row = self.kline_canvas.df_indicator.iloc[index]
            new_fd = int(row['r_date'])
            self.current_focus_date = new_fd
            self.kline_canvas.focus_date_val = new_fd

    def _on_export_png(self) -> None:
        """导出PNG"""
        default_name = (f"{self.current_symbol}_"
                        f"{self.current_focus_date}.png")
        save_path, _ = QFileDialog.getSaveFileName(
            self, TXT_EXPORT_PNG_TITLE, default_name,
            f"{TXT_PNG_IMAGE} (*.png);;{TXT_ALL_FILE_FILTER}")
        if save_path:
            self.kline_canvas.export_png(save_path)

    def _on_tpsl_update(self) -> None:
        """根据输入的止盈止损百分比和天数刷新计算结果（基于关注日期）"""
        if not self.current_symbol or self.current_attention_date <= 0:
            self.status_label.setText(TXT_PLEASE_SELECT_STOCK_DATE)
            return

        tp_val = float(self.edit_tp.value())
        sl_val = float(self.edit_sl.value())
        days_val = self.edit_tpsl_days.value()

        if days_val <= 0:
            self.status_label.setText(TXT_TPSL_DAYS_MUST_POSITIVE)
            return

        self.current_tp_ratio = tp_val / 100.0
        self.current_sl_ratio = sl_val / 100.0
        self.current_tpsl_days = days_val

        if self.kline_canvas.df_indicator is not None:
            self.kline_canvas._calc_tpsl(
                self.kline_canvas.df_indicator,
                self.current_attention_date,
                self.current_tp_ratio, self.current_sl_ratio,
                self.agent, self.current_tpsl_days)

        self.status_label.setText(
            f"{TXT_TPSL_UPDATED}: {TXT_TAKE_PROFIT}{tp_val}% "
            f"{TXT_STOP_LOSS}{sl_val}% "
            f"{TXT_DAYS_LABEL}{days_val}{TXT_DAY}")

        self.lbl_tpsl_result.setText(
            self.kline_canvas._tpsl_html.strip())

    def _on_jump_ths(self) -> None:
        """跳转到同花顺查看当前股票
        
        参考ths_tools.py的实现重新生成，不调用现有代码。
        流程：查找窗口 -> 激活窗口 -> 输入代码 -> 确认定位
        未找到窗口时尝试启动同花顺程序。
        """
        if not self.current_symbol:
            self.status_label.setText(TXT_PLEASE_SELECT_STOCK)
            return

        padded_code = self.current_symbol.zfill(6)
        self.status_label.setText(f"{TXT_JUMPING_THS} {padded_code}...")

        try:
            # Step 1: 查找同花顺窗口
            ths_window = None
            for window in gw.getAllWindows():
                if window.title:
                    for keyword in THS_KEYWORDS:
                        if keyword in window.title:
                            ths_window = window
                            break
                if ths_window:
                    break

            # Step 2: 未找到窗口 -> 尝试启动同花顺
            if not ths_window:
                launched = False
                ths_paths = [
                    r"C:\同花顺软件\同花顺\hexinlauncher.exe",
                    r"D:\同花顺\hexin.exe",
                    r"C:\Program Files\同花顺\hexin.exe",
                    r"C:\ths\hexin.exe",
                ]
                for path in ths_paths:
                    if os.path.exists(path):
                        import subprocess
                        subprocess.Popen([path])
                        Logger.log().info(f"{TXT_START_THS}: {path}")
                        launched = True
                        break

                if launched:
                    time.sleep(5)
                    for window in gw.getAllWindows():
                        if window.title:
                            for keyword in THS_KEYWORDS:
                                if keyword in window.title:
                                    ths_window = window
                                    break
                        if ths_window:
                            break

                if not ths_window:
                    self.status_label.setText(
                        f"{TXT_THS_NOT_FOUND} {padded_code}")
                    QMessageBox.information(
                        self, TXT_THS_JUMP,
                        f"{TXT_THS_WINDOW_NOT_FOUND} {padded_code}")
                    return

            # Step 3: 激活窗口
            try:
                if ths_window.isMinimized:
                    ths_window.restore()
                ths_window.activate()
                time.sleep(0.5)
            except Exception:
                self.status_label.setText(TXT_THS_CANNOT_ACTIVATE)
                QMessageBox.information(
                    self, TXT_THS_JUMP, TXT_THS_CANNOT_ACTIVATE)
                return

            # Step 4: 输入股票代码并定位日K线
            time.sleep(1)
            pyautogui.typewrite(padded_code)
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(2)
            pyautogui.press('f5')
            time.sleep(1)

            self.status_label.setText(
                f"{TXT_THS_LOCATED} {padded_code} {TXT_DAILY_KLINE}")
            Logger.log().info(f"{TXT_THS_LOCATED}: {padded_code}")

        except Exception as e:
            Logger.log().error(f"{TXT_THS_JUMP_FAILED}: {e}")
            self.status_label.setText(f"{TXT_THS_JUMP_EXCEPTION}: {e}")
            QMessageBox.warning(self, TXT_THS_JUMP_FAILED, str(e))

    def _show_about(self) -> None:
        """关于对话框"""
        QMessageBox.about(self, TXT_ABOUT_TITLE, TXT_ABOUT_CONTENT)

    def keyPressEvent(self, event) -> None:
        """全局键盘事件分发"""
        key = event.key()

        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Escape):
            self.kline_canvas.keyPressEvent(event)
            if event.isAccepted():
                return

        if key == Qt.Key.Key_Up:
            cur_row = self.list_panel.current_row()
            if cur_row > 0:
                self.list_panel.select_row(cur_row - 1)
        elif key == Qt.Key.Key_Down:
            cur_row = self.list_panel.current_row()
            if cur_row < self.list_panel.total_rows() - 1:
                self.list_panel.select_row(cur_row + 1)
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cur_row = self.list_panel.current_row()
            if cur_row >= 0:
                self._on_list_row_selected(cur_row)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """窗口关闭事件：清理资源"""
        self.loader.cancel()
        self.loader.wait(2000)
        self.cache_mgr.clear()
        event.accept()


# ==================== 入口点 ====================

def main():
    """应用主入口函数"""
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("StockReviewTool")

    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)

    app.setStyleSheet(
        f"QToolTip{{"
        f"background-color:{COLOR_BG_SECONDARY};"
        f"color:{COLOR_TEXT_PRIMARY};"
        f"border:1px solid {COLOR_BG_TERTIARY};"
        f"border-radius:4px;"
        f"padding:4px;"
        f"opacity:230;}}")

    window = MainWindow()
    window.show()

    Logger.log().info(TXT_APP_STARTED)

    exit_code = app.exec()
    Logger.log().info(f"{TXT_PROGRAM_EXIT}{exit_code}")
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
