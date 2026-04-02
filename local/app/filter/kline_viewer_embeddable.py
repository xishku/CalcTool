#!/usr/bin/python
#-*-coding:UTF-8-*-

import os
import sys
import argparse
import re
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import numpy as np
import datetime
import mplcursors
import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, FuncFormatter
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import time

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent

def normalize_stock_code(stock_code):
    """标准化股票代码格式"""
    if not stock_code:
        return stock_code
    
    # 移除所有非数字字符
    code = re.sub(r'[^0-9]', '', str(stock_code))
    
    # 补齐到6位
    if code.isdigit():
        return code.zfill(6)
    
    return stock_code

class KLineViewerEmbeddable:
    """可嵌入的K线图表查看器类"""
    
    def __init__(self, parent=None, stock_code="601398", start_date="20260101", end_date="20260401", 
                 target_date=None, display_days=30, is_embedded=False):
        """
        初始化K线查看器
        
        Args:
            parent: 父窗口，如果为None则创建独立窗口
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            target_date: 默认定位的目标日期
            display_days: 显示天数
            is_embedded: 是否为嵌入模式
        """
        self.parent = parent
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.target_date = target_date
        self.display_days = display_days
        self.is_embedded = is_embedded
        
        # 数据相关
        self.df = None
        self.start_date_str = ""
        self.end_date_str = ""
        
        # 显示相关
        self.current_display_df = None
        self.current_display_start = 0
        self.current_highlight_idx = None
        
        # 图表相关
        self.fig = None
        self.ax1 = None
        self.ax2 = None
        self.canvas = None
        self.toolbar = None
        self.cursor = None
        self.date_to_patch_map = {}
        self.current_annotation = None
        
        # GUI相关
        self.window = None
        self.control_frame = None
        self.date_label = None
        
        # 状态相关
        self.move_days_last_time = 0
        
        # 显示用的股票代码
        self.display_stock_code = stock_code
    
    def create_window(self):
        """创建独立窗口"""
        self.window = tk.Tk()
        self.window.title(f"K线图 - {self.stock_code}")
        self.window.geometry("1200x800")
        
        # 绑定窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        
        # 创建主框架
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建控制面板
        self.create_control_panel(main_frame)
        
        # 创建图表区域
        self.create_chart_area(main_frame)
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        self.control_frame = tk.Frame(parent, bg="#f0f0f0", height=40)
        self.control_frame.pack(fill=tk.X, pady=(0, 5))
        self.control_frame.pack_propagate(False)  # 保持固定高度
        
        # 左对齐控件
        left_frame = tk.Frame(self.control_frame, bg="#f0f0f0")
        left_frame.pack(side=tk.LEFT, padx=10)
        
        # 股票信息
        tk.Label(left_frame, text=f"股票代码: {self.display_stock_code}", 
                bg="#f0f0f0", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 20))
        
        # 日期范围
        date_range = f"日期范围: {self.start_date} 到 {self.end_date}"
        tk.Label(left_frame, text=date_range, bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 20))
        
        # 定位按钮
        locate_btn = tk.Button(left_frame, text="定位到日期", command=self._locate_to_date,
                              bg="#4a6fa5", fg="white", padx=10)
        locate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 日期显示标签
        self.date_label = tk.Label(left_frame, text="", bg="#f0f0f0", fg="#d9534f", 
                                  font=('Arial', 10, 'bold'))
        self.date_label.pack(side=tk.LEFT)
        
        # 右对齐控件
        right_frame = tk.Frame(self.control_frame, bg="#f0f0f0")
        right_frame.pack(side=tk.RIGHT, padx=10)
        
        # 操作说明
        tk.Label(right_frame, text="操作: G键定位 | ←→键浏览 | 鼠标悬停查看详情", 
                bg="#f0f0f0", fg="#666666").pack(side=tk.RIGHT)
    
    def create_chart_area(self, parent):
        """创建图表区域"""
        # 创建Matplotlib图形
        self.fig = plt.figure(figsize=(12, 8), dpi=100)
        
        # 创建Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        
        # 创建工具栏
        self.toolbar = NavigationToolbar2Tk(self.canvas, parent)
        self.toolbar.update()
        
        # 将Canvas和Toolbar打包
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 绑定键盘事件
        self.canvas.mpl_connect('key_press_event', self._on_key_press)
    
    def embed_in_frame(self, parent_frame):
        """嵌入到现有框架中"""
        self.parent = parent_frame
        self.is_embedded = True
        
        # 清除父框架中的所有内容
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        # 创建控制面板
        self.create_control_panel(parent_frame)
        
        # 创建图表区域
        self.create_chart_area(parent_frame)
        
        return self
    
    def _format_y_axis(self, value, pos):
        """格式化Y轴刻度，保留适当的小数位数"""
        if value >= 1000:
            return f'{value:,.0f}'
        elif value >= 100:
            return f'{value:.1f}'
        elif value >= 10:
            return f'{value:.2f}'
        elif value >= 1:
            return f'{value:.3f}'
        else:
            return f'{value:.4f}'
    
    def _show_annotation_for_date(self, date_str, x_pos, y_pos, ax, is_cursor=False):
        """为指定日期显示注释"""
        if self.current_display_df is None or date_str is None:
            return
        
        # 如果已存在注释，先移除
        if self.current_annotation is not None:
            self.current_annotation.remove()
            self.current_annotation = None
        
        try:
            # 在显示数据中查找对应的行
            row_idx = None
            for i, date_val in enumerate(self.current_display_df['date']):
                if str(date_val) == date_str:
                    row_idx = i
                    break
            
            if row_idx is None:
                return
            
            row = self.current_display_df.iloc[row_idx]
            
            # 计算涨跌幅
            if row_idx > 0:
                prev_close = self.current_display_df.iloc[row_idx-1]['Close']
                change_pct = (row['Close'] - prev_close) / prev_close * 100
            else:
                change_pct = 0
            
            # 准备注释文本
            text = (f"日期: {date_str}\n"
                    f"开盘: {row['Open']:.2f}\n"
                    f"最高: {row['High']:.2f}\n"
                    f"最低: {row['Low']:.2f}\n"
                    f"收盘: {row['Close']:.2f}\n"
                    f"涨跌: {change_pct:+.2f}%\n"
                    f"成交量: {int(row['Volume']):,}")
            
            # 如果是光标触发的，使用光标的位置
            if is_cursor:
                return text
            
            # 否则创建新注释
            bbox_props = dict(boxstyle="round,pad=0.3", facecolor="lightyellow", 
                             edgecolor="black", linewidth=1, alpha=0.9)
            
            # 调整注释位置，避免超出图形边界
            y_lim = ax.get_ylim()
            x_lim = ax.get_xlim()
            
            # 计算最佳位置
            if y_pos > (y_lim[0] + y_lim[1]) / 2:
                va = 'top'
                y_offset = -0.05 * (y_lim[1] - y_lim[0])
            else:
                va = 'bottom'
                y_offset = 0.05 * (y_lim[1] - y_lim[0])
            
            if x_pos > (x_lim[0] + x_lim[1]) / 2:
                ha = 'right'
                x_offset = -0.05 * (x_lim[1] - x_lim[0])
            else:
                ha = 'left'
                x_offset = 0.05 * (x_lim[1] - x_lim[0])
            
            self.current_annotation = ax.text(x_pos + x_offset, y_pos + y_offset, text,
                                            fontsize=9, va=va, ha=ha,
                                            bbox=bbox_props, zorder=1000)
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"显示注释出错: {e}")
    
    def _on_add(self, sel):
        """鼠标悬停事件处理"""
        if self.current_display_df is None or len(self.current_display_df) == 0:
            return
        
        try:
            # 获取被悬停的艺术家对象
            artist = sel.artist
            
            # 查找这个艺术家对应的日期
            target_date_str = None
            for date_str, patch in self.date_to_patch_map.items():
                if patch == artist:
                    # 只处理蜡烛矩形，忽略均线
                    if not date_str.endswith('_MA5') and not date_str.endswith('_MA10') and not date_str.endswith('_MA20') and not date_str.endswith('_MA30') and not date_str.endswith('_MA60'):
                        target_date_str = date_str
                        break
            
            if target_date_str is not None:
                # 获取蜡烛的坐标
                x_pos = artist.get_x() + artist.get_width() / 2
                y_pos = artist.get_y() + artist.get_height() / 2
                
                # 获取注释文本
                text = self._show_annotation_for_date(target_date_str, x_pos, y_pos, self.ax1, is_cursor=True)
                if text:
                    sel.annotation.set_text(text)
                    sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightyellow',
                                                       edgecolor='black', linewidth=1)
                return
        
        except Exception as e:
            pass
        
        # 如果上述方法都失败，显示简单信息
        if len(self.current_display_df) > 0:
            date_str = str(self.current_display_df.iloc[0]['date'])
            last_date = str(self.current_display_df.iloc[-1]['date'])
            text = f"显示 {len(self.current_display_df)} 个交易日\n日期范围: {date_str} 到 {last_date}"
            sel.annotation.set_text(text)
            sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightblue',
                                               edgecolor='blue', linewidth=1)
    
    def _locate_to_date(self):
        """弹出对话框让用户输入日期，然后定位到该日期"""
        if self.window and not self.is_embedded:
            root = self.window
        elif self.parent:
            root = self.parent.winfo_toplevel()
        else:
            root = tk.Tk()
            root.withdraw()
        
        date_str = simpledialog.askstring("定位到日期", 
                                         f"请输入日期 (YYYY-MM-DD 或 YYYYMMDD)\n日期范围: {self.start_date_str} 到 {self.end_date_str}",
                                         parent=root)
        
        if not self.is_embedded and not self.window:
            root.destroy()
        
        if date_str is None or date_str.strip() == "":
            return
        
        try:
            # 尝试不同格式
            try:
                target_date = pd.to_datetime(date_str)
            except:
                target_date = pd.to_datetime(date_str, format='%Y%m%d')
            
            # 查找最接近的日期
            date_idx = None
            min_diff = None
            
            for i, dt in enumerate(self.df['Date']):
                diff = abs((dt - target_date).days)
                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    date_idx = i
            
            if date_idx is not None:
                self._refresh_chart(highlight_idx=date_idx, is_locate=True, 
                                 locate_date_str=date_str, min_diff=min_diff)
                # 显示该日期的注释
                highlight_idx_in_display = date_idx - self.current_display_start
                if 0 <= highlight_idx_in_display < len(self.current_display_df):
                    date_str = str(self.current_display_df.iloc[highlight_idx_in_display]['date'])
                    x_pos = highlight_idx_in_display
                    y_pos = self.current_display_df.iloc[highlight_idx_in_display]['Close']
                    self._show_annotation_for_date(date_str, x_pos, y_pos, self.ax1)
                
        except Exception as e:
            if not self.is_embedded:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("错误", f"日期格式错误: {e}\n请使用 YYYY-MM-DD 或 YYYYMMDD 格式")
                root.destroy()
            else:
                messagebox.showerror("错误", f"日期格式错误: {e}\n请使用 YYYY-MM-DD 或 YYYYMMDD 格式")
    
    def _refresh_chart(self, highlight_idx=None, is_locate=False, locate_date_str="", min_diff=0):
        """刷新图表显示"""
        if not hasattr(self, '_current_display_start'):
            self._current_display_start = max(0, len(self.df) - self.display_days)
        
        if highlight_idx is not None:
            if highlight_idx < 0:
                highlight_idx = 0
            elif highlight_idx >= len(self.df):
                highlight_idx = len(self.df) - 1
            
            display_start = max(0, highlight_idx - self.display_days // 2)
            self._current_display_start = display_start
        
        self.current_display_start = self._current_display_start
        display_end = min(len(self.df), self.current_display_start + self.display_days)
        
        if display_end - self.current_display_start < 10:
            self.current_display_start = max(0, len(self.df) - self.display_days)
            display_end = len(self.df)
            self._current_display_start = self.current_display_start
        
        # 获取显示数据
        self.current_display_df = self.df.iloc[self.current_display_start:display_end].copy()
        self.current_highlight_idx = highlight_idx
        
        # 清空图形和映射
        self.fig.clear()
        self.date_to_patch_map.clear()
        
        # 移除之前的注释
        if self.current_annotation is not None:
            self.current_annotation = None
        
        # 设置样式
        rc_params = {
            'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
            'axes.unicode_minus': False,
        }
        
        # 创建子图
        self.ax1 = plt.subplot2grid((6, 1), (0, 0), rowspan=4, fig=self.fig)
        self.ax2 = plt.subplot2grid((6, 1), (4, 0), rowspan=2, sharex=self.ax1, fig=self.fig)
        
        # 设置标题
        if is_locate:
            if min_diff > 0:
                actual_date = self.df.iloc[highlight_idx]['Date'].strftime('%Y-%m-%d')
                title = f'{self.display_stock_code} 日K线 - 定位到: {actual_date} (输入: {locate_date_str}, 相差{min_diff}天)'
            else:
                title = f'{self.display_stock_code} 日K线 - 定位到: {locate_date_str}'
        else:
            title = f'{self.display_stock_code} 日K线 ({self.start_date_str} 至 {self.end_date_str})'
        
        self.ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 准备数据 - 使用整数索引确保日期连续
        plot_dates = np.arange(len(self.current_display_df))
        dates_list = self.current_display_df['Date'].tolist()
        
        # 存储蜡烛宽度
        candle_width = 0.6
        
        # 绘制每个蜡烛
        patches = []
        for i, (idx, row) in enumerate(self.current_display_df.iterrows()):
            date = row['Date']
            open_price = row['Open']
            high = row['High']
            low = row['Low']
            close = row['Close']
            date_str = str(row['date'])
            
            # 确定颜色
            if close >= open_price:
                color = 'red'
                fill = True
            else:
                color = 'green'
                fill = True
            
            # 绘制影线
            self.ax1.plot([plot_dates[i], plot_dates[i]], [low, high], color=color, linewidth=1, zorder=2)
            
            # 绘制实体
            rect = Rectangle(
                (plot_dates[i] - candle_width/2, min(open_price, close)),
                candle_width,
                abs(close - open_price),
                facecolor=color,
                edgecolor=color,
                fill=fill,
                zorder=3
            )
            self.ax1.add_patch(rect)
            
            # 保存映射
            self.date_to_patch_map[date_str] = rect
            patches.append(rect)
        
        # 添加均线
        for period in [5, 10, 20, 30, 60]:
            if len(self.current_display_df) >= period:
                # 计算移动平均
                ma_values = []
                for i in range(len(self.current_display_df)):
                    if i >= period - 1:
                        ma = self.current_display_df['Close'].iloc[i-period+1:i+1].mean()
                    else:
                        ma = np.nan
                    ma_values.append(ma)
                
                # 绘制均线
                ma_line, = self.ax1.plot(plot_dates, ma_values, color=f'C{period//10}', 
                                      linewidth=1.5, label=f'MA{period}', alpha=0.7, zorder=1)
                
                # 将均线也添加到映射
                for i, date_str in enumerate(self.current_display_df['date']):
                    self.date_to_patch_map[f"{date_str}_MA{period}"] = ma_line
        
        # 绘制成交量
        volume_colors = []
        volume_heights = []
        for i, (idx, row) in enumerate(self.current_display_df.iterrows()):
            if row['Close'] >= row['Open']:
                volume_colors.append('red')
            else:
                volume_colors.append('green')
            volume_heights.append(row['Volume'])
        
        self.ax2.bar(plot_dates, volume_heights, width=candle_width*0.8, 
                   color=volume_colors, alpha=0.7, zorder=2)
        
        # 设置X轴刻度
        n_ticks = min(10, len(plot_dates))
        if n_ticks > 0:
            tick_indices = np.linspace(0, len(plot_dates)-1, n_ticks, dtype=int)
            tick_labels = []
            for idx in tick_indices:
                if idx < len(self.current_display_df):
                    date_obj = self.current_display_df.iloc[idx]['Date']
                    tick_labels.append(date_obj.strftime('%m-%d'))
            
            self.ax1.set_xticks(plot_dates[tick_indices])
            self.ax1.set_xticklabels(tick_labels, fontsize=9)
            self.ax2.set_xticks(plot_dates[tick_indices])
            self.ax2.set_xticklabels(tick_labels, fontsize=9)
        
        # 设置Y轴格式
        self.ax1.yaxis.set_major_formatter(FuncFormatter(self._format_y_axis))
        self.ax1.yaxis.set_major_locator(MaxNLocator(prune='both', nbins=8))
        
        # 添加Y轴标签
        self.ax1.set_ylabel('价格(元)', fontsize=10)
        self.ax2.set_ylabel('成交量', fontsize=10)
        
        # 添加图例
        self.ax1.legend(loc='upper left', fontsize=9)
        
        # 在图表最下方添加完整的日期说明
        if len(self.current_display_df) > 0:
            first_date = self.current_display_df.iloc[0]['Date'].strftime('%Y-%m-%d')
            last_date = self.current_display_df.iloc[-1]['Date'].strftime('%Y-%m-%d')
            date_info = f"显示日期范围: {first_date} 至 {last_date} (共{len(self.current_display_df)}个交易日)"
            self.fig.text(0.5, 0.01, date_info, ha='center', fontsize=10, 
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
            
            # 更新日期标签
            if self.date_label:
                if highlight_idx is not None and 0 <= highlight_idx < len(self.df):
                    highlight_date = self.df.iloc[highlight_idx]['Date'].strftime('%Y-%m-%d')
                    self.date_label.config(text=f"当前显示日期: {highlight_date}")
        
        # 添加高亮标记
        highlight_idx_in_display = None
        if highlight_idx is not None and self.current_display_start <= highlight_idx < display_end:
            highlight_idx_in_display = highlight_idx - self.current_display_start
            if 0 <= highlight_idx_in_display < len(self.current_display_df):
                loc_date = self.current_display_df.iloc[highlight_idx_in_display]['Date']
                loc_close = self.current_display_df.iloc[highlight_idx_in_display]['Close']
                
                # 添加垂直线标记
                self.ax1.axvline(x=plot_dates[highlight_idx_in_display], color='red', alpha=0.7, 
                               linestyle='--', linewidth=2, zorder=4)
                self.ax2.axvline(x=plot_dates[highlight_idx_in_display], color='red', alpha=0.7, 
                               linestyle='--', linewidth=2, zorder=4)
                
                # 添加标记点
                self.ax1.plot(plot_dates[highlight_idx_in_display], loc_close, 'ro', markersize=10, 
                            alpha=0.7, zorder=5)
                
                # 添加文本标签
                ylim = self.ax1.get_ylim()
                date_display = loc_date.strftime('%Y-%m-%d')
                self.ax1.text(plot_dates[highlight_idx_in_display], ylim[1] * 0.95, f'← {date_display}', 
                            fontsize=11, color='red', va='top', ha='left', weight='bold',
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.9),
                            zorder=6)
        
        # 设置X轴范围
        self.ax1.set_xlim(plot_dates[0] - 1, plot_dates[-1] + 1)
        self.ax2.set_xlim(plot_dates[0] - 1, plot_dates[-1] + 1)
        
        # 调整布局
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        
        # 重新连接鼠标悬停事件
        if self.cursor is not None:
            self.cursor.remove()
        self.cursor = mplcursors.cursor(patches, hover=True)
        self.cursor.connect("add", self._on_add)
        
        # 添加键盘提示
        self.fig.text(0.5, 0.96, "提示：按 G 键输入日期定位，按 ← → 键逐日浏览", 
                    ha='center', fontsize=10, color='blue',
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
        
        self.canvas.draw()
        print(f"图表已刷新，显示 {len(self.current_display_df)} 个交易日的数据")
        
        # 如果高亮了某一天，显示该日期的注释
        if highlight_idx_in_display is not None:
            date_str = str(self.current_display_df.iloc[highlight_idx_in_display]['date'])
            x_pos = highlight_idx_in_display
            y_pos = self.current_display_df.iloc[highlight_idx_in_display]['Close']
            self._show_annotation_for_date(date_str, x_pos, y_pos, self.ax1)
    
    def _on_key_press(self, event):
        """键盘事件处理"""
        # 防按键过快
        current_time = time.time()
        if current_time - self.move_days_last_time < 0.1:  # 至少间隔0.1秒
            return
        
        if event.key == 'g' or event.key == 'G':
            self._locate_to_date()
        elif event.key == 'left':
            self._move_days(-1)
            self.move_days_last_time = current_time
        elif event.key == 'right':
            self._move_days(1)
            self.move_days_last_time = current_time
    
    def _move_days(self, days):
        """移动指定天数"""
        if not hasattr(self, '_current_display_start'):
            self._current_display_start = max(0, len(self.df) - self.display_days)
        
        if self.current_highlight_idx is None:
            self.current_highlight_idx = self._current_display_start + self.display_days // 2
        
        new_idx = self.current_highlight_idx + days
        if 0 <= new_idx < len(self.df):
            self.current_highlight_idx = new_idx
            self._refresh_chart(highlight_idx=new_idx)
    
    def _find_date_index(self, target_date_str):
        """查找指定日期在数据中的索引"""
        try:
            # 尝试不同格式解析日期
            try:
                target_date = pd.to_datetime(target_date_str)
            except:
                target_date = pd.to_datetime(target_date_str, format='%Y%m%d')
            
            # 查找最接近的日期
            date_idx = None
            min_diff = None
            
            for i, dt in enumerate(self.df['Date']):
                diff = abs((dt - target_date).days)
                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    date_idx = i
            
            if date_idx is not None:
                if min_diff > 0:
                    print(f"提示: 输入的日期 {target_date_str} 没有对应数据，定位到最接近的日期 {self.df.iloc[date_idx]['Date'].strftime('%Y-%m-%d')} (相差{min_diff}天)")
                else:
                    print(f"成功定位到日期: {target_date_str}")
                return date_idx
            else:
                return None
        except Exception as e:
            print(f"日期解析错误: {e}")
            return None
    
    def load_data(self):
        """加载股票数据"""
        agent = TdxDataAgent()
        
        # 标准化股票代码
        original_code = self.stock_code
        normalized_code = normalize_stock_code(original_code)
        
        print(f"正在加载 {original_code} (标准化: {normalized_code}) 的数据，日期范围: {self.start_date} 到 {self.end_date}...")
        
        # 保存显示用的股票代码
        self.display_stock_code = original_code
        
        try:
            # 尝试不同的代码格式
            code_variants = []
            
            # 1. 标准化后的6位代码
            if normalized_code != original_code:
                code_variants.append(normalized_code)
            
            # 2. 原始代码
            code_variants.append(original_code)
            
            # 3. 如果原始代码是数字，尝试不同长度
            if original_code.isdigit():
                # 补齐到6位
                code_variants.append(original_code.zfill(6))
                # 如果是5位，可能去掉开头的0
                if len(original_code) == 5:
                    code_variants.append(original_code.lstrip('0').zfill(6))
            
            # 移除重复
            code_variants = list(dict.fromkeys(code_variants))
            
            print(f"将尝试以下股票代码格式: {code_variants}")
            
            # 尝试不同的代码格式
            last_error = None
            for code_variant in code_variants:
                try:
                    print(f"尝试代码: {code_variant}")
                    self.df = agent.read_kdata_cache(code_variant, self.start_date, self.end_date)
                    
                    if self.df is not None and not self.df.empty:
                        print(f"✓ 代码 {code_variant} 成功获取 {len(self.df)} 条数据")
                        self.stock_code = code_variant  # 更新为成功的代码
                        self.display_stock_code = f"{original_code} ({code_variant})"  # 显示信息
                        break
                    else:
                        print(f"✗ 代码 {code_variant} 无数据")
                except Exception as e:
                    last_error = e
                    print(f"✗ 代码 {code_variant} 失败: {e}")
            
            if self.df is None or self.df.empty:
                error_msg = f"无法获取股票数据\n"
                error_msg += f"原始代码: {original_code}\n"
                error_msg += f"尝试的格式: {', '.join(code_variants)}\n"
                if last_error:
                    error_msg += f"最后错误: {last_error}"
                print(error_msg)
                return False
                
            print(f"获取数据成功，共{len(self.df)}条记录")
            
            # 处理数据格式
            print("处理数据格式...")
            
            # 检查数据列
            print("数据列名:", self.df.columns.tolist())
            
            # 根据实际列名处理数据
            if 'r_open' in self.df.columns and 'r_high' in self.df.columns and 'r_low' in self.df.columns and 'r_close' in self.df.columns:
                self.df['Open'] = self.df['r_open']
                self.df['High'] = self.df['r_high']
                self.df['Low'] = self.df['r_low']
                self.df['Close'] = self.df['r_close']
                print("使用复权价格数据")
            elif 'open' in self.df.columns and 'high' in self.df.columns and 'low' in self.df.columns and 'close' in self.df.columns:
                sample_price = self.df['close'].iloc[0] if not self.df.empty else 0
                if sample_price > 1000:
                    print("检测到价格单位为分，转换为元")
                    self.df['Open'] = self.df['open'] / 100.0
                    self.df['High'] = self.df['high'] / 100.0
                    self.df['Low'] = self.df['low'] / 100.0
                    self.df['Close'] = self.df['close'] / 100.0
                else:
                    print("使用原始价格数据")
                    self.df['Open'] = self.df['open']
                    self.df['High'] = self.df['high']
                    self.df['Low'] = self.df['low']
                    self.df['Close'] = self.df['close']
            else:
                print("错误：数据中未找到价格列")
                print("可用列:", self.df.columns.tolist())
                return False
            
            # 确保价格是数值类型
            for col in ['Open', 'High', 'Low', 'Close']:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            
            # 检查是否有有效的价格数据
            if self.df[['Open', 'High', 'Low', 'Close']].isna().all().all():
                print("错误：所有价格数据均为NaN")
                return False
            
            # 处理缺失值
            for col in ['Open', 'High', 'Low', 'Close']:
                if self.df[col].isna().all():
                    print(f"警告：{col}列全为NaN，使用0填充")
                    self.df[col] = 0
                else:
                    prev_value = None
                    for i in range(len(self.df)):
                        if pd.isna(self.df.at[i, col]):
                            if prev_value is not None:
                                self.df.at[i, col] = prev_value
                        else:
                            prev_value = self.df.at[i, col]
                    
                    if self.df[col].isna().any():
                        first_valid_idx = self.df[col].first_valid_index()
                        if first_valid_idx is not None:
                            first_valid_value = self.df.at[first_valid_idx, col]
                            self.df[col] = self.df[col].fillna(first_valid_value)
            
            # 处理成交量
            if 'volume' in self.df.columns:
                self.df['Volume'] = pd.to_numeric(self.df['volume'], errors='coerce')
                if self.df['Volume'].isna().all():
                    self.df['Volume'] = 100000
                else:
                    prev_volume = None
                    for i in range(len(self.df)):
                        if pd.isna(self.df.at[i, 'Volume']):
                            if prev_volume is not None:
                                self.df.at[i, 'Volume'] = prev_volume
                        else:
                            prev_volume = self.df.at[i, 'Volume']
                    
                    if self.df['Volume'].isna().any():
                        self.df['Volume'] = self.df['Volume'].fillna(100000)
            else:
                print("警告：未找到成交量列，使用默认值")
                self.df['Volume'] = 100000
            
            # 处理日期
            if 'date' in self.df.columns:
                self.df['Date'] = pd.to_datetime(self.df['date'], format='%Y%m%d', errors='coerce')
            else:
                print("错误：未找到日期列")
                return False
            
            # 删除无效日期
            original_len = len(self.df)
            self.df = self.df.dropna(subset=['Date'])
            if len(self.df) < original_len:
                print(f"警告：删除了{original_len - len(self.df)}条无效日期记录")
            
            self.df = self.df.sort_values('Date')
            
            if len(self.df) == 0:
                print("错误：没有有效的日期数据")
                return False
            
            # 获取日期范围字符串
            self.start_date_str = str(self.df['date'].iloc[0])
            self.end_date_str = str(self.df['date'].iloc[-1])
            
            # 打印价格范围
            price_min = self.df['Close'].min()
            price_max = self.df['Close'].max()
            print(f"数据日期范围: {self.start_date_str} 到 {self.end_date_str}")
            print(f"价格范围: {price_min:.2f} 到 {price_max:.2f}")
            print(f"数据示例（前5行）:")
            print(self.df[['date', 'Open', 'High', 'Low', 'Close']].head())
            
            return True
            
        except Exception as e:
            print(f"数据加载或处理出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def show(self):
        """显示图表（独立窗口模式）"""
        if not self.load_data():
            print("数据加载失败")
            if self.window:
                self.window.destroy()
            return
        
        # 如果还没有创建窗口，创建它
        if self.window is None:
            self.create_window()
        
        # 确定初始高亮索引
        initial_highlight_idx = None
        
        if self.target_date:
            # 如果指定了目标日期，查找该日期的索引
            initial_highlight_idx = self._find_date_index(self.target_date)
            if initial_highlight_idx is not None:
                print(f"图表将默认定位到: {self.df.iloc[initial_highlight_idx]['Date'].strftime('%Y-%m-%d')}")
            else:
                print(f"警告: 无法定位到日期 {self.target_date}，将显示最近的数据")
                initial_highlight_idx = len(self.df) - 1
        else:
            # 默认显示最近的数据
            initial_highlight_idx = len(self.df) - 1
            print(f"图表默认显示最近的数据: {self.df.iloc[initial_highlight_idx]['Date'].strftime('%Y-%m-%d')}")
        
        # 初始绘制
        is_locate = bool(self.target_date)
        self._refresh_chart(highlight_idx=initial_highlight_idx, is_locate=is_locate, 
                          locate_date_str=self.target_date or "", min_diff=0)
        
        if self.window:
            self.window.mainloop()
    
    def show_embedded(self, parent_frame=None):
        """显示嵌入的图表 - 这是关键的方法！"""
        if parent_frame:
            self.embed_in_frame(parent_frame)
        
        if not self.load_data():
            print("数据加载失败")
            return False
        
        # 确定初始高亮索引
        initial_highlight_idx = None
        
        if self.target_date:
            # 如果指定了目标日期，查找该日期的索引
            initial_highlight_idx = self._find_date_index(self.target_date)
            if initial_highlight_idx is not None:
                print(f"图表将默认定位到: {self.df.iloc[initial_highlight_idx]['Date'].strftime('%Y-%m-%d')}")
            else:
                print(f"警告: 无法定位到日期 {self.target_date}，将显示最近的数据")
                initial_highlight_idx = len(self.df) - 1
        else:
            # 默认显示最近的数据
            initial_highlight_idx = len(self.df) - 1
            print(f"图表默认显示最近的数据: {self.df.iloc[initial_highlight_idx]['Date'].strftime('%Y-%m-%d')}")
        
        # 初始绘制
        is_locate = bool(self.target_date)
        self._refresh_chart(highlight_idx=initial_highlight_idx, is_locate=is_locate, 
                          locate_date_str=self.target_date or "", min_diff=0)
        
        return True
    
    def close(self):
        """关闭窗口"""
        if self.window:
            self.window.destroy()
        elif self.parent and not self.is_embedded:
            self.parent.destroy()


def main():
    """命令行入口点"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票K线图查看器')
    parser.add_argument('--stock', type=str, default='601398', help='股票代码')
    parser.add_argument('--start', type=str, default='20260101', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, default='20260401', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--target', type=str, help='默认定位到的目标日期 (YYYYMMDD 或 YYYY-MM-DD)')
    parser.add_argument('--embedded', action='store_true', help='嵌入模式')
    
    args = parser.parse_args()
    
    if args.embedded:
        print("嵌入模式，需要指定父窗口")
        return
    
    # 创建查看器并显示
    viewer = KLineViewerEmbeddable(
        stock_code=args.stock,
        start_date=args.start,
        end_date=args.end,
        target_date=args.target
    )
    
    viewer.show()


if __name__ == '__main__':
    main()