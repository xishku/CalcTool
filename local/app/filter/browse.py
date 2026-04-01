#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据解析与K线图分析工具
功能：
1. 读取并解析list.txt格式的股票数据文件
2. 在GUI左侧显示所有股票数据行
3. 点击左侧行，右侧显示详细信息
4. 支持加载扩展的K线图，默认聚焦在基准日期区间
5. 集成mplfinance绘制专业的K线图
6. 支持跳转到同花顺查看股票K线图
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import matplotlib
matplotlib.use('TkAgg')  # 使用Tkinter后端
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import mplfinance as mpf
import mplcursors
from pathlib import Path
import numpy as np
import csv
import webbrowser
import subprocess
import platform


class ListFileParser:
    """
    解析 list.txt 文件的类
    处理制表符分隔的文本文件，格式为：时间戳<tab>代码<tab>日期序列
    """
    
    def __init__(self, filepath: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            filepath: 文件路径，可选
        """
        self.filepath = filepath
        self.parsed_data = []  # 原始解析数据
        self.df = pd.DataFrame()  # DataFrame格式数据
        self.summary = {}  # 统计摘要
    
    def parse_file(self, filepath: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        解析文件内容
        
        Args:
            filepath: 文件路径，如果为None则使用初始化时指定的路径
        
        Returns:
            包含解析后数据的字典列表
        """
        if filepath is None:
            if self.filepath is None:
                raise ValueError("未提供文件路径")
            filepath = self.filepath
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        parsed_data = []
        line_count = 0
        error_count = 0
        
        with open(filepath, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                # 跳过空行
                if not line.strip():
                    continue
                
                line_count += 1
                
                try:
                    # 解析单行
                    parsed_item = self._parse_line(line.strip(), line_num)
                    if parsed_item:
                        parsed_data.append(parsed_item)
                except Exception as e:
                    error_count += 1
                    print(f"解析第 {line_num} 行时出错: {e}")
                    continue
        
        self.parsed_data = parsed_data
        self.filepath = filepath
        
        # 生成统计信息
        self._generate_summary(line_count, error_count)
        
        return parsed_data
    
    def _parse_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """
        解析单行数据
        
        Args:
            line: 行内容
            line_num: 行号（用于错误提示）
        
        Returns:
            解析后的字典，解析失败返回None
        """
        # 按制表符分割
        parts = line.split('\t')
        
        if len(parts) < 2:
            raise ValueError(f"格式错误，至少需要2个字段，实际{len(parts)}个: {line}")
        
        # 解析第一个字段：日期时间
        timestamp_str = parts[0]
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            # 尝试不带微秒的格式
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                raise ValueError(f"时间戳格式错误: {timestamp_str}") from e
        
        # 第二个字段：股票代码
        code = parts[1]
        
        # 第三个及以后的字段：日期序列
        date_sequence = []
        for date_str in parts[2:]:
            if date_str:  # 跳过空字符串
                try:
                    # 解析日期，格式为 YYYYMMDD
                    date_obj = datetime.strptime(date_str, "%Y%m%d").date()
                    date_sequence.append(date_obj)
                except ValueError as e:
                    raise ValueError(f"日期格式错误: {date_str}") from e
        
        return {
            'timestamp': timestamp,
            'code': code,
            'date_sequence': date_sequence,
            'date_count': len(date_sequence),
            'line_number': line_num,
            'original_line': line
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        将解析结果转换为DataFrame
        
        Returns:
            DataFrame，包含解析后的数据
        """
        if not self.parsed_data:
            raise ValueError("未解析任何数据，请先调用 parse_file()")
        
        # 转换为DataFrame
        df = pd.DataFrame(self.parsed_data)
        
        # 添加辅助列
        df['timestamp_str'] = df['timestamp'].apply(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f")
        )
        df['date_sequence_str'] = df['date_sequence'].apply(
            lambda dates: [d.strftime("%Y-%m-%d") for d in dates]
        )
        df['date_sequence_yyyymmdd'] = df['date_sequence'].apply(
            lambda dates: [d.strftime("%Y%m%d") for d in dates]
        )
        df['first_date'] = df['date_sequence'].apply(
            lambda dates: dates[0].strftime("%Y-%m-%d") if dates else None
        )
        df['last_date'] = df['date_sequence'].apply(
            lambda dates: dates[-1].strftime("%Y-%m-%d") if dates else None
        )
        
        self.df = df
        return df
    
    def _generate_summary(self, total_lines: int, error_lines: int):
        """生成统计摘要"""
        if not self.parsed_data:
            self.summary = {}
            return
        
        total_dates = sum(len(item['date_sequence']) for item in self.parsed_data)
        avg_dates_per_code = total_dates / len(self.parsed_data) if self.parsed_data else 0
        
        # 获取时间范围
        timestamps = [item['timestamp'] for item in self.parsed_data]
        min_time = min(timestamps) if timestamps else None
        max_time = max(timestamps) if timestamps else None
        
        self.summary = {
            'total_lines': total_lines,
            'parsed_lines': len(self.parsed_data),
            'error_lines': error_lines,
            'total_dates': total_dates,
            'avg_dates_per_code': round(avg_dates_per_code, 2),
            'time_range': f"{min_time} 到 {max_time}" if min_time and max_time else None,
            'unique_codes': len(set(item['code'] for item in self.parsed_data)),
            'success_rate': round(len(self.parsed_data) / total_lines * 100, 2) if total_lines > 0 else 0
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取解析统计摘要
        
        Returns:
            统计信息字典
        """
        return self.summary
    
    def get_codes(self) -> List[str]:
        """
        获取所有唯一的代码
        
        Returns:
            代码列表
        """
        if not self.parsed_data:
            return []
        return sorted(set(item['code'] for item in self.parsed_data))
    
    def get_code_data(self, code: str) -> List[Dict[str, Any]]:
        """
        获取指定代码的所有记录
        
        Args:
            code: 股票代码
        
        Returns:
            该代码的所有记录
        """
        return [item for item in self.parsed_data if item['code'] == code]
    
    def get_dates_for_code(self, code: str) -> List[date]:
        """
        获取指定代码的所有日期（去重）
        
        Args:
            code: 股票代码
        
        Returns:
            日期列表
        """
        dates = []
        for item in self.parsed_data:
            if item['code'] == code:
                dates.extend(item['date_sequence'])
        return sorted(set(dates))
    
    def filter_by_date(self, target_date: str) -> List[Dict[str, Any]]:
        """
        筛选包含指定日期的记录
        
        Args:
            target_date: 目标日期，格式 YYYY-MM-DD
        
        Returns:
            包含目标日期的记录
        """
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        result = []
        for item in self.parsed_data:
            if target_date_obj in item['date_sequence']:
                result.append(item)
        return result


class KLineChartManager:
    """K线图管理器 - 支持扩展显示，默认聚焦基准区间"""
    
    def __init__(self):
        # 配置matplotlib中文字体
        matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        matplotlib.rcParams['axes.unicode_minus'] = False
        
        # 当前图表相关对象
        self.current_figure = None
        self.current_canvas = None
        self.current_toolbar = None
        self.current_axlist = None
        self.cursor = None
        self.current_df = None
        self.plot_df = None
        self.kline_data = None  # 存储K线图数据
        
        # 扩展天数
        self.extend_days = 20
        
        # 基准区间信息
        self.base_start_idx = 0
        self.base_end_idx = 0
        self.base_start_date = ""
        self.base_end_date = ""
        
        # 数据获取代理
        self.data_agent = None
        
    def safe_get_value(self, row, key, default="N/A"):
        """安全获取值，防止KeyError"""
        try:
            if key in row:
                value = row[key]
                if pd.isna(value):
                    return default
                return value
            return default
        except:
            return default
    
    def on_add(self, sel):
        """鼠标悬停提示的回调函数"""
        if self.kline_data is None or len(self.kline_data) == 0:
            return
        
        # 获取鼠标位置的索引
        idx = int(sel.index[0]) if isinstance(sel.index, tuple) else int(sel.index)
        
        # 确保索引不越界
        if idx < len(self.kline_data):
            row = self.kline_data.iloc[idx]
            
            # 获取对应的日期
            date_str = "N/A"
            if hasattr(self, 'current_df') and self.current_df is not None and idx < len(self.current_df):
                if 'date' in self.current_df.columns:
                    date_str = str(self.safe_get_value(self.current_df.iloc[idx], 'date', 'N/A'))
            
            # 检查是否在基准区间内
            in_base_period = ""
            if hasattr(self, 'base_start_idx') and hasattr(self, 'base_end_idx'):
                if self.base_start_idx <= idx <= self.base_end_idx:
                    in_base_period = " (基准区间内)"
            
            # 使用安全的方式获取值
            open_val = self.safe_get_value(row, 'Open', 'N/A')
            high_val = self.safe_get_value(row, 'High', 'N/A')
            low_val = self.safe_get_value(row, 'Low', 'N/A')
            close_val = self.safe_get_value(row, 'Close', 'N/A')
            
            # 格式化数值
            try:
                if open_val != 'N/A':
                    open_val = f"{float(open_val):.2f}"
                if high_val != 'N/A':
                    high_val = f"{float(high_val):.2f}"
                if low_val != 'N/A':
                    low_val = f"{float(low_val):.2f}"
                if close_val != 'N/A':
                    close_val = f"{float(close_val):.2f}"
            except:
                pass
            
            # 自定义显示的文本内容
            text = (f"日期: {date_str}{in_base_period}\n"
                    f"开盘: {open_val}\n"
                    f"最高: {high_val}\n"
                    f"最低: {low_val}\n"
                    f"收盘: {close_val}")
            
            # 设置提示框文本
            sel.annotation.set_text(text)
            
            # 美化提示框样式
            sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightyellow')
    
    def get_stock_data(self, stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            
        Returns:
            包含股票数据的DataFrame
        """
        # 尝试获取真实数据
        if self.data_agent and hasattr(self.data_agent, 'read_kdata_cache'):
            try:
                if start_date is None:
                    start_date = "20240101"
                if end_date is None:
                    end_date = datetime.now().strftime("%Y%m%d")
                
                df = self.data_agent.read_kdata_cache(stock_code, start_date, end_date)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                print(f"获取真实数据失败: {e}")
        
        # 回退方案：生成模拟数据
        print(f"使用模拟数据展示: {stock_code}")
        return self._generate_mock_data(stock_code, start_date, end_date)
    
    def _generate_mock_data(self, stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """生成模拟股票数据用于演示"""
        if start_date is None:
            start_date = "20240101"
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        
        # 生成日期范围
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        
        # 生成所有日期（包括周末）
        all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        
        # 过滤掉周末（模拟交易日）
        trading_dates = all_dates[all_dates.weekday < 5]
        
        n_days = len(trading_dates)
        if n_days == 0:
            # 如果没有交易日，使用所有日期
            trading_dates = all_dates
            n_days = len(trading_dates)
        
        # 生成模拟价格数据
        np.random.seed(hash(stock_code) % 10000)  # 使用股票代码作为随机种子
        
        # 基础价格
        base_price = 10.0 + (hash(stock_code) % 100) / 10.0
        
        # 生成随机游走
        returns = np.random.randn(n_days) * 0.02
        prices = base_price * (1 + returns).cumprod()
        
        # 生成OHLC数据
        df = pd.DataFrame(index=range(n_days))
        df['open'] = prices * (1 + np.random.randn(n_days) * 0.01)
        df['high'] = df['open'] * (1 + np.abs(np.random.randn(n_days)) * 0.03)
        df['low'] = df['open'] * (1 - np.abs(np.random.randn(n_days)) * 0.03)
        df['close'] = prices
        df['volume'] = np.random.randint(10000, 1000000, n_days)
        df['date'] = [d.strftime("%Y%m%d") for d in trading_dates]
        
        return df
    
    def prepare_data_for_mplfinance(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据用于mplfinance绘图"""
        if df is None or df.empty:
            return None
        
        # 复制数据
        plot_df = df.copy()
        
        # 确保有必要的列
        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        available_columns = set(plot_df.columns)
        
        # 检查并创建缺失的列
        for col in required_columns:
            if col not in available_columns:
                if col == 'volume':
                    plot_df[col] = 0
                else:
                    plot_df[col] = 0.0
        
        # 准备mplfinance所需的列
        column_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low', 
            'close': 'Close',
            'volume': 'Volume'
        }
        
        for src_col, target_col in column_mapping.items():
            if src_col in plot_df.columns:
                if src_col == 'high' or src_col == 'low' or src_col == 'close':
                    # 如果价格已经是除以100的，就不需要再除
                    if plot_df[src_col].max() < 1000:  # 假设价格小于1000表示已经是除以100后的
                        plot_df[target_col] = plot_df[src_col]
                    else:
                        plot_df[target_col] = plot_df[src_col] / 100
                else:
                    plot_df[target_col] = plot_df[src_col]
        
        # 设置日期索引
        if 'date' in plot_df.columns:
            plot_df['Date'] = pd.to_datetime(plot_df['date'])
            plot_df.set_index('Date', inplace=True)
        elif plot_df.index.name == 'Date' or isinstance(plot_df.index, pd.DatetimeIndex):
            # 已经设置好了
            pass
        else:
            # 创建默认日期索引
            plot_df.index = pd.date_range(start='2024-01-01', periods=len(plot_df), freq='D')
        
        return plot_df
    
    def get_extended_stock_data(self, stock_code: str, base_start_date: str, 
                               base_end_date: str, extend_days: int = None) -> pd.DataFrame:
        """
        获取扩展的数据（向前和向后各扩展指定天数）
        
        Args:
            stock_code: 股票代码
            base_start_date: 基准开始日期 (YYYYMMDD)
            base_end_date: 基准结束日期 (YYYYMMDD)
            extend_days: 扩展天数，如果为None则使用self.extend_days
            
        Returns:
            扩展后的DataFrame
        """
        if extend_days is None:
            extend_days = self.extend_days
        
        # 保存基准日期
        self.base_start_date = base_start_date
        self.base_end_date = base_end_date
        
        # 将日期字符串转换为datetime
        try:
            base_start = datetime.strptime(base_start_date, "%Y%m%d")
            base_end = datetime.strptime(base_end_date, "%Y%m%d")
        except ValueError as e:
            raise ValueError(f"日期格式错误: {e}")
        
        # 计算扩展天数（考虑非交易日）
        extend_factor = 1.5  # 假设大约1/3的日子是非交易日
        
        # 向前扩展
        extended_start = base_start - timedelta(days=int(extend_days * extend_factor))
        
        # 向后扩展
        extended_end = base_end + timedelta(days=int(extend_days * extend_factor))
        
        # 确保结束日期不晚于今天
        today = datetime.now()
        if extended_end > today:
            extended_end = today
        
        # 转换为字符串格式
        extended_start_str = extended_start.strftime("%Y%m%d")
        extended_end_str = extended_end.strftime("%Y%m%d")
        
        # 获取扩展范围的数据
        df = self.get_stock_data(stock_code, extended_start_str, extended_end_str)
        
        if df is None or df.empty:
            return df
        
        # 标记基准日期范围
        df['is_base_period'] = False
        if 'date' in df.columns:
            # 确保日期是字符串格式
            mask = (df['date'] >= base_start_date) & (df['date'] <= base_end_date)
            df.loc[mask, 'is_base_period'] = True
            
            # 找到基准区间的开始和结束索引
            base_indices = df[mask].index
            if len(base_indices) > 0:
                self.base_start_idx = base_indices[0]
                self.base_end_idx = base_indices[-1]
        
        return df
    
    def create_kline_chart_with_extension(self, stock_code: str, base_start_date: str, 
                                        base_end_date: str) -> Tuple[plt.Figure, List]:
        """
        创建带扩展的K线图，默认聚焦在基准区间
        
        Args:
            stock_code: 股票代码
            base_start_date: 基准开始日期
            base_end_date: 基准结束日期
            
        Returns:
            (figure, axlist) 元组
        """
        # 获取扩展数据
        df = self.get_extended_stock_data(stock_code, base_start_date, base_end_date)
        
        if df is None or df.empty:
            raise ValueError(f"无法获取股票 {stock_code} 的扩展数据")
        
        # 保存原始数据
        self.current_df = df.copy()
        
        # 准备数据
        plot_df = self.prepare_data_for_mplfinance(df)
        if plot_df is None or plot_df.empty:
            raise ValueError("数据格式错误，无法绘制K线图")
        
        # 保存plot_df用于后续操作
        self.plot_df = plot_df.copy()
        self.kline_data = plot_df.copy()  # 保存K线图数据用于鼠标悬停
        
        # 获取实际显示的数据范围
        if 'date' in df.columns:
            actual_dates = df['date']
            if not actual_dates.empty:
                actual_start = str(actual_dates.iloc[0])
                actual_end = str(actual_dates.iloc[-1])
                
                # 计算实际交易日数量
                actual_trading_days = len(df)
                
                # 计算基准区间的交易日数量
                base_trading_days = len(df[df['is_base_period']]) if 'is_base_period' in df.columns else 0
            else:
                actual_start = "N/A"
                actual_end = "N/A"
                actual_trading_days = 0
                base_trading_days = 0
        else:
            actual_start = plot_df.index[0].strftime("%Y%m%d") if len(plot_df) > 0 else "N/A"
            actual_end = plot_df.index[-1].strftime("%Y%m%d") if len(plot_df) > 0 else "N/A"
            actual_trading_days = len(plot_df)
            base_trading_days = 0
        
        # 拼接标题
        chart_title = (
            f'{stock_code} 日K线 (扩展{self.extend_days}个交易日)\n'
            f'显示范围: {actual_start} 至 {actual_end} (共{actual_trading_days}个交易日)\n'
            f'基准区间: {base_start_date} 至 {base_end_date} (共{base_trading_days}个交易日)'
        )
        
        # 配置样式
        rc_params = {
            'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
            'axes.unicode_minus': False,
        }
        style = mpf.make_mpf_style(base_mpf_style='charles', rc=rc_params)
        
        # 计算聚焦范围：基准区间前后各加一些缓冲区
        focus_start_idx = max(0, self.base_start_idx - 10)  # 基准区间前10个交易日
        focus_end_idx = min(len(plot_df) - 1, self.base_end_idx + 10)  # 基准区间后10个交易日
        
        # 创建图表
        fig, axlist = mpf.plot(
            plot_df,
            type='candle',
            title=chart_title,
            volume=True,
            mav=(5, 10, 20, 30, 60),
            style=style,
            returnfig=True,
            figscale=1.5
        )
        
        # 设置x轴范围，聚焦在基准区间附近
        ax_kline = axlist[0]
        ax_volume = axlist[2] if len(axlist) > 2 else None
        
        # 设置x轴范围，使基准区间居中显示
        total_days = len(plot_df)
        if total_days > 0 and hasattr(self, 'base_start_idx') and hasattr(self, 'base_end_idx'):
            # 计算显示范围：基准区间前后各保留30%的空间
            buffer = int(total_days * 0.3)
            xlim_start = max(0, self.base_start_idx - buffer)
            xlim_end = min(total_days - 1, self.base_end_idx + buffer)
            
            # 设置K线图的x轴范围
            ax_kline.set_xlim(xlim_start - 0.5, xlim_end + 0.5)
            
            # 设置成交量图的x轴范围
            if ax_volume is not None:
                ax_volume.set_xlim(xlim_start - 0.5, xlim_end + 0.5)
            
            # 在基准区间添加背景色
            import matplotlib.patches as patches
            
            # 获取y轴范围
            ylim_kline = ax_kline.get_ylim()
            ylim_volume = ax_volume.get_ylim() if ax_volume is not None else (0, 1)
            
            # 在K线图上添加基准区间背景
            rect_kline = patches.Rectangle(
                (self.base_start_idx - 0.5, ylim_kline[0]),
                self.base_end_idx - self.base_start_idx + 1,
                ylim_kline[1] - ylim_kline[0],
                linewidth=0,
                alpha=0.1,
                facecolor='blue',
                zorder=0
            )
            ax_kline.add_patch(rect_kline)
            
            # 在成交量图上添加基准区间背景
            if ax_volume is not None:
                rect_volume = patches.Rectangle(
                    (self.base_start_idx - 0.5, ylim_volume[0]),
                    self.base_end_idx - self.base_start_idx + 1,
                    ylim_volume[1] - ylim_volume[0],
                    linewidth=0,
                    alpha=0.1,
                    facecolor='blue',
                    zorder=0
                )
                ax_volume.add_patch(rect_volume)
            
            # 添加基准区间标记线
            ax_kline.axvline(x=self.base_start_idx - 0.5, color='red', linestyle='--', alpha=0.5, linewidth=1)
            ax_kline.axvline(x=self.base_end_idx + 0.5, color='red', linestyle='--', alpha=0.5, linewidth=1)
            
            # 添加图例
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], color='blue', alpha=0.1, lw=4, label='基准区间'),
                Line2D([0], [0], color='red', alpha=0.5, linestyle='--', lw=1, label='基准边界')
            ]
            ax_kline.legend(handles=legend_elements, loc='upper left', fontsize=8)
        
        # 添加网格
        ax_kline.grid(True, alpha=0.3, linestyle='--')
        
        # 添加鼠标悬停提示
        self.cursor = mplcursors.cursor(axlist[0], hover=True)
        self.cursor.connect("add", self.on_add)
        
        return fig, axlist
    
    def clear_chart(self):
        """清除当前图表"""
        if self.current_figure:
            plt.close(self.current_figure)
        self.current_figure = None
        self.current_canvas = None
        self.current_toolbar = None
        self.current_axlist = None
        self.cursor = None
        self.current_df = None
        self.plot_df = None
        self.kline_data = None


