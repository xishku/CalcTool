#!/usr/bin/python#

#-*-coding:UTF-8-*-

import os
import sys


import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False  # 负号正常显示
import pandas as pd
import datetime
import mplcursors

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent


from pytdx.hq import TdxHq_API 
from pytdx.util.best_ip import select_best_ip
# from .timeit_decorator import Dec

df = None

def on_add(sel):
    # sel.target.index 获取的是鼠标点击/悬停位置的 x 轴索引（整数）
    # 注意：mplfinance 内部会将日期转换为整数索引进行绘图
    idx = int(sel.index[0]) if isinstance(sel.index, tuple) else int(sel.index)
    
    # 确保索引不越界
    if idx < len(df):
        row = df.iloc[idx]
        
        # 获取对应的日期（从原始 DataFrame 的索引中获取）
        date_str = str(df['date'].iloc[idx])
        
        # 自定义显示的文本内容
        text = (f"日期: {date_str}\n"
                f"开盘: {row['Open']:.2f}\n"
                f"最高: {row['High']:.2f}\n"
                f"最低: {row['Low']:.2f}\n"
                f"收盘: {row['Close']:.2f}")
        
        # 设置提示框文本
        sel.annotation.set_text(text)
        
        # (可选) 美化提示框样式
        sel.annotation.get_bbox_patch().set(alpha=0.9, facecolor='lightyellow')



if __name__ == '__main__':
    # # 自动测试并返回最佳服务器IP和端口
    # best_ip_info = select_best_ip()
    # print(best_ip_info)
    # # 输出示例: {'ip': '115.238.90.165', 'port': 7709}


    # api = TdxHq_API(heartbeat=True, auto_retry=True)
    # with api.connect('218.75.126.9', 7709): # 121.36.81.195
    #     print("OK")
    #     # data = api.get_security_bars(9, 0, '000001', 0, 10) #返回普通list
    #     # print(data)
    #     data = api.to_df(api.get_security_bars(9, 0, '000001', 0, 10)) # 返回DataFrame
    #     # print(data)
    #     xdxr = api.get_xdxr_info(1, '601398')

    #     print(type(xdxr))
    #     for item in xdxr:
    #         print(item)


        # print(read_kdata('000001'))
    agent = TdxDataAgent()

    stock_code = "601816" 
    df = agent.read_kdata_cache(stock_code, "20250101", "20260401")
    # print(df)


    # 假设 df 是一个包含 Open, High, Low, Close, Volume 列的 DataFrame
    # 且索引为日期时间类型
    # df = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)

    df['Open'] = df['open']
    # df['preclose'] = df['close'].shift()
    # df['r_open'] = df['open'] / 100
    df['High'] = df['high'] / 100
    df['Low'] = df['low'] / 100
    df['Close'] = df['close'] / 100
    # df['Date'] = df['date']
    # df['limitup'] = df['r_close'] >= round(df['preclose'] / 100 * 1.1, 2)
    # df['limitdown'] = df['r_close'] <= round(df['preclose'] / 100 * 0.9, 2)
    df['Volume'] = df['volume']
    df['Date'] = pd.to_datetime(df['date']) # 确保是时间格式
    df.set_index('Date', inplace=True)      # 设为索引

    
    # print(df['date'].iloc[0], datetime.datetime.strptime(str(df['date'].iloc[0]), "%Y%m%d").strftime("%Y-%m-%d"))
    # 获取数据的起始和结束日期
    start_date = str(df['date'].iloc[0])
    end_date = str(df['date'].iloc[-1])

    # 拼接标题
    chart_title = f'{stock_code} 日K线 ({start_date} 至 {end_date})'

    # 指定中文字体，解决乱码
    rc_params = {
        'font.sans-serif': ['Microsoft YaHei', 'SimHei'],
        'axes.unicode_minus': False,
    }
    s = mpf.make_mpf_style(base_mpf_style='charles', rc=rc_params)

    # 一行代码绘制带成交量和20日、60日均线的K线图
    fig, axlist = mpf.plot(df, 
        type='candle', 
        title=chart_title, 
        volume=True, 
        mav=(5, 10, 20, 30, 60), 
        style=s,
        returnfig=True,  # 返回 Figure 对象
        figscale=1.5)
    
    cursor = mplcursors.cursor(axlist[0], hover=True)
    cursor.connect("add", on_add)

    plt.show()