#!/usr/bin/python
#-*-coding:UTF-8-*-

import os
import sys
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
from tkinter import simpledialog, messagebox
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, FuncFormatter
from matplotlib.patches import Rectangle

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent

# 全局变量
current_display_df = None
current_display_start = 0
cursor = None
fig = None
ax1 = None
ax2 = None
date_to_patch_map = {}  # 映射日期到对应的蜡烛矩形

def on_add(sel):
    global current_display_df, date_to_patch_map
    
    if current_display_df is None or len(current_display_df) == 0:
        return
    
    try:
        # 获取被悬停的艺术家对象
        artist = sel.artist
        
        # 查找这个艺术家对应的日期
        target_date = None
        for date_str, patch in date_to_patch_map.items():
            if patch == artist:
                target_date = pd.to_datetime(date_str, format='%Y%m%d')
                break
        
        if target_date is None:
            # 如果没有找到映射，尝试从x坐标推断
            if hasattr(artist, 'get_x'):
                x_val = artist.get_x()
                if isinstance(x_val, (tuple, list, np.ndarray)):
                    x_val = x_val[0] if len(x_val) > 0 else None
                
                if x_val is not None:
                    try:
                        # 将x坐标转换为日期
                        date_num = float(x_val)
                        target_date = mdates.num2date(date_num)
                    except:
                        pass
        
        if target_date is not None:
            # 在显示数据中查找对应的行
            closest_idx = None
            min_diff = float('inf')
            
            for i, date in enumerate(current_display_df['Date']):
                diff = abs((date - target_date).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_idx = i
            
            if closest_idx is not None and closest_idx < len(current_display_df):
                row = current_display_df.iloc[closest_idx]
                date_str = str(row['date'])
                
                # 计算涨跌幅
                if closest_idx > 0:
                    prev_close = current_display_df.iloc[closest_idx-1]['Close']
                    change_pct = (row['Close'] - prev_close) / prev_close * 100
                else:
                    change_pct = 0
                
                # 显示实际价格
                text = (f"日期: {date_str}\n"
                        f"开盘: {row['Open']:.2f}\n"
                        f"最高: {row['High']:.2f}\n"
                        f"最低: {row['Low']:.2f}\n"
                        f"收盘: {row['Close']:.2f}\n"
                        f"涨跌: {change_pct:+.2f}%\n"
                        f"成交量: {int(row['Volume']):,}")
                
                sel.annotation.set_text(text)
                sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightyellow',
                                                   edgecolor='black', linewidth=1)
                return
    
    except Exception as e:
        pass
    
    # 如果上述方法都失败，显示简单信息
    if len(current_display_df) > 0:
        date_str = str(current_display_df.iloc[0]['date'])
        last_date = str(current_display_df.iloc[-1]['date'])
        text = f"显示 {len(current_display_df)} 个交易日\n日期范围: {date_str} 到 {last_date}"
        sel.annotation.set_text(text)
        sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightblue',
                                           edgecolor='blue', linewidth=1)

def locate_to_date():
    """弹出对话框让用户输入日期，然后定位到该日期"""
    root = tk.Tk()
    root.withdraw()
    
    date_str = simpledialog.askstring("定位到日期", 
                                     f"请输入日期 (YYYY-MM-DD 或 YYYYMMDD)\n日期范围: {start_date_str} 到 {end_date_str}",
                                     parent=root)
    
    if date_str is None or date_str.strip() == "":
        root.destroy()
        return
    
    root.destroy()
    
    try:
        # 尝试不同格式
        try:
            target_date = pd.to_datetime(date_str)
        except:
            target_date = pd.to_datetime(date_str, format='%Y%m%d')
        
        # 查找最接近的日期
        date_idx = None
        min_diff = None
        
        for i, dt in enumerate(df['Date']):
            diff = abs((dt - target_date).days)
            if min_diff is None or diff < min_diff:
                min_diff = diff
                date_idx = i
        
        if date_idx is not None:
            refresh_chart(highlight_idx=date_idx, is_locate=True, 
                         locate_date_str=date_str, min_diff=min_diff)
            
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", f"日期格式错误: {e}\n请使用 YYYY-MM-DD 或 YYYYMMDD 格式")
        root.destroy()

def format_y_axis(value, pos):
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

