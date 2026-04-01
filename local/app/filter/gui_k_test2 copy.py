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
import datetime
import mplcursors
import tkinter as tk
from tkinter import simpledialog

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent

def on_add(sel):
    idx = int(sel.index[0]) if isinstance(sel.index, tuple) else int(sel.index)
    
    if idx < len(df):
        row = df.iloc[idx]
        date_str = str(df['date'].iloc[idx])
        
        text = (f"日期: {date_str}\n"
                f"开盘: {row['Open']:.2f}\n"
                f"最高: {row['High']:.2f}\n"
                f"最低: {row['Low']:.2f}\n"
                f"收盘: {row['Close']:.2f}")
        
        sel.annotation.set_text(text)
        sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightyellow')

def locate_to_date():
    """弹出对话框让用户输入日期，然后定位到该日期"""
    # 创建简单的Tkinter对话框
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 弹出日期输入对话框
    date_str = simpledialog.askstring("定位到日期", 
                                     f"请输入日期 (YYYY-MM-DD 或 YYYYMMDD)\n日期范围: {start_date_str} 到 {end_date_str}",
                                     parent=root)
    
    if date_str is None or date_str.strip() == "":
        root.destroy()
        return
    
    root.destroy()
    
    # 尝试解析日期
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
            # 计算显示范围（显示定位日期的前后15天）
            display_start = max(0, date_idx - 15)
            display_end = min(len(df), date_idx + 15)
            
            # 获取显示数据
            display_df = df.iloc[display_start:display_end]
            
            # 重新绘图
            fig.clear()
            
            rc_params = {
                'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
                'axes.unicode_minus': False,
            }
            s = mpf.make_mpf_style(base_mpf_style='charles', rc=rc_params)
            
            # 绘制K线
            axlist = mpf.plot(display_df.set_index('Date'), 
                type='candle', 
                title=f'{stock_code} 日K线 ({start_date_str} 至 {end_date_str}) - 定位到: {target_date.strftime("%Y-%m-%d")}',
                volume=True, 
                mav=(5, 10, 20, 30, 60), 
                style=s,
                returnfig=True,
                fig=fig)[1]
            
            # 在定位日期添加标记
            if date_idx >= display_start and date_idx < display_end:
                loc_idx = date_idx - display_start
                if loc_idx < len(display_df):
                    loc_date = display_df.iloc[loc_idx]['Date']
                    loc_close = display_df.iloc[loc_idx]['Close']
                    
                    # 添加垂直线标记
                    axlist[0].axvline(x=loc_date, color='red', alpha=0.5, linestyle='--', linewidth=1.5)
                    
                    # 添加标记点
                    axlist[0].plot(loc_date, loc_close, 'ro', markersize=8, alpha=0.7, zorder=5)
                    
                    # 添加文本标签
                    ylim = axlist[0].get_ylim()
                    axlist[0].text(loc_date, ylim[1] * 0.95, f'← 定位位置\n{target_date.strftime("%Y-%m-%d")}', 
                                 fontsize=10, color='red', va='top', ha='left',
                                 bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.8))
            
            # 重新连接鼠标悬停事件
            cursor = mplcursors.cursor(axlist[0], hover=True)
            cursor.connect("add", on_add)
            
            # 添加定位日期信息
            if min_diff > 0:
                plt.figtext(0.5, 0.01, f"注意：未找到精确日期{date_str}，已定位到最近日期（相差{min_diff}天）", 
                          ha='center', fontsize=10, color='red', 
                          bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))
            
            fig.tight_layout(rect=[0, 0.03, 1, 0.97])
            plt.draw()
            
    except Exception as e:
        # 显示错误对话框
        root = tk.Tk()
        root.withdraw()
        tk.messagebox.showerror("错误", f"日期格式错误: {e}\n请使用 YYYY-MM-DD 或 YYYYMMDD 格式")
        root.destroy()

def on_key_press(event):
    """键盘事件处理"""
    if event.key == 'g' or event.key == 'G':
        locate_to_date()
    elif event.key == 'left':
        # 向左移动一天
        move_days(-1)
    elif event.key == 'right':
        # 向右移动一天
        move_days(1)

