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

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent

def on_add(sel):
    idx = int(sel.target.index) if hasattr(sel.target, 'index') else 0
    
    if idx < len(current_display_df):
        row = current_display_df.iloc[idx]
        date_str = str(row['date'])
        
        text = (f"日期: {date_str}\n"
                f"开盘: {row['Open']:.3f}\n"
                f"最高: {row['High']:.3f}\n"
                f"最低: {row['Low']:.3f}\n"
                f"收盘: {row['Close']:.3f}")
        
        sel.annotation.set_text(text)
        sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightyellow')

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
    global current_display_df, current_display_start, fig, ax1, ax2
    
    if not hasattr(refresh_chart, 'current_display_start'):
        refresh_chart.current_display_start = max(0, len(df) - 30)
    
    if highlight_idx is not None:
        # 确保highlight_idx在有效范围内
        if highlight_idx < 0:
            highlight_idx = 0
        elif highlight_idx >= len(df):
            highlight_idx = len(df) - 1
        
        # 计算显示范围，确保高亮日期在中间
        display_start = max(0, highlight_idx - 15)
        refresh_chart.current_display_start = display_start
    
    display_start = refresh_chart.current_display_start
    display_end = min(len(df), display_start + 30)
    
    if display_end - display_start < 10:  # 如果数据太少，显示更多
        display_start = max(0, len(df) - 30)
        display_end = len(df)
    
    # 获取显示数据
    current_display_df = df.iloc[display_start:display_end].copy()
    
    # 清空图形
    fig.clear()
    
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
    
    # 准备用于mplfinance的数据
    plot_data = current_display_df.set_index('Date').copy()
    
    # 使用mplfinance绘制K线
    ap = []
    # 添加均线
    for period in [5, 10, 20, 30, 60]:
        if len(plot_data) >= period:
            ma = plot_data['Close'].rolling(period).mean()
            ap.append(mpf.make_addplot(ma, ax=ax1, color=f'C{period//10}', width=0.7))
    
    # 使用charles样式
    s = mpf.make_mpf_style(base_mpf_style='charles', rc=rc_params)
    
    # 直接调用mplfinance绘图函数
    mpf.plot(plot_data, 
             type='candle',
             ax=ax1,
             volume=ax2,
             addplot=ap,
             style=s,
             show_nontrading=False,
             datetime_format='%Y-%m-%d',  # 设置日期格式
             xrotation=45,  # 旋转日期标签
             axtitle='',
             volume_panel=1)
    
    # 格式化X轴，使用实际的日期
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    
    # 控制显示的日期数量
    n_dates = len(plot_data)
    if n_dates > 20:
        # 如果日期太多，间隔显示
        step = max(1, n_dates // 10)
        tick_positions = list(range(0, n_dates, step))
        tick_labels = [plot_data.index[i].strftime('%m-%d') for i in tick_positions]
        
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels(tick_labels, fontsize=9)
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, fontsize=9)
    
    # 设置Y轴格式
    ax1.yaxis.set_major_formatter(FuncFormatter(format_y_axis))
    
    # 设置Y轴刻度密度
    ax1.yaxis.set_major_locator(MaxNLocator(prune='both', nbins=8))
    
    # 添加Y轴标签
    ax1.set_ylabel('价格', fontsize=10)
    ax2.set_ylabel('成交量', fontsize=10)
    
    # 在图表最下方添加完整的日期说明
    if len(current_display_df) > 0:
        first_date = current_display_df.iloc[0]['Date'].strftime('%Y-%m-%d')
        last_date = current_display_df.iloc[-1]['Date'].strftime('%Y-%m-%d')
        date_info = f"显示日期范围: {first_date} 至 {last_date} (共{len(current_display_df)}个交易日)"
        fig.text(0.5, 0.01, date_info, ha='center', fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
    
    # 添加高亮标记
    if highlight_idx is not None and display_start <= highlight_idx < display_end:
        loc_idx = highlight_idx - display_start
        if 0 <= loc_idx < len(current_display_df):
            # 获取实际的日期位置
            loc_date = current_display_df.iloc[loc_idx]['Date']
            loc_close = current_display_df.iloc[loc_idx]['Close']
            
            # 在X轴上找到这个日期的位置
            date_num = mdates.date2num(loc_date)
            
            # 添加垂直线标记
            ax1.axvline(x=date_num, color='red', alpha=0.7, linestyle='--', linewidth=2)
            ax2.axvline(x=date_num, color='red', alpha=0.7, linestyle='--', linewidth=2)
            
            # 添加标记点
            ax1.plot(date_num, loc_close, 'ro', markersize=10, alpha=0.7, zorder=5)
            
            # 添加文本标签
            ylim = ax1.get_ylim()
            date_display = loc_date.strftime('%Y-%m-%d')
            ax1.text(date_num, ylim[1] * 0.95, f'← {date_display}', 
                    fontsize=11, color='red', va='top', ha='left', weight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.9))
    
    # 调整布局
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    # 重新连接鼠标悬停事件
    cursor = mplcursors.cursor(ax1, hover=True)
    cursor.connect("add", on_add)
    
    # 添加键盘提示
    fig.text(0.5, 0.96, "提示：按 G 键输入日期定位，按 ← → 键逐日浏览", 
            ha='center', fontsize=10, color='blue',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
    
    plt.draw()

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
    
    # 获取当前高亮位置
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
    
    # 注意：当前是2026年4月1日，获取2026年3月到4月的数据
    try:
        df = agent.read_kdata_cache(stock_code, "20260301", "20260401")
        
        if df is None or df.empty:
            print("错误：无法获取数据，程序退出")
            sys.exit(1)
            
        print(f"获取数据成功，共{len(df)}条记录")
        
        # 处理数据格式 - 使用实际价格，不除以100
        print("处理数据格式...")
        
        # 检查数据列
        print("数据列名:", df.columns.tolist())
        
        # 根据实际列名处理数据
        if 'r_open' in df.columns and 'r_high' in df.columns and 'r_low' in df.columns and 'r_close' in df.columns:
            # 使用复权价格
            df['Open'] = df['r_open']
            df['High'] = df['r_high']
            df['Low'] = df['r_low']
            df['Close'] = df['r_close']
        elif 'open' in df.columns and 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
            # 使用原始价格
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
        
        # 处理缺失值 - 不使用fillna的method参数
        for col in ['Open', 'High', 'Low', 'Close']:
            # 检查是否全为NaN
            if df[col].isna().all():
                print(f"警告：{col}列全为NaN，使用0填充")
                df[col] = 0
            else:
                # 手动向前填充NaN值
                prev_value = None
                for i in range(len(df)):
                    if pd.isna(df.at[i, col]):
                        if prev_value is not None:
                            df.at[i, col] = prev_value
                    else:
                        prev_value = df.at[i, col]
                
                # 如果还有NaN（比如第一行就是NaN），向后填充
                if df[col].isna().any():
                    # 找到第一个非NaN值
                    first_valid_idx = df[col].first_valid_index()
                    if first_valid_idx is not None:
                        first_valid_value = df.at[first_valid_idx, col]
                        df[col] = df[col].fillna(first_valid_value)
        
        # 处理成交量
        if 'volume' in df.columns:
            df['Volume'] = pd.to_numeric(df['volume'], errors='coerce')
            # 处理缺失值
            if df['Volume'].isna().all():
                df['Volume'] = 100000
            else:
                # 手动处理缺失值
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
        print(f"价格范围: {price_min:.3f} 到 {price_max:.3f}")
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