class StockDataGUI:
    """股票数据GUI应用程序"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("股票数据解析与K线图分析")
        self.root.geometry("1400x800")
        
        # 数据解析器
        self.parser = ListFileParser()
        self.current_data = []
        
        # K线图管理器
        self.chart_manager = KLineChartManager()
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
        # 默认文件路径
        self.default_file = "list.txt"
        
        # 当前选中的股票信息
        self.selected_stock = {
            'code': None,
            'dates': [],
            'line_data': None
        }
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 自定义颜色
        self.bg_color = "#f0f0f0"
        self.left_panel_bg = "#e8e8e8"
        self.right_panel_bg = "#ffffff"
        
        self.root.configure(bg=self.bg_color)
    
    def create_widgets(self):
        """创建界面控件"""
        # 顶部工具栏
        self.create_toolbar()
        
        # 主内容区域
        self.create_main_content()
        
        # 状态栏
        self.create_statusbar()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = tk.Frame(self.root, bg=self.bg_color, height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # 打开文件按钮
        open_btn = ttk.Button(toolbar, text="打开文件", command=self.open_file)
        open_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 刷新按钮
        refresh_btn = ttk.Button(toolbar, text="刷新", command=self.refresh_data)
        refresh_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 搜索框
        search_frame = tk.Frame(toolbar, bg=self.bg_color)
        search_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(search_frame, text="搜索代码:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_data)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT)
        
        # 统计信息标签
        self.stats_label = ttk.Label(toolbar, text="未加载数据")
        self.stats_label.pack(side=tk.RIGHT, padx=20)
    
    def create_main_content(self):
        """创建主内容区域"""
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧面板 - 数据列表
        self.create_left_panel(main_frame)
        
        # 右侧面板 - K线图区域
        self.create_right_panel(main_frame)
    
    def create_left_panel(self, parent):
        """创建左侧数据面板"""
        left_frame = tk.Frame(parent, bg=self.left_panel_bg, relief=tk.RAISED, bd=1)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 标题
        title_frame = tk.Frame(left_frame, bg=self.left_panel_bg)
        title_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        ttk.Label(title_frame, text="股票数据列表", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        # 列表容器
        list_container = tk.Frame(left_frame, bg=self.left_panel_bg)
        list_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Treeview
        self.create_treeview(list_container)
    
    def create_treeview(self, parent):
        """创建数据表格"""
        # 滚动条
        tree_scroll_y = ttk.Scrollbar(parent, orient=tk.VERTICAL)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_scroll_x = ttk.Scrollbar(parent, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        columns = ('line', 'time', 'code', 'dates', 'first_date', 'last_date')
        self.tree = ttk.Treeview(
            parent, 
            columns=columns,
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            selectmode='browse',
            height=20
        )
        
        # 配置滚动条
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # 定义列
        self.tree.column('#0', width=0, stretch=tk.NO)  # 隐藏第一列
        self.tree.column('line', width=50, anchor=tk.CENTER, minwidth=40)
        self.tree.column('time', width=180, anchor=tk.W, minwidth=150)
        self.tree.column('code', width=80, anchor=tk.CENTER, minwidth=60)
        self.tree.column('dates', width=60, anchor=tk.CENTER, minwidth=50)
        self.tree.column('first_date', width=100, anchor=tk.CENTER, minwidth=80)
        self.tree.column('last_date', width=100, anchor=tk.CENTER, minwidth=80)
        
        # 定义列标题
        self.tree.heading('line', text='行号', anchor=tk.CENTER)
        self.tree.heading('time', text='时间戳', anchor=tk.W)
        self.tree.heading('code', text='代码', anchor=tk.CENTER)
        self.tree.heading('dates', text='日期数', anchor=tk.CENTER)
        self.tree.heading('first_date', text='最早日期', anchor=tk.CENTER)
        self.tree.heading('last_date', text='最晚日期', anchor=tk.CENTER)
        
        # 绑定点击事件
        self.tree.bind('<<TreeviewSelect>>', self.on_item_select)
        
        # 绑定双击事件
        self.tree.bind('<Double-Button-1>', self.on_item_double_click)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    def create_right_panel(self, parent):
        """创建右侧K线图面板"""
        right_frame = tk.Frame(parent, bg=self.right_panel_bg, relief=tk.RAISED, bd=1)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 标题和控制区域
        self.create_right_header(right_frame)
        
        # 详细信息区域
        self.create_detail_area(right_frame)
        
        # K线图容器
        self.create_chart_area(right_frame)
        
        # 控制按钮区域
        self.create_control_area(right_frame)
    
    def create_right_header(self, parent):
        """创建右侧标题区域"""
        header_frame = tk.Frame(parent, bg=self.right_panel_bg)
        header_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.right_title = ttk.Label(header_frame, text="K线图区域", font=('Arial', 12, 'bold'))
        self.right_title.pack(side=tk.LEFT)
        
        # 扩展控制区域
        extend_frame = tk.Frame(header_frame, bg=self.right_panel_bg)
        extend_frame.pack(side=tk.RIGHT)
        
        # 扩展天数选择
        ttk.Label(extend_frame, text="扩展天数:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.extend_days_var = tk.IntVar(value=20)
        extend_spinbox = ttk.Spinbox(
            extend_frame, 
            from_=0, 
            to=100, 
            textvariable=self.extend_days_var, 
            width=5
        )
        extend_spinbox.pack(side=tk.LEFT, padx=2)
        
        # 日期范围选择
        date_frame = tk.Frame(header_frame, bg=self.right_panel_bg)
        date_frame.pack(side=tk.RIGHT, padx=20)
        
        ttk.Label(date_frame, text="基准区间:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 开始日期
        self.start_date_var = tk.StringVar(value="20240101")
        start_entry = ttk.Entry(date_frame, textvariable=self.start_date_var, width=10)
        start_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(date_frame, text="至").pack(side=tk.LEFT, padx=2)
        
        # 结束日期
        self.end_date_var = tk.StringVar(value=datetime.now().strftime("%Y%m%d"))
        end_entry = ttk.Entry(date_frame, textvariable=self.end_date_var, width=10)
        end_entry.pack(side=tk.LEFT, padx=2)
    
    def create_detail_area(self, parent):
        """创建详细信息区域"""
        detail_frame = tk.Frame(parent, bg=self.right_panel_bg)
        detail_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.detail_label = ttk.Label(
            detail_frame, 
            text="请点击左侧的数据行查看详情并加载K线图",
            wraplength=500
        )
        self.detail_label.pack(side=tk.LEFT, anchor=tk.W)
    
    def create_chart_area(self, parent):
        """创建K线图容器"""
        # 主容器
        self.chart_container = tk.Frame(parent, bg=self.right_panel_bg)
        self.chart_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 初始占位文本
        self.chart_placeholder = ttk.Label(
            self.chart_container, 
            text="K线图区域\n\n"
                 "点击左侧的股票数据行，此处将显示对应的K线图\n\n"
                 "支持鼠标悬停查看详细数据点信息\n"
                 "K线图默认聚焦在基准日期区间，前后各扩展指定天数",
            font=('Arial', 10),
            justify=tk.CENTER,
            background='white'
        )
        self.chart_placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # 图表框架
        self.chart_frame = tk.Frame(self.chart_container, bg=self.right_panel_bg)
        
        # 工具栏框架
        self.toolbar_frame = tk.Frame(self.chart_container, bg=self.right_panel_bg, height=30)
    
    def create_control_area(self, parent):
        """创建控制按钮区域"""
        button_frame = tk.Frame(parent, bg=self.right_panel_bg)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # 加载K线图按钮
        load_chart_btn = ttk.Button(
            button_frame, 
            text="加载K线图", 
            command=self.load_kline_chart
        )
        load_chart_btn.pack(side=tk.LEFT, padx=5)
        
        # 清除图表按钮
        clear_chart_btn = ttk.Button(
            button_frame, 
            text="清除图表", 
            command=self.clear_kline_chart
        )
        clear_chart_btn.pack(side=tk.LEFT, padx=5)
        
        # 显示全部范围按钮
        show_all_btn = ttk.Button(
            button_frame, 
            text="显示全部范围", 
            command=self.show_full_range
        )
        show_all_btn.pack(side=tk.LEFT, padx=5)
        
        # 聚焦基准区间按钮
        focus_base_btn = ttk.Button(
            button_frame, 
            text="聚焦基准区间", 
            command=self.focus_base_range
        )
        focus_base_btn.pack(side=tk.LEFT, padx=5)
        
        # 同花顺查看按钮
        ths_btn = ttk.Button(
            button_frame, 
            text="同花顺查看", 
            command=self.open_ths,
            style="Accent.TButton"  # 使用特殊样式突出显示
        )
        ths_btn.pack(side=tk.LEFT, padx=5)
        
        # 导出数据按钮
        export_btn = ttk.Button(button_frame, text="导出选中数据", command=self.export_selected)
        export_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def open_ths(self):
        """打开同花顺查看股票K线图"""
        code = self.selected_stock.get('code')
        if not code:
            messagebox.showinfo("提示", "请先选择一条股票数据")
            return
        
        # 获取基准日期
        start_date = self.start_date_var.get()
        end_date = self.end_date_var.get()
        
        if not start_date or not end_date:
            messagebox.showinfo("提示", "请先设置基准日期区间")
            return
        
        try:
            # 尝试多种方式打开同花顺
            self._open_ths_stock(code, start_date, end_date)
            
        except Exception as e:
            messagebox.showerror("打开同花顺错误", f"打开同花顺时出错: {str(e)}\n\n您可以手动打开同花顺，查看股票: {code}")
            self.statusbar.config(text=f"打开同花顺失败: {str(e)}")
    
    def _open_ths_stock(self, code: str, start_date: str, end_date: str):
        """打开同花顺查看股票"""
        # 格式化日期
        try:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            
            # 转换为同花顺可能使用的格式
            start_str = start_dt.strftime("%Y-%m-%d")
            end_str = end_dt.strftime("%Y-%m-%d")
        except:
            start_str = start_date
            end_str = end_date
        
        # 尝试多种方法打开同花顺
        
        # 方法1: 同花顺URL协议
        try:
            # 同花顺的URL协议格式: ths://code
            ths_url = f"ths://{code}"
            webbrowser.open(ths_url)
            self.statusbar.config(text=f"正在通过URL协议打开同花顺: {code}")
            return
        except:
            pass
        
        # 方法2: 同花顺客户端协议
        try:
            # 同花顺客户端可能支持的命令
            system = platform.system()
            
            if system == "Windows":
                # Windows系统
                ths_paths = [
                    r"C:\同花顺软件\同花顺\hexinlauncher.exe",  # 同花顺交易客户端
                    # r"C:\Program Files\同花顺\xiadan.exe",
                    # r"C:\Program Files (x86)\同花顺\xiadan.exe",
                    # r"C:\ths\xiadan.exe",
                ]
                
                for ths_path in ths_paths:
                    if os.path.exists(ths_path):
                        # 使用subprocess打开同花顺
                        cmd = [ths_path, f"code={code}"]
                        subprocess.Popen(cmd)
                        self.statusbar.config(text=f"正在打开同花顺客户端: {code}")
                        return
                
                # 如果找不到可执行文件，尝试用thssafe协议
                thssafe_url = f"thssafe://{code}"
                webbrowser.open(thssafe_url)
                self.statusbar.config(text=f"正在通过thssafe协议打开: {code}")
                return
                
            elif system == "Darwin":  # macOS
                ths_paths = [
                    "/Applications/同花顺.app",
                    "/Applications/Ths.app",
                ]
                
                for ths_path in ths_paths:
                    if os.path.exists(ths_path):
                        subprocess.Popen(["open", ths_path, "--args", f"code={code}"])
                        self.statusbar.config(text=f"正在打开macOS同花顺: {code}")
                        return
                        
            elif system == "Linux":
                # Linux系统
                ths_paths = [
                    "/opt/同花顺/同花顺",
                    "/usr/bin/同花顺",
                    "/usr/local/bin/同花顺",
                ]
                
                for ths_path in ths_paths:
                    if os.path.exists(ths_path):
                        subprocess.Popen([ths_path, f"code={code}"])
                        self.statusbar.config(text=f"正在打开Linux同花顺: {code}")
                        return
            
        except Exception as e:
            print(f"打开同花顺客户端失败: {e}")
        
        # 方法3: 同花顺网页版
        try:
            # 同花顺网页版URL
            ths_web_urls = [
                f"https://stock.10jqka.com.cn/{code}/",  # 同花顺个股页面
                f"https://q.10jqka.com.cn/{code}/",      # 同花顺行情页面
                f"https://stockpage.10jqka.com.cn/{code}/",  # 同花顺股票页面
            ]
            
            for url in ths_web_urls:
                webbrowser.open(url)
                self.statusbar.config(text=f"正在打开同花顺网页版: {code}")
                return
        except:
            pass
        
        # 方法4: 东方财富网页版（备选）
        try:
            dfcf_url = f"https://quote.eastmoney.com/{code}.html"
            webbrowser.open(dfcf_url)
            self.statusbar.config(text=f"正在打开东方财富网页版: {code} (同花顺备用)")
            return
        except:
            pass
        
        # 方法5: 雪球网页版（备选）
        try:
            xueqiu_url = f"https://xueqiu.com/S/{code}"
            webbrowser.open(xueqiu_url)
            self.statusbar.config(text=f"正在打开雪球网页版: {code} (同花顺备用)")
            return
        except:
            pass
        
        # 如果所有方法都失败，显示提示信息
        messagebox.showinfo(
            "打开同花顺", 
            f"无法自动打开同花顺，请手动操作：\n\n"
            f"股票代码: {code}\n"
            f"基准区间: {start_str} 至 {end_str}\n\n"
            f"操作建议：\n"
            f"1. 手动打开同花顺软件\n"
            f"2. 输入股票代码 {code}\n"
            f"3. 在K线图中定位到 {start_str} 至 {end_str} 区间"
        )
        
        # 将股票信息复制到剪贴板
        try:
            import pyperclip
            pyperclip.copy(f"{code} {start_str} {end_str}")
            self.statusbar.config(text=f"股票信息已复制到剪贴板: {code}")
        except:
            # 如果没有pyperclip，尝试使用tkinter剪贴板
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(f"{code} {start_str} {end_str}")
                self.statusbar.config(text=f"股票信息已复制到剪贴板: {code}")
            except:
                self.statusbar.config(text=f"请手动记录: 代码={code}, 区间={start_str}至{end_str}")
    
    def open_file(self):
        """打开文件对话框"""
        filepath = filedialog.askopenfilename(
            title="选择数据文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filepath:
            self.load_file(filepath)
    
    def load_file(self, filepath=None):
        """加载文件"""
        if filepath is None:
            filepath = self.default_file
        
        try:
            if not os.path.exists(filepath):
                messagebox.showwarning("文件不存在", f"文件不存在: {filepath}")
                return
            
            self.statusbar.config(text=f"正在加载文件: {os.path.basename(filepath)}...")
            self.root.update()
            
            # 解析文件
            self.parser = ListFileParser(filepath)
            self.current_data = self.parser.parse_file()
            
            if not self.current_data:
                messagebox.showinfo("无数据", "文件为空或解析失败")
                self.statusbar.config(text="无数据")
                return
            
            # 转换为DataFrame
            self.parser.to_dataframe()
            
            # 更新界面
            self.update_treeview()
            
            # 更新统计信息
            summary = self.parser.get_summary()
            stats_text = (f"记录数: {summary['parsed_lines']} | "
                         f"代码数: {summary['unique_codes']} | "
                         f"总日期数: {summary['total_dates']}")
            self.stats_label.config(text=stats_text)
            
            self.statusbar.config(text=f"已加载: {os.path.basename(filepath)} - {len(self.current_data)} 条记录")
            
        except Exception as e:
            messagebox.showerror("加载错误", f"加载文件时出错: {str(e)}")
            self.statusbar.config(text="加载失败")
    
    def refresh_data(self):
        """刷新数据"""
        if hasattr(self.parser, 'filepath') and self.parser.filepath:
            self.load_file(self.parser.filepath)
        else:
            messagebox.showinfo("提示", "请先打开一个文件")
    
    def update_treeview(self):
        """更新Treeview显示"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加新数据
        for item in self.current_data:
            dates_str = [d.strftime("%Y-%m-%d") for d in item['date_sequence']]
            first_date = dates_str[0] if dates_str else ""
            last_date = dates_str[-1] if dates_str else ""
            
            self.tree.insert('', 'end', values=(
                item['line_number'],
                item['timestamp'].strftime("%Y-%m-%d %H:%M:%S.%f"),
                item['code'],
                item['date_count'],
                first_date,
                last_date
            ))
    
    def filter_data(self, *args):
        """根据搜索框过滤数据"""
        search_text = self.search_var.get().strip().upper()
        
        if not search_text:
            # 显示所有数据
            for item in self.tree.get_children():
                self.tree.item(item, tags=())
                self.tree.detach(item)
                self.tree.reattach(item, '', 'end')
            return
        
        # 过滤显示
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if values and len(values) > 2:  # 确保有足够的列
                code = values[2]  # 代码在第3列
                if search_text in code:
                    self.tree.item(item, tags=())
                    self.tree.detach(item)
                    self.tree.reattach(item, '', 'end')
                else:
                    self.tree.detach(item)
    
    def on_item_select(self, event):
        """处理项目选择事件"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        values = self.tree.item(item_id, 'values')
        
        if values and len(values) > 2:
            line_num = values[0]
            timestamp = values[1]
            code = values[2]
            date_count = values[3]
            first_date = values[4] if len(values) > 4 else ""
            last_date = values[5] if len(values) > 5 else ""
            
            # 查找原始数据
            original_item = None
            for item in self.current_data:
                if (str(item['line_number']) == line_num and 
                    item['timestamp'].strftime("%Y-%m-%d %H:%M:%S.%f") == timestamp and
                    item['code'] == code):
                    original_item = item
                    break
            
            if original_item:
                # 更新右侧标题
                self.right_title.config(text=f"股票代码: {code}")
                
                # 获取日期序列
                dates = original_item['date_sequence']
                dates_str = [d.strftime("%Y-%m-%d") for d in dates]
                
                # 自动设置基准区间
                if dates:
                    # 将日期转换为YYYYMMDD格式
                    first_date_fmt = dates[0].strftime("%Y%m%d")
                    last_date_fmt = dates[-1].strftime("%Y%m%d")
                    
                    # 更新日期范围控件
                    self.start_date_var.set(first_date_fmt)
                    self.end_date_var.set(last_date_fmt)
                    
                    # 计算扩展后的日期范围
                    extend_days = self.extend_days_var.get()
                    first_date_dt = datetime.strptime(first_date_fmt, "%Y%m%d")
                    last_date_dt = datetime.strptime(last_date_fmt, "%Y%m%d")
                    
                    # 计算扩展后的开始和结束日期
                    extend_factor = 1.5
                    extended_start = first_date_dt - timedelta(days=int(extend_days * extend_factor))
                    extended_end = last_date_dt + timedelta(days=int(extend_days * extend_factor))
                    
                    # 确保结束日期不晚于今天
                    today = datetime.now()
                    if extended_end > today:
                        extended_end = today
                
                # 更新详细信息
                detail_text = (f"行号: {line_num}\n"
                              f"时间: {timestamp}\n"
                              f"代码: {code}\n"
                              f"日期数量: {date_count}\n"
                              f"基准区间: {first_date_fmt if dates else ''} 至 {last_date_fmt if dates else ''}\n"
                              f"扩展天数: {self.extend_days_var.get()}\n"
                              f"显示焦点: 默认聚焦基准区间\n\n"
                              f"点击'同花顺查看'按钮可在同花顺中查看此股票")
                self.detail_label.config(text=detail_text)
                
                # 保存选中的信息
                self.selected_stock = {
                    'code': code,
                    'dates': dates_str,
                    'line_data': original_item
                }
                
                # 更新状态栏
                self.statusbar.config(text=f"已选择: {code} (行号: {line_num}, 日期数: {date_count})")
    
    def on_item_double_click(self, event):
        """处理项目双击事件 - 自动加载K线图"""
        self.on_item_select(event)  # 先更新选择
        self.load_kline_chart()  # 然后加载K线图
    
    def load_kline_chart(self):
        """加载K线图"""
        code = self.selected_stock.get('code')
        if not code:
            messagebox.showinfo("提示", "请先选择一条股票数据")
            return
        
        try:
            # 获取参数
            base_start_date = self.start_date_var.get()
            base_end_date = self.end_date_var.get()
            extend_days = self.extend_days_var.get()
            
            # 验证日期格式
            try:
                datetime.strptime(base_start_date, "%Y%m%d")
                datetime.strptime(base_end_date, "%Y%m%d")
            except ValueError:
                messagebox.showerror("日期格式错误", "日期格式应为YYYYMMDD，例如：20240101")
                return
            
            # 设置扩展天数
            self.chart_manager.extend_days = extend_days
            
            self.statusbar.config(text=f"正在加载 {code} 的K线图，聚焦基准区间...")
            self.root.update()
            
            # 清除之前的图表
            self.clear_kline_chart()
            
            # 隐藏占位符
            self.chart_placeholder.place_forget()
            
            # 显示图表框架
            self.chart_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建带扩展的K线图
            fig, axlist = self.chart_manager.create_kline_chart_with_extension(
                code, base_start_date, base_end_date
            )
            
            # 创建Canvas
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            
            # 创建工具栏
            toolbar = NavigationToolbar2Tk(canvas, self.toolbar_frame)
            toolbar.update()
            self.toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
            
            # 显示Canvas
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # 保存引用
            self.chart_manager.current_figure = fig
            self.chart_manager.current_canvas = canvas
            self.chart_manager.current_toolbar = toolbar
            self.chart_manager.current_axlist = axlist
            
            self.statusbar.config(
                text=f"已加载 {code} 的K线图 (基准区间: {base_start_date}-{base_end_date}, 扩展{extend_days}天, 聚焦基准区间)"
            )
            
        except Exception as e:
            messagebox.showerror("加载K线图错误", f"加载K线图时出错: {str(e)}")
            self.statusbar.config(text="K线图加载失败")
            # 显示占位符
            self.chart_placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    
    def clear_kline_chart(self):
        """清除K线图"""
        # 清除图表管理器
        self.chart_manager.clear_chart()
        
        # 清除界面元素
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        for widget in self.toolbar_frame.winfo_children():
            widget.destroy()
        
        # 隐藏图表框架
        self.chart_frame.pack_forget()
        self.toolbar_frame.pack_forget()
        
        # 显示占位符
        self.chart_placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        self.statusbar.config(text="已清除K线图")
    
    def show_full_range(self):
        """显示全部数据范围"""
        if not self.chart_manager.current_figure or not self.chart_manager.current_axlist:
            messagebox.showinfo("提示", "请先加载K线图")
            return
        
        try:
            ax_kline = self.chart_manager.current_axlist[0]
            ax_volume = self.chart_manager.current_axlist[2] if len(self.chart_manager.current_axlist) > 2 else None
            
            # 重置x轴范围，显示全部数据
            if self.chart_manager.plot_df is not None:
                total_days = len(self.chart_manager.plot_df)
                ax_kline.set_xlim(-0.5, total_days - 0.5)
                
                if ax_volume is not None:
                    ax_volume.set_xlim(-0.5, total_days - 0.5)
            
            # 重绘图表
            self.chart_manager.current_canvas.draw()
            self.statusbar.config(text="已显示全部数据范围")
            
        except Exception as e:
            messagebox.showerror("错误", f"显示全部范围时出错: {str(e)}")
    
    def focus_base_range(self):
        """重新聚焦到基准区间"""
        if not self.chart_manager.current_figure or not self.chart_manager.current_axlist:
            messagebox.showinfo("提示", "请先加载K线图")
            return
        
        try:
            ax_kline = self.chart_manager.current_axlist[0]
            ax_volume = self.chart_manager.current_axlist[2] if len(self.chart_manager.current_axlist) > 2 else None
            
            if hasattr(self.chart_manager, 'base_start_idx') and hasattr(self.chart_manager, 'base_end_idx'):
                # 计算显示范围：基准区间前后各保留30%的空间
                total_days = len(self.chart_manager.plot_df) if self.chart_manager.plot_df is not None else 0
                buffer = int(total_days * 0.3)
                xlim_start = max(0, self.chart_manager.base_start_idx - buffer)
                xlim_end = min(total_days - 1, self.chart_manager.base_end_idx + buffer)
                
                # 设置K线图的x轴范围
                ax_kline.set_xlim(xlim_start - 0.5, xlim_end + 0.5)
                
                # 设置成交量图的x轴范围
                if ax_volume is not None:
                    ax_volume.set_xlim(xlim_start - 0.5, xlim_end + 0.5)
                
                # 重绘图表
                self.chart_manager.current_canvas.draw()
                self.statusbar.config(text="已重新聚焦到基准区间")
            else:
                messagebox.showinfo("提示", "未找到基准区间信息")
            
        except Exception as e:
            messagebox.showerror("错误", f"聚焦基准区间时出错: {str(e)}")
    
    def export_selected(self):
        """导出选中的数据"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择要导出的数据")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="保存数据",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            # 收集选中的数据
            selected_data = []
            for item_id in selection:
                values = self.tree.item(item_id, 'values')
                if values:
                    # 查找对应的原始数据
                    for item in self.current_data:
                        if (str(item['line_number']) == values[0] and 
                            item['code'] == values[2]):
                            selected_data.append(item)
                            break
            
            if not selected_data:
                messagebox.showwarning("警告", "未找到选中的数据")
                return
            
            # 保存到CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入标题
                writer.writerow(['行号', '时间戳', '代码', '日期数量', '日期序列', '原始数据'])
                # 写入数据
                for item in selected_data:
                    dates_str = ','.join([d.strftime("%Y-%m-%d") for d in item['date_sequence']])
                    writer.writerow([
                        item['line_number'],
                        item['timestamp'].strftime("%Y-%m-%d %H:%M:%S.%f"),
                        item['code'],
                        item['date_count'],
                        dates_str,
                        item['original_line']
                    ])
            
            messagebox.showinfo("导出成功", f"已导出 {len(selected_data)} 条数据到:\n{filepath}")
            self.statusbar.config(text=f"已导出 {len(selected_data)} 条数据")
            
        except Exception as e:
            messagebox.showerror("导出错误", f"导出数据时出错: {str(e)}")
    
    def run(self):
        """运行应用程序"""
        # 尝试自动加载默认文件
        if os.path.exists(self.default_file):
            self.load_file()
        
        self.root.mainloop()


def main():
    """主函数"""
    root = tk.Tk()
    app = StockDataGUI(root)
    app.run()


if __name__ == "__main__":
    main()