def move_days(days):
    """移动指定天数"""
    global current_display_idx
    
    if not hasattr(plt.gcf(), 'current_display_idx'):
        plt.gcf().current_display_idx = len(df) // 2
    else:
        current_display_idx = plt.gcf().current_display_idx
    
    new_idx = current_display_idx + days
    if 0 <= new_idx < len(df):
        plt.gcf().current_display_idx = new_idx
        
        # 计算显示范围
        display_start = max(0, new_idx - 15)
        display_end = min(len(df), new_idx + 15)
        
        # 重新绘图
        fig.clear()
        display_df = df.iloc[display_start:display_end]
        
        rc_params = {
            'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
            'axes.unicode_minus': False,
        }
        s = mpf.make_mpf_style(base_mpf_style='charles', rc=rc_params)
        
        axlist = mpf.plot(display_df.set_index('Date'), 
            type='candle', 
            title=f'{stock_code} 日K线 ({start_date_str} 至 {end_date_str})',
            volume=True, 
            mav=(5, 10, 20, 30, 60), 
            style=s,
            returnfig=True,
            fig=fig)[1]
        
        # 添加标记
        loc_idx = new_idx - display_start
        if 0 <= loc_idx < len(display_df):
            loc_date = display_df.iloc[loc_idx]['Date']
            loc_close = display_df.iloc[loc_idx]['Close']
            
            axlist[0].axvline(x=loc_date, color='red', alpha=0.5, linestyle='--', linewidth=1.5)
            axlist[0].plot(loc_date, loc_close, 'ro', markersize=8, alpha=0.7, zorder=5)
            
            ylim = axlist[0].get_ylim()
            axlist[0].text(loc_date, ylim[1] * 0.95, f'← 当前位置', 
                         fontsize=10, color='red', va='top', ha='left',
                         bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.8))
        
        cursor = mplcursors.cursor(axlist[0], hover=True)
        cursor.connect("add", on_add)
        
        fig.tight_layout()
        plt.draw()

if __name__ == '__main__':
    agent = TdxDataAgent()
    stock_code = "601398" 
    df = agent.read_kdata_cache(stock_code, "20260301", "20260401")
    
    # 处理数据格式
    df['Open'] = df['open']
    df['High'] = df['high'] / 100
    df['Low'] = df['low'] / 100
    df['Close'] = df['close'] / 100
    df['Volume'] = df['volume']
    df['Date'] = pd.to_datetime(df['date'])
    
    # 保存原始数据格式用于显示
    original_df = df.copy()
    
    # 准备用于绘图的DataFrame
    plot_df = df.set_index('Date').copy()
    
    # 获取日期范围字符串
    start_date_str = str(df['date'].iloc[0])
    end_date_str = str(df['date'].iloc[-1])
    
    # 设置初始显示范围（最后30天）
    display_start = max(0, len(df) - 30)
    display_df = df.iloc[display_start:].set_index('Date')
    
    # 设置图表标题
    chart_title = f'{stock_code} 日K线 ({start_date_str} 至 {end_date_str})'
    
    # 设置样式
    rc_params = {
        'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
        'axes.unicode_minus': False,
    }
    s = mpf.make_mpf_style(base_mpf_style='charles', rc=rc_params)
    
    # 绘制K线图
    fig, axlist = mpf.plot(display_df, 
        type='candle', 
        title=chart_title, 
        volume=True, 
        mav=(5, 10, 20, 30, 60), 
        style=s,
        returnfig=True,
        figscale=1.5)
    
    # 添加鼠标悬停
    cursor = mplcursors.cursor(axlist[0], hover=True)
    cursor.connect("add", on_add)
    
    # 连接键盘事件
    fig.canvas.mpl_connect('key_press_event', on_key_press)
    
    # 添加提示文本
    plt.figtext(0.5, 0.01, "提示：按 G 键输入日期定位，按 ← → 键逐日浏览", 
                ha='center', fontsize=10, color='blue',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
    
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    
    # 显示图表
    plt.show()