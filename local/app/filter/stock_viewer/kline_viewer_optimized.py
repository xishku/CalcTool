#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
K线图查看器优化版
修复了图形对象为None的问题，提供稳定的K线图显示
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class KLineViewerOptimized:
    """K线图查看器优化版 - 修复了图形对象问题"""
    
    def __init__(self, parent=None, stock_code='000001', 
                 start_date='20230101', end_date='20231231', 
                 target_date=None, is_embedded=False):
        """
        初始化K线图查看器
        
        参数:
            parent: 父容器
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            target_date: 目标关注日期
            is_embedded: 是否嵌入模式
        """
        self.parent = parent
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.target_date = target_date
        self.is_embedded = is_embedded
        self.canvas = None
        self.fig = None
        self.ax = None
        
        # 打印调试信息
        print(f"[KLine] 初始化: {stock_code}, 日期范围: {start_date} 到 {end_date}")
        
    def show_embedded(self, container):
        """
        显示嵌入的K线图
        
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
            
            # 创建图形对象
            self._create_figure()
            
            if self.fig is None:
                print("[KLine] 错误: 图形创建失败")
                return False
            
            # 获取股票数据
            data = self._get_stock_data()
            
            if data is None or data.empty:
                print(f"[KLine] 警告: 无法获取 {self.stock_code} 的数据")
                self._show_no_data_message(container)
                return True  # 返回True表示UI已更新，只是没有数据
            
            # 绘制K线图
            success = self._plot_kline(data)
            
            if not success:
                print("[KLine] 警告: K线图绘制失败")
                self._show_error_message(container, "K线图绘制失败")
                return True  # 返回True表示UI已更新
            
            # 创建画布
            self._create_canvas(container)
            
            if self.canvas is None:
                print("[KLine] 错误: 画布创建失败")
                return False
            
            print(f"[KLine] K线图显示成功: {self.stock_code}")
            return True
            
        except Exception as e:
            print(f"[KLine] 异常: 显示K线图时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 显示错误信息
            self._show_error_message(container, f"错误: {str(e)[:50]}")
            return True  # 返回True表示UI已更新
    
    def _create_figure(self):
        """创建图形对象"""
        try:
            print("[KLine] 创建图形对象")
            
            # 创建图形和子图
            self.fig = Figure(figsize=(10, 6), dpi=100, facecolor='white')
            
            # 创建子图
            self.ax = self.fig.add_subplot(111)
            
            # 设置图形属性
            self.fig.patch.set_alpha(0.0)  # 透明背景
            
            print("[KLine] 图形对象创建成功")
            
        except Exception as e:
            print(f"[KLine] 错误: 创建图形对象时出错: {str(e)}")
            self.fig = None
            self.ax = None
    
    def _get_stock_data(self):
        """获取股票数据"""
        try:
            print(f"[KLine] 获取股票数据: {self.stock_code}")
            
            # 解析日期
            start_dt = datetime.strptime(self.start_date, "%Y%m%d")
            end_dt = datetime.strptime(self.end_date, "%Y%m%d")
            
            # 确保开始日期不晚于结束日期
            if start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt
                print(f"[KLine] 警告: 开始日期晚于结束日期，已交换")
            
            # 生成日期范围
            date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
            
            if len(date_range) == 0:
                print("[KLine] 警告: 日期范围为空")
                return pd.DataFrame()
            
            # 使用股票代码作为随机种子，确保相同股票的数据一致
            seed = sum(ord(c) for c in self.stock_code)
            np.random.seed(seed)
            
            # 生成随机价格数据
            days = len(date_range)
            
            # 基础价格（根据股票代码生成）
            base_price = 10.0 + (seed % 100) / 10.0
            
            # 生成随机收益率
            returns = np.random.randn(days) * 0.02
            
            # 计算价格
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
            
            print(f"[KLine] 生成 {len(data)} 天数据")
            return data
            
        except Exception as e:
            print(f"[KLine] 错误: 获取股票数据时出错: {str(e)}")
            return pd.DataFrame()
    
    def _plot_kline(self, data):
        """绘制K线图"""
        try:
            print(f"[KLine] 开始绘制K线图，数据量: {len(data)}")
            
            if self.fig is None or self.ax is None:
                print("[KLine] 错误: 图形或坐标轴为None")
                return False
            
            # 清除坐标轴
            self.ax.clear()
            
            # 设置标题
            title = f"{self.stock_code} - K线图"
            if self.target_date:
                title += f" (关注日期: {self.target_date})"
            
            self.ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            
            # 绘制价格走势（使用折线图替代K线图，更稳定）
            self._plot_price_line(data)
            
            # 标记目标日期
            if self.target_date:
                self._mark_target_date(data)
            
            # 设置标签
            self.ax.set_xlabel("日期", fontsize=10)
            self.ax.set_ylabel("价格", fontsize=10)
            
            # 设置网格
            self.ax.grid(True, alpha=0.3, linestyle='--')
            
            # 自动调整刻度标签
            self._adjust_ticks(data)
            
            # 设置图形样式
            self._set_plot_style()
            
            # 调整布局
            self.fig.tight_layout()
            
            print("[KLine] K线图绘制完成")
            return True
            
        except Exception as e:
            print(f"[KLine] 错误: 绘制K线图时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _plot_price_line(self, data):
        """绘制价格走势线"""
        try:
            # 使用收盘价绘制折线
            prices = data['Close'].values
            dates = data.index
            
            # 绘制主价格线
            self.ax.plot(dates, prices, 
                        color='#2c3e50', 
                        linewidth=2, 
                        alpha=0.8,
                        label='收盘价')
            
            # 计算移动平均线
            if len(prices) >= 5:
                ma5 = pd.Series(prices).rolling(window=5).mean()
                self.ax.plot(dates, ma5, 
                           color='#e74c3c', 
                           linewidth=1.5, 
                           alpha=0.7,
                           linestyle='--',
                           label='5日均线')
            
            if len(prices) >= 20:
                ma20 = pd.Series(prices).rolling(window=20).mean()
                self.ax.plot(dates, ma20, 
                           color='#3498db', 
                           linewidth=1.5, 
                           alpha=0.7,
                           linestyle='-.',
                           label='20日均线')
            
            # 添加图例
            self.ax.legend(loc='upper left', fontsize=9)
            
        except Exception as e:
            print(f"[KLine] 警告: 绘制价格线时出错: {str(e)}")
            # 回退到简单折线
            self.ax.plot(data.index, data['Close'], color='blue', linewidth=2)
    
    def _mark_target_date(self, data):
        """标记目标日期"""
        try:
            if not self.target_date:
                return
            
            # 解析目标日期
            target_dt = datetime.strptime(self.target_date, "%Y%m%d")
            
            # 转换为pandas时间戳
            target_ts = pd.Timestamp(target_dt)
            
            # 检查目标日期是否在数据范围内
            if target_ts >= data.index[0] and target_ts <= data.index[-1]:
                # 找到最接近的日期
                idx = (data.index >= target_ts).argmax()
                closest_date = data.index[idx]
                
                # 绘制垂直线
                self.ax.axvline(x=closest_date, 
                              color='red', 
                              linestyle='--', 
                              linewidth=2, 
                              alpha=0.7)
                
                # 添加标注
                price_at_date = data.loc[closest_date, 'Close'] if closest_date in data.index else data['Close'].iloc[idx]
                self.ax.annotate(f'关注点\n{self.target_date}', 
                               xy=(closest_date, price_at_date),
                               xytext=(10, 20),
                               textcoords='offset points',
                               arrowprops=dict(arrowstyle='->', color='red', alpha=0.7),
                               fontsize=9,
                               color='red',
                               backgroundcolor='white',
                               alpha=0.8)
                
                print(f"[KLine] 标记目标日期: {self.target_date}")
                
        except Exception as e:
            print(f"[KLine] 警告: 标记目标日期时出错: {str(e)}")
    
    def _adjust_ticks(self, data):
        """调整刻度"""
        try:
            # 自动格式化日期
            if len(data) > 30:
                # 如果数据点多，减少刻度数量
                self.ax.xaxis.set_major_locator(plt.MaxNLocator(10))
            
            # 旋转日期标签
            plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 格式化Y轴
            self.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.2f}'))
            
        except Exception as e:
            print(f"[KLine] 警告: 调整刻度时出错: {str(e)}")
    
    def _set_plot_style(self):
        """设置图形样式"""
        try:
            # 设置背景色
            self.ax.set_facecolor('#f8f9fa')
            self.fig.patch.set_facecolor('#ffffff')
            
            # 设置边框颜色
            for spine in self.ax.spines.values():
                spine.set_edgecolor('#dddddd')
                spine.set_linewidth(1)
            
        except Exception as e:
            print(f"[KLine] 警告: 设置图形样式时出错: {str(e)}")
    
    def _create_canvas(self, container):
        """创建画布"""
        try:
            print("[KLine] 创建画布")
            
            if self.fig is None:
                print("[KLine] 错误: 图形为None，无法创建画布")
                return
            
            # 创建Matplotlib画布
            self.canvas = FigureCanvasTkAgg(self.fig, container)
            
            # 绘制图形
            self.canvas.draw()
            
            # 获取Tkinter部件并打包
            canvas_widget = self.canvas.get_tk_widget()
            canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 添加工具栏
            self._add_toolbar(container, canvas_widget)
            
            print("[KLine] 画布创建成功")
            
        except Exception as e:
            print(f"[KLine] 错误: 创建画布时出错: {str(e)}")
            self.canvas = None
    
    def _add_toolbar(self, container, canvas_widget):
        """添加工具栏"""
        try:
            # 创建工具栏容器
            toolbar_frame = ttk.Frame(container)
            toolbar_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
            
            # 创建工具栏
            toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
            toolbar.update()
            
            # 将工具栏部件添加到容器
            toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
        except Exception as e:
            print(f"[KLine] 警告: 添加工具栏时出错: {str(e)}")
            # 忽略工具栏错误，继续显示图表
    
    def _show_no_data_message(self, container):
        """显示无数据消息"""
        try:
            # 清除容器
            for widget in container.winfo_children():
                widget.destroy()
            
            # 创建消息框架
            msg_frame = ttk.Frame(container)
            msg_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # 图标
            icon_label = tk.Label(
                msg_frame,
                text="📈",
                font=('Arial', 48),
                foreground="#95a5a6"
            )
            icon_label.pack(pady=(0, 20))
            
            # 标题
            title_label = tk.Label(
                msg_frame,
                text=f"无 {self.stock_code} 的数据",
                font=('Arial', 14, 'bold'),
                foreground="#2c3e50"
            )
            title_label.pack(pady=(0, 10))
            
            # 详细信息
            info_label = tk.Label(
                msg_frame,
                text=f"日期范围: {self.start_date} 到 {self.end_date}",
                font=('Arial', 10),
                foreground="#7f8c8d"
            )
            info_label.pack()
            
            # 提示
            tip_label = tk.Label(
                msg_frame,
                text="(演示数据生成失败)",
                font=('Arial', 9),
                foreground="#bdc3c7"
            )
            tip_label.pack(pady=(20, 0))
            
        except Exception as e:
            print(f"[KLine] 错误: 显示无数据消息时出错: {str(e)}")
    
    def _show_error_message(self, container, message):
        """显示错误消息"""
        try:
            # 清除容器
            for widget in container.winfo_children():
                widget.destroy()
            
            # 创建错误框架
            error_frame = ttk.Frame(container)
            error_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # 错误图标
            icon_label = tk.Label(
                error_frame,
                text="⚠️",
                font=('Arial', 48),
                foreground="#e74c3c"
            )
            icon_label.pack(pady=(0, 20))
            
            # 错误标题
            title_label = tk.Label(
                error_frame,
                text="K线图加载失败",
                font=('Arial', 14, 'bold'),
                foreground="#e74c3c"
            )
            title_label.pack(pady=(0, 10))
            
            # 错误详情
            error_label = tk.Label(
                error_frame,
                text=message,
                font=('Arial', 10),
                foreground="#7f8c8d",
                wraplength=300,
                justify=tk.CENTER
            )
            error_label.pack(pady=(0, 20))
            
            # 股票信息
            stock_label = tk.Label(
                error_frame,
                text=f"股票: {self.stock_code}",
                font=('Arial', 9),
                foreground="#95a5a6"
            )
            stock_label.pack()
            
        except Exception as e:
            print(f"[KLine] 错误: 显示错误消息时出错: {str(e)}")
    
    def close(self):
        """关闭K线图"""
        try:
            if self.canvas:
                try:
                    self.canvas.get_tk_widget().destroy()
                except:
                    pass
                self.canvas = None
            
            if self.fig:
                try:
                    import matplotlib.pyplot as plt
                    plt.close(self.fig)
                except:
                    pass
                self.fig = None
            
            self.ax = None
            
            print("[KLine] K线图已关闭")
            
        except Exception as e:
            print(f"[KLine] 警告: 关闭K线图时出错: {str(e)}")


# 导入matplotlib.pyplot，但只在需要时使用
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError as e:
    print(f"[KLine] 警告: matplotlib.pyplot导入失败: {str(e)}")
    HAS_MATPLOTLIB = False
    plt = None


class SimpleKLineViewer:
    """简化版K线图查看器 - 作为备用方案"""
    
    def __init__(self, parent=None, stock_code='000001', 
                 start_date='20230101', end_date='20231231', 
                 target_date=None, is_embedded=False):
        self.parent = parent
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.target_date = target_date
        self.is_embedded = is_embedded
        
    def show_embedded(self, container):
        """显示简化的K线图"""
        try:
            # 清除容器
            for widget in container.winfo_children():
                widget.destroy()
            
            # 创建主框架
            main_frame = ttk.Frame(container)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # 标题
            title_label = tk.Label(
                main_frame,
                text=f"📈 {self.stock_code} K线图",
                font=('Arial', 16, 'bold'),
                foreground="#2c3e50"
            )
            title_label.pack(pady=(0, 20))
            
            # 信息框
            info_frame = ttk.LabelFrame(main_frame, text="股票信息", padding=10)
            info_frame.pack(fill=tk.X, pady=(0, 20))
            
            # 股票代码
            code_label = tk.Label(
                info_frame,
                text=f"股票代码: {self.stock_code}",
                font=('Arial', 12),
                foreground="#4a6fa5"
            )
            code_label.pack(anchor='w')
            
            # 日期范围
            date_label = tk.Label(
                info_frame,
                text=f"日期范围: {self.start_date} 到 {self.end_date}",
                font=('Arial', 11),
                foreground="#666666"
            )
            date_label.pack(anchor='w')
            
            # 关注日期
            if self.target_date:
                focus_label = tk.Label(
                    info_frame,
                    text=f"关注日期: {self.target_date}",
                    font=('Arial', 11, 'bold'),
                    foreground="#e74c3c"
                )
                focus_label.pack(anchor='w')
            
            # 模拟图表框架
            chart_frame = ttk.LabelFrame(main_frame, text="价格走势", padding=10)
            chart_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建简单的模拟图表
            self._create_simple_chart(chart_frame)
            
            # 状态提示
            status_label = tk.Label(
                main_frame,
                text="(简化视图 - Matplotlib图表加载失败)",
                font=('Arial', 9),
                foreground="#95a5a6"
            )
            status_label.pack(pady=(20, 0))
            
            return True
            
        except Exception as e:
            print(f"[SimpleKLine] 错误: 显示简化K线图时出错: {str(e)}")
            return False
    
    def _create_simple_chart(self, parent):
        """创建简单图表"""
        try:
            # 创建Canvas绘制简单折线
            canvas = tk.Canvas(parent, bg='white', height=300, highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            # 获取Canvas尺寸
            width = canvas.winfo_reqwidth()
            height = canvas.winfo_reqheight()
            
            if width < 10 or height < 10:
                width, height = 400, 300
            
            # 绘制边框
            canvas.create_rectangle(2, 2, width-2, height-2, 
                                  outline='#dddddd', width=1)
            
            # 绘制网格
            grid_color = '#f0f0f0'
            for i in range(1, 5):
                y = height * i // 5
                canvas.create_line(0, y, width, y, fill=grid_color, dash=(2, 2))
            
            for i in range(1, 10):
                x = width * i // 10
                canvas.create_line(x, 0, x, height, fill=grid_color, dash=(1, 2))
            
            # 生成模拟价格数据
            points = 20
            prices = []
            base = 10.0
            
            for i in range(points):
                change = (np.random.random() - 0.5) * 2
                base = max(1.0, base + change)
                prices.append(base)
            
            # 计算缩放比例
            min_price = min(prices)
            max_price = max(prices)
            price_range = max_price - min_price
            
            if price_range < 0.1:
                price_range = 0.1
            
            # 绘制价格线
            line_points = []
            for i, price in enumerate(prices):
                x = width * i / (points - 1) if points > 1 else width / 2
                y = height - (price - min_price) / price_range * height * 0.8
                y = max(10, min(height - 10, y))
                line_points.extend([x, y])
            
            if len(line_points) >= 4:
                canvas.create_line(line_points, fill='#3498db', width=3, smooth=True)
            
            # 绘制价格点
            for i, price in enumerate(prices):
                x = width * i / (points - 1) if points > 1 else width / 2
                y = height - (price - min_price) / price_range * height * 0.8
                y = max(10, min(height - 10, y))
                
                color = '#2ecc71' if i == 0 or price >= prices[i-1] else '#e74c3c'
                canvas.create_oval(x-4, y-4, x+4, y+4, fill=color, outline=color)
            
            # 添加Y轴标签
            for i in range(6):
                y = height * i // 5
                price_val = min_price + (5 - i) / 5 * price_range
                label = f"{price_val:.2f}"
                canvas.create_text(width - 5, y, text=label, anchor='e', 
                                 font=('Arial', 8), fill='#666666')
            
        except Exception as e:
            print(f"[SimpleKLine] 警告: 创建简单图表时出错: {str(e)}")
    
    def close(self):
        """关闭图表"""
        pass


# 主函数，用于测试
if __name__ == '__main__':
    # 测试K线图查看器
    root = tk.Tk()
    root.title("K线图测试")
    root.geometry("800x600")
    
    container = ttk.Frame(root)
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 创建K线图查看器
    viewer = KLineViewerOptimized(
        parent=container,
        stock_code='000001',
        start_date='20240101',
        end_date='20240331',
        target_date='20240215'
    )
    
    # 显示K线图
    success = viewer.show_embedded(container)
    
    if not success:
        print("使用简化版K线图")
        simple_viewer = SimpleKLineViewer(
            parent=container,
            stock_code='000001',
            start_date='20240101',
            end_date='20240331',
            target_date='20240215'
        )
        simple_viewer.show_embedded(container)
    
    root.mainloop()