def refresh_chart(highlight_idx=None, is_locate=False, locate_date_str="", min_diff=0):
    """刷新图表显示"""
    global current_display_df, current_display_start, fig, ax1, ax2, cursor, date_to_patch_map
    
    if not hasattr(refresh_chart, 'current_display_start'):
        refresh_chart.current_display_start = max(0, len(df) - 30)
    
    if highlight_idx is not None:
        if highlight_idx < 0:
            highlight_idx = 0
        elif highlight_idx >= len(df):
            highlight_idx = len(df) - 1
        
        display_start = max(0, highlight_idx - 15)
        refresh_chart.current_display_start = display_start
    
    current_display_start = refresh_chart.current_display_start
    display_end = min(len(df), current_display_start + 30)
    
    if display_end - current_display_start < 10:
        current_display_start = max(0, len(df) - 30)
        display_end = len(df)
        refresh_chart.current_display_start = current_display_start
    
    # 获取显示数据
    current_display_df = df.iloc[current_display_start:display_end].copy()
    
    # 清空图形和映射
    fig.clear()
    date_to_patch_map.clear()
    
    # 设置样式
    rc_params = {
        'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
        'axes.unicode_minus': False,
    }
    
    # 创建子图
    ax1 = plt.subplot2grid((6, 1), (0, 0), rowspan=4, fig=fig)
    ax2 = plt.subplot2grid((6, 1), (4, 0), rowspan=2, sharex=ax1, fig=fig)
    
    # 设置标题
    if is_locate:
        if min_diff > 0:
            actual_date = df.iloc[highlight_idx]['Date'].strftime('%Y-%m-%d')
            title = f'{stock_code} 日K线 - 定位到: {actual_date} (输入: {locate_date_str}, 相差{min_diff}天)'
        else:
            title = f'{stock_code} 日K线 - 定位到: {locate_date_str}'
    else:
        title = f'{stock_code} 日K线 ({start_date_str} 至 {end_date_str})'
    
    ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    # 准备数据 - 使用整数索引确保日期连续
    plot_dates = np.arange(len(current_display_df))
    dates_list = current_display_df['Date'].tolist()
    
    # 存储蜡烛宽度
    candle_width = 0.6
    
    # 绘制每个蜡烛
    patches = []
    for i, (idx, row) in enumerate(current_display_df.iterrows()):
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
        ax1.plot([plot_dates[i], plot_dates[i]], [low, high], color=color, linewidth=1, zorder=2)
        
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
        ax1.add_patch(rect)
        
        # 保存映射
        date_to_patch_map[date_str] = rect
        patches.append(rect)
    
    # 添加均线
    for period in [5, 10, 20, 30, 60]:
        if len(current_display_df) >= period:
            # 计算移动平均
            ma_values = []
            for i in range(len(current_display_df)):
                if i >= period - 1:
                    ma = current_display_df['Close'].iloc[i-period+1:i+1].mean()
                else:
                    ma = np.nan
                ma_values.append(ma)
            
            # 绘制均线
            ma_line, = ax1.plot(plot_dates, ma_values, color=f'C{period//10}', 
                              linewidth=1.5, label=f'MA{period}', alpha=0.7, zorder=1)
            
            # 将均线也添加到映射
            for i, date_str in enumerate(current_display_df['date']):
                date_to_patch_map[f"{date_str}_MA{period}"] = ma_line
    
    # 绘制成交量
    volume_colors = []
    volume_heights = []
    for i, (idx, row) in enumerate(current_display_df.iterrows()):
        if row['Close'] >= row['Open']:
            volume_colors.append('red')
        else:
            volume_colors.append('green')
        volume_heights.append(row['Volume'])
    
    ax2.bar(plot_dates, volume_heights, width=candle_width*0.8, 
           color=volume_colors, alpha=0.7, zorder=2)
    
    # 设置X轴刻度
    n_ticks = min(10, len(plot_dates))
    if n_ticks > 0:
        tick_indices = np.linspace(0, len(plot_dates)-1, n_ticks, dtype=int)
        tick_labels = []
        for idx in tick_indices:
            if idx < len(current_display_df):
                date_obj = current_display_df.iloc[idx]['Date']
                tick_labels.append(date_obj.strftime('%m-%d'))
        
        ax1.set_xticks(plot_dates[tick_indices])
        ax1.set_xticklabels(tick_labels, fontsize=9)
        ax2.set_xticks(plot_dates[tick_indices])
        ax2.set_xticklabels(tick_labels, fontsize=9)
    
    # 设置Y轴格式
    ax1.yaxis.set_major_formatter(FuncFormatter(format_y_axis))
    ax1.yaxis.set_major_locator(MaxNLocator(prune='both', nbins=8))
    
    # 添加Y轴标签
    ax1.set_ylabel('价格(元)', fontsize=10)
    ax2.set_ylabel('成交量', fontsize=10)
    
    # 添加图例
    ax1.legend(loc='upper left', fontsize=9)
    
    # 在图表最下方添加完整的日期说明
    if len(current_display_df) > 0:
        first_date = current_display_df.iloc[0]['Date'].strftime('%Y-%m-%d')
        last_date = current_display_df.iloc[-1]['Date'].strftime('%Y-%m-%d')
        date_info = f"显示日期范围: {first_date} 至 {last_date} (共{len(current_display_df)}个交易日)"
        fig.text(0.5, 0.01, date_info, ha='center', fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
    
    # 添加高亮标记
    if highlight_idx is not None and current_display_start <= highlight_idx < display_end:
        loc_idx = highlight_idx - current_display_start
        if 0 <= loc_idx < len(current_display_df):
            loc_date = current_display_df.iloc[loc_idx]['Date']
            loc_close = current_display_df.iloc[loc_idx]['Close']
            
            # 添加垂直线标记
            ax1.axvline(x=plot_dates[loc_idx], color='red', alpha=0.7, 
                       linestyle='--', linewidth=2, zorder=4)
            ax2.axvline(x=plot_dates[loc_idx], color='red', alpha=0.7, 
                       linestyle='--', linewidth=2, zorder=4)
            
            # 添加标记点
            ax1.plot(plot_dates[loc_idx], loc_close, 'ro', markersize=10, 
                    alpha=0.7, zorder=5)
            
            # 添加文本标签
            ylim = ax1.get_ylim()
            date_display = loc_date.strftime('%Y-%m-%d')
            ax1.text(plot_dates[loc_idx], ylim[1] * 0.95, f'← {date_display}', 
                    fontsize=11, color='red', va='top', ha='left', weight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.9),
                    zorder=6)
    
    # 设置X轴范围
    ax1.set_xlim(plot_dates[0] - 1, plot_dates[-1] + 1)
    ax2.set_xlim(plot_dates[0] - 1, plot_dates[-1] + 1)
    
    # 调整布局
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    # 重新连接鼠标悬停事件
    cursor = mplcursors.cursor(patches, hover=True)
    cursor.connect("add", on_add)
    
    # 添加键盘提示
    fig.text(0.5, 0.96, "提示：按 G 键输入日期定位，按 ← → 键逐日浏览", 
            ha='center', fontsize=10, color='blue',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
    
    plt.draw()
    print(f"图表已刷新，显示 {len(current_display_df)} 个交易日的数据")

def on_key_press(event):
    """键盘事件处理"""
    if event.key == 'g' or event.key == 'G':
        locate_to_date()
    elif event.key == 'left':
        move_days(-1)
    elif event.key == 'right':
        move_days(1)

def move_days(days):
    """移动指定天数"""
    if not hasattr(refresh_chart, 'current_display_start'):
        refresh_chart.current_display_start = max(0, len(df) - 30)
    
    if hasattr(move_days, 'current_highlight_idx'):
        current_idx = move_days.current_highlight_idx
    else:
        current_idx = refresh_chart.current_display_start + 15
    
    new_idx = current_idx + days
    if 0 <= new_idx < len(df):
        move_days.current_highlight_idx = new_idx
        refresh_chart(highlight_idx=new_idx)

if __name__ == '__main__':
    # 加载数据
    agent = TdxDataAgent()
    stock_code = "601398" 
    print("正在加载数据...")
    
    try:
        df = agent.read_kdata_cache(stock_code, "20260301", "20260401")
        
        if df is None or df.empty:
            print("错误：无法获取数据，程序退出")
            sys.exit(1)
            
        print(f"获取数据成功，共{len(df)}条记录")
        
        # 处理数据格式
        print("处理数据格式...")
        
        # 检查数据列
        print("数据列名:", df.columns.tolist())
        
        # 根据实际列名处理数据
        if 'r_open' in df.columns and 'r_high' in df.columns and 'r_low' in df.columns and 'r_close' in df.columns:
            df['Open'] = df['r_open']
            df['High'] = df['r_high']
            df['Low'] = df['r_low']
            df['Close'] = df['r_close']
            print("使用复权价格数据")
        elif 'open' in df.columns and 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
            sample_price = df['close'].iloc[0] if not df.empty else 0
            if sample_price > 1000:
                print("检测到价格单位为分，转换为元")
                df['Open'] = df['open'] / 100.0
                df['High'] = df['high'] / 100.0
                df['Low'] = df['low'] / 100.0
                df['Close'] = df['close'] / 100.0
            else:
                print("使用原始价格数据")
                df['Open'] = df['open']
                df['High'] = df['high']
                df['Low'] = df['low']
                df['Close'] = df['close']
        else:
            print("错误：数据中未找到价格列")
            print("可用列:", df.columns.tolist())
            sys.exit(1)
        
        # 确保价格是数值类型
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 检查是否有有效的价格数据
        if df[['Open', 'High', 'Low', 'Close']].isna().all().all():
            print("错误：所有价格数据均为NaN")
            sys.exit(1)
        
        # 处理缺失值
        for col in ['Open', 'High', 'Low', 'Close']:
            if df[col].isna().all():
                print(f"警告：{col}列全为NaN，使用0填充")
                df[col] = 0
            else:
                prev_value = None
                for i in range(len(df)):
                    if pd.isna(df.at[i, col]):
                        if prev_value is not None:
                            df.at[i, col] = prev_value
                    else:
                        prev_value = df.at[i, col]
                
                if df[col].isna().any():
                    first_valid_idx = df[col].first_valid_index()
                    if first_valid_idx is not None:
                        first_valid_value = df.at[first_valid_idx, col]
                        df[col] = df[col].fillna(first_valid_value)
        
        # 处理成交量
        if 'volume' in df.columns:
            df['Volume'] = pd.to_numeric(df['volume'], errors='coerce')
            if df['Volume'].isna().all():
                df['Volume'] = 100000
            else:
                prev_volume = None
                for i in range(len(df)):
                    if pd.isna(df.at[i, 'Volume']):
                        if prev_volume is not None:
                            df.at[i, 'Volume'] = prev_volume
                    else:
                        prev_volume = df.at[i, 'Volume']
                
                if df['Volume'].isna().any():
                    df['Volume'] = df['Volume'].fillna(100000)
        else:
            print("警告：未找到成交量列，使用默认值")
            df['Volume'] = 100000
        
        # 处理日期
        if 'date' in df.columns:
            df['Date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
        else:
            print("错误：未找到日期列")
            sys.exit(1)
        
        # 删除无效日期
        original_len = len(df)
        df = df.dropna(subset=['Date'])
        if len(df) < original_len:
            print(f"警告：删除了{original_len - len(df)}条无效日期记录")
        
        df = df.sort_values('Date')
        
        if len(df) == 0:
            print("错误：没有有效的日期数据")
            sys.exit(1)
        
        # 获取日期范围字符串
        start_date_str = str(df['date'].iloc[0])
        end_date_str = str(df['date'].iloc[-1])
        
        # 打印价格范围
        price_min = df['Close'].min()
        price_max = df['Close'].max()
        print(f"数据日期范围: {start_date_str} 到 {end_date_str}")
        print(f"价格范围: {price_min:.2f} 到 {price_max:.2f}")
        print(f"数据示例（前5行）:")
        print(df[['date', 'Open', 'High', 'Low', 'Close']].head())
        
    except Exception as e:
        print(f"数据加载或处理出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 创建图形
    fig = plt.figure(figsize=(14, 9))
    
    # 初始绘制
    refresh_chart()
    
    # 连接键盘事件
    fig.canvas.mpl_connect('key_press_event', on_key_press)
    
    # 显示图表
    print("显示图表中...")
    print("使用说明:")
    print("1. 按 G 键: 输入日期定位")
    print("2. 按 ← 键: 向前一天")
    print("3. 按 → 键: 向后一天")
    print("4. 鼠标悬停: 查看详细信息")
    plt.show()