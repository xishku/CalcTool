#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
K线图查看器优化版
专注于K线图绘制和显示，与其他模块功能解耦
"""

import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import mplcursors
import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import simpledialog, messagebox
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, FuncFormatter
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import time
import warnings
warnings.filterwarnings('ignore')


class KLineViewerOptimized:
    """K线图表查看器类 - 精简优化版本"""
    
    def __init__(self, parent=None, stock_code="000001", start_date="20230101", end_date="20231231", 
                 target_date=None, is_embedded=False, display_days=30):
        """
        初始化K线查看器
        
        Args:
            parent: 父窗口，如果为None则创建独立窗口
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            target_date: 默认定位的目标日期
            is_embedded: 是否为嵌入模式
            display_days: 显示天数
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
        
        # 控制面板相关
        self.control_frame = None
        self.date_label = None
        
        # 状态相关
        self.move_days_last_time = 0
        
        # 显示用的股票代码
        self.display_stock_code = stock_code
    
    def _create_simple_kline_data(self):
        """创建简单的K线图数据（用于测试或演示）"""
        try:
            # 解析日期
            from datetime import datetime, timedelta
            start_dt = datetime.strptime(self.start_date, "%Y%m%d")
            end_dt = datetime.strptime(self.end_date, "%Y%m%d")
            
            # 确保开始日期不晚于结束日期
            if start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt
            
            # 生成日期范围
            date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
            
            if len(date_range) == 0:
                return pd.DataFrame()
            
            # 使用股票代码作为随机种子
            seed = sum(ord(c) for c in str(self.stock_code))
            np.random.seed(seed)
            
            # 生成随机价格数据
            days = len(date_range)
            base_price = 10.0 + (seed % 100) / 10.0
            returns = np.random.randn(days) * 0.02
            price = base_price * np.exp(np.cumsum(returns))
            
            # 生成OHLCV数据
            data = pd.DataFrame({
                'Open': price * (1 + np.random.randn(days) * 0.01),
                'High': price * (1 + np.abs(np.random.randn(days)) * 0.02 + 0.02),
                'Low': price * (1 - np.abs(np.random.randn(days)) * 0.02 - 0.02),
                'Close': price * (1 + np.random.randn(days) * 0.01),
                'Volume': np.random.randint(10000, 100000, days)
            }, index=date_range)
            
            # 确保价格合理
            data['Open'] = data['Open'].clip(lower=0.1)
            data['High'] = data['High'].clip(lower=data['Open'] * 1.01)
            data['Low'] = data['Low'].clip(upper=data['Open'] * 0.99)
            data['Close'] = data['Close'].clip(lower=0.1)
            
            # 添加日期列
            data['date'] = [d.strftime('%Y%m%d') for d in date_range]
            data['Date'] = date_range
            
            return data
            
        except Exception as e:
            print(f"[KLine] 创建测试数据时出错: {str(e)}")
            return pd.DataFrame()
    
    def load_data(self, external_data=None):
        """
        加载股票数据
        
        参数:
            external_data: 外部提供的数据，格式为DataFrame
                         如果为None，则使用演示数据
        """
        try:
            if external_data is not None and not external_data.empty:
                # 使用外部提供的数据
                self.df = external_data.copy()
                print(f"[KLine] 使用外部数据，共{len(self.df)}条记录")
                
                # 确保有必要的列
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Date']
                for col in required_columns:
                    if col not in self.df.columns:
                        if col == 'Date':
                            if 'date' in self.df.columns:
                                self.df['Date'] = pd.to_datetime(self.df['date'], errors='coerce')
                            else:
                                self.df['Date'] = pd.date_range(start='2023-01-01', periods=len(self.df))
                        elif col in ['Open', 'High', 'Low', 'Close']:
                            # 生成模拟价格
                            base = 10.0
                            self.df[col] = [base + np.random.random() * 10 for _ in range(len(self.df))]
                        elif col == 'Volume':
                            self.df['Volume'] = 100000
                
                # 确保Date列是datetime类型
                if not pd.api.types.is_datetime64_any_dtype(self.df['Date']):
                    self.df['Date'] = pd.to_datetime(self.df['Date'], errors='coerce')
                
                # 删除无效日期
                self.df = self.df.dropna(subset=['Date'])
                self.df = self.df.sort_values('Date')
                
            else:
                # 使用演示数据
                print(f"[KLine] 生成演示数据: {self.stock_code}")
                self.df = self._create_simple_kline_data()
            
            if self.df is None or self.df.empty:
                print("[KLine] 错误: 没有可用的数据")
                return False
            
            # 获取日期范围字符串
            if 'date' in self.df.columns and not self.df['date'].isna().all():
                self.start_date_str = str(self.df['date'].iloc[0]) if len(self.df) > 0 else ""
                self.end_date_str = str(self.df['date'].iloc[-1]) if len(self.df) > 0 else ""
            else:
                self.start_date_str = self.df['Date'].iloc[0].strftime('%Y%m%d') if len(self.df) > 0 else ""
                self.end_date_str = self.df['Date'].iloc[-1].strftime('%Y%m%d') if len(self.df) > 0 else ""
            
            print(f"[KLine] 数据加载完成: {len(self.df)} 条记录")
            print(f"[KLine] 日期范围: {self.start_date_str} 到 {self.end_date_str}")
            
            return True
            
        except Exception as e:
            print(f"[KLine] 数据加载失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
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
            # 查找对应日期
            row = None
            for i, date_val in enumerate(self.current_display_df['date'] if 'date' in self.current_display_df.columns 
                                        else self.current_display_df['Date']):
                if str(date_val) == date_str:
                    row = self.current_display_df.iloc[i]
                    break
            
            if row is None:
                return
            
            # 计算涨跌幅
            if i > 0:
                prev_close = self.current_display_df.iloc[i-1]['Close']
                change_pct = (row['Close'] - prev_close) / prev_close * 100
            else:
                change_pct = 0
            
            # 准备注释文本
            date_display = row['Date'].strftime('%Y-%m-%d') if hasattr(row['Date'], 'strftime') else str(row['Date'])
            text = (f"日期: {date_display}\n"
                    f"开盘: {row['Open']:.2f}\n"
                    f"最高: {row['High']:.2f}\n"
                    f"最低: {row['Low']:.2f}\n"
                    f"收盘: {row['Close']:.2f}\n"
                    f"涨跌: {change_pct:+.2f}%")
            
            if 'Volume' in row:
                text += f"\n成交量: {int(row['Volume']):,}"
            
            # 如果是光标触发的，返回文本
            if is_cursor:
                return text
            
            # 创建注释
            bbox_props = dict(boxstyle="round,pad=0.3", facecolor="lightyellow", 
                             edgecolor="black", linewidth=1, alpha=0.9)
            
            # 调整注释位置
            y_lim = ax.get_ylim()
            x_lim = ax.get_xlim()
            
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
            print(f"[KLine] 显示注释出错: {e}")
    
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
                    # 只处理蜡烛矩形
                    if not date_str.endswith('_MA'):
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
        
        # 显示简单信息
        if len(self.current_display_df) > 0:
            first_date = self.current_display_df.iloc[0]['Date']
            last_date = self.current_display_df.iloc[-1]['Date']
            first_str = first_date.strftime('%Y-%m-%d') if hasattr(first_date, 'strftime') else str(first_date)
            last_str = last_date.strftime('%Y-%m-%d') if hasattr(last_date, 'strftime') else str(last_date)
            
            text = f"显示 {len(self.current_display_df)} 个交易日\n日期范围: {first_str} 到 {last_str}"
            sel.annotation.set_text(text)
            sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightblue',
                                               edgecolor='blue', linewidth=1)
    
    def _locate_to_date(self):
        """弹出对话框让用户输入日期，然后定位到该日期"""
        if not self.df or len(self.df) == 0:
            messagebox.showinfo("提示", "没有可用的数据")
            return
        
        # 获取根窗口
        if self.parent:
            root = self.parent.winfo_toplevel()
        else:
            root = tk.Tk()
            root.withdraw()
        
        # 获取可用的日期范围
        first_date = self.df.iloc[0]['Date']
        last_date = self.df.iloc[-1]['Date']
        first_str = first_date.strftime('%Y-%m-%d') if hasattr(first_date, 'strftime') else str(first_date)
        last_str = last_date.strftime('%Y-%m-%d') if hasattr(last_date, 'strftime') else str(last_date)
        
        date_str = simpledialog.askstring("定位到日期", 
                                         f"请输入日期 (YYYY-MM-DD 或 YYYYMMDD)\n可用日期范围: {first_str} 到 {last_str}",
                                         parent=root)
        
        if date_str is None or date_str.strip() == "":
            return
        
        try:
            # 尝试解析日期
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
                    date_val = self.current_display_df.iloc[highlight_idx_in_display]['Date']
                    date_str = date_val.strftime('%Y%m%d') if hasattr(date_val, 'strftime') else str(date_val)
                    x_pos = highlight_idx_in_display
                    y_pos = self.current_display_df.iloc[highlight_idx_in_display]['Close']
                    self._show_annotation_for_date(date_str, x_pos, y_pos, self.ax1)
                
        except Exception as e:
            messagebox.showerror("错误", f"日期格式错误: {e}\n请使用 YYYY-MM-DD 或 YYYYMMDD 格式")
    
    def _refresh_chart(self, highlight_idx=None, is_locate=False, locate_date_str="", min_diff=0):
        """刷新图表显示"""
        if self.df is None or len(self.df) == 0:
            print("[KLine] 错误: 没有可用的数据")
            return
        
        # 初始化显示起始位置
        if not hasattr(self, '_current_display_start'):
            self._current_display_start = max(0, len(self.df) - self.display_days)
        
        # 计算显示范围
        if highlight_idx is not None:
            if highlight_idx < 0:
                highlight_idx = 0
            elif highlight_idx >= len(self.df):
                highlight_idx = len(self.df) - 1
            
            display_start = max(0, highlight_idx - self.display_days // 2)
            self._current_display_start = display_start
        
        self.current_display_start = self._current_display_start
        display_end = min(len(self.df), self.current_display_start + self.display_days)
        
        # 确保至少显示10天
        if display_end - self.current_display_start < 10:
            self.current_display_start = max(0, len(self.df) - self.display_days)
            display_end = len(self.df)
            self._current_display_start = self.current_display_start
        
        # 获取显示数据
        self.current_display_df = self.df.iloc[self.current_display_start:display_end].copy()
        self.current_highlight_idx = highlight_idx
        
        # 清空图形
        self.fig.clear()
        self.date_to_patch_map.clear()
        
        # 移除之前的注释
        if self.current_annotation is not None:
            self.current_annotation = None
        
        # 创建子图
        self.ax1 = plt.subplot2grid((6, 1), (0, 0), rowspan=4, fig=self.fig)
        self.ax2 = plt.subplot2grid((6, 1), (4, 0), rowspan=2, sharex=self.ax1, fig=self.fig)
        
        # 设置标题
        if is_locate:
            if min_diff > 0:
                actual_date = self.df.iloc[highlight_idx]['Date']
                actual_str = actual_date.strftime('%Y-%m-%d') if hasattr(actual_date, 'strftime') else str(actual_date)
                title = f'{self.display_stock_code} 日K线 - 定位到: {actual_str} (输入: {locate_date_str}, 相差{min_diff}天)'
            else:
                title = f'{self.display_stock_code} 日K线 - 定位到: {locate_date_str}'
        else:
            title = f'{self.display_stock_code} 日K线 ({self.start_date_str} 至 {self.end_date_str})'
        
        self.ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 准备数据 - 使用整数索引确保日期连续
        plot_dates = np.arange(len(self.current_display_df))
        
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
            date_str = str(row['date']) if 'date' in row else str(date)
            
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
        
        # 添加移动平均线
        for period in [5, 10, 20]:
            if len(self.current_display_df) >= period:
                ma_values = self.current_display_df['Close'].rolling(window=period, min_periods=1).mean()
                ma_line, = self.ax1.plot(plot_dates, ma_values, color=f'C{period//5}', 
                                      linewidth=1.5, label=f'MA{period}', alpha=0.7, zorder=1)
        
        # 绘制成交量
        if 'Volume' in self.current_display_df.columns:
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
                    if hasattr(date_obj, 'strftime'):
                        tick_labels.append(date_obj.strftime('%m-%d'))
                    else:
                        tick_labels.append(str(date_obj)[5:10])  # 取MM-DD部分
            
            self.ax1.set_xticks(plot_dates[tick_indices])
            self.ax1.set_xticklabels(tick_labels, fontsize=9)
            self.ax2.set_xticks(plot_dates[tick_indices])
            self.ax2.set_xticklabels(tick_labels, fontsize=9)
        
        # 设置Y轴格式
        self.ax1.yaxis.set_major_formatter(FuncFormatter(self._format_y_axis))
        self.ax1.yaxis.set_major_locator(MaxNLocator(prune='both', nbins=8))
        
        # 添加Y轴标签
        self.ax1.set_ylabel('价格', fontsize=10)
        self.ax2.set_ylabel('成交量', fontsize=10)
        
        # 添加图例
        self.ax1.legend(loc='upper left', fontsize=9)
        
        # 添加日期范围说明
        if len(self.current_display_df) > 0:
            first_date = self.current_display_df.iloc[0]['Date']
            last_date = self.current_display_df.iloc[-1]['Date']
            first_str = first_date.strftime('%Y-%m-%d') if hasattr(first_date, 'strftime') else str(first_date)
            last_str = last_date.strftime('%Y-%m-%d') if hasattr(last_date, 'strftime') else str(last_date)
            
            date_info = f"显示日期范围: {first_str} 至 {last_str} (共{len(self.current_display_df)}个交易日)"
            self.fig.text(0.5, 0.01, date_info, ha='center', fontsize=10, 
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
        
        # 高亮标记
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
                date_display = loc_date.strftime('%Y-%m-%d') if hasattr(loc_date, 'strftime') else str(loc_date)
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
        print(f"[KLine] 图表已刷新，显示 {len(self.current_display_df)} 个交易日的数据")
        
        # 显示高亮日期的注释
        if highlight_idx_in_display is not None:
            date_val = self.current_display_df.iloc[highlight_idx_in_display]['Date']
            date_str = date_val.strftime('%Y%m%d') if hasattr(date_val, 'strftime') else str(date_val)
            x_pos = highlight_idx_in_display
            y_pos = self.current_display_df.iloc[highlight_idx_in_display]['Close']
            self._show_annotation_for_date(date_str, x_pos, y_pos, self.ax1)
    
    def _on_key_press(self, event):
        """键盘事件处理"""
        # 防按键过快
        current_time = time.time()
        if current_time - self.move_days_last_time < 0.1:
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
        if self.df is None or len(self.df) == 0:
            return
        
        if not hasattr(self, '_current_display_start'):
            self._current_display_start = max(0, len(self.df) - self.display_days)
        
        if self.current_highlight_idx is None:
            self.current_highlight_idx = self._current_display_start + self.display_days // 2
        
        new_idx = self.current_highlight_idx + days
        if 0 <= new_idx < len(self.df):
            self.current_highlight_idx = new_idx
            self._refresh_chart(highlight_idx=new_idx)
    
    def _create_control_panel(self, parent):
        """创建简化控制面板"""
        self.control_frame = tk.Frame(parent, bg="#f0f0f0", height=40)
        self.control_frame.pack(fill=tk.X, pady=(0, 5))
        self.control_frame.pack_propagate(False)
        
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
                              bg="#4a6fa5", fg="white", padx=10, font=('Arial', 9))
        locate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 日期显示标签
        self.date_label = tk.Label(left_frame, text="", bg="#f0f0f0", fg="#d9534f", 
                                  font=('Arial', 10, 'bold'))
        self.date_label.pack(side=tk.LEFT)
    
    def show_embedded(self, container, external_data=None):
        """
        显示嵌入的图表
        
        参数:
            container: 容器控件
            external_data: 外部数据，可选
            
        返回:
            bool: 显示是否成功
        """
        try:
            print(f"[KLine] 开始显示K线图: {self.stock_code}")
            
            # 确保容器存在
            if container is None:
                print("[KLine] 错误: 容器为None")
                return False
            
            # 清除容器中的现有内容
            for widget in container.winfo_children():
                widget.destroy()
            
            # 创建Matplotlib图形
            self.fig = plt.figure(figsize=(10, 7), dpi=100)
            
            # 创建Canvas
            self.canvas = FigureCanvasTkAgg(self.fig, master=container)
            self.canvas.draw()
            
            # 绑定键盘事件
            self.canvas.mpl_connect('key_press_event', self._on_key_press)
            
            # 将Canvas打包
            self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 加载数据
            if not self.load_data(external_data):
                # 显示错误信息
                error_label = tk.Label(container, 
                                     text=f"无法显示K线图: 数据加载失败\n股票: {self.stock_code}",
                                     font=('Arial', 12),
                                     foreground="#ff0000")
                error_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
                return False
            
            # 确定初始高亮索引
            initial_highlight_idx = None
            
            if self.target_date:
                # 查找目标日期
                try:
                    target_date = pd.to_datetime(self.target_date, format='%Y%m%d')
                    date_idx = None
                    min_diff = None
                    
                    for i, dt in enumerate(self.df['Date']):
                        diff = abs((dt - target_date).days)
                        if min_diff is None or diff < min_diff:
                            min_diff = diff
                            date_idx = i
                    
                    if date_idx is not None:
                        initial_highlight_idx = date_idx
                except:
                    initial_highlight_idx = len(self.df) - 1
            else:
                # 默认显示最近的数据
                initial_highlight_idx = len(self.df) - 1
            
            # 初始绘制
            is_locate = bool(self.target_date)
            self._refresh_chart(highlight_idx=initial_highlight_idx, is_locate=is_locate, 
                              locate_date_str=self.target_date or "", min_diff=0)
            
            print(f"[KLine] K线图显示成功: {self.stock_code}")
            return True
            
        except Exception as e:
            print(f"[KLine] 异常: 显示K线图时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def close(self):
        """关闭K线图"""
        try:
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
            if self.fig:
                plt.close(self.fig)
            
            self.fig = None
            self.canvas = None
            self.df = None
            
            print("[KLine] K线图已关闭")
            
        except Exception as e:
            print(f"[KLine] 警告: 关闭K线图时出错: {str(e)}")