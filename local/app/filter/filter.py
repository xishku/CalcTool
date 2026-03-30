
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
from data import Stock

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
from CalcTool.sdk.logger import Logger


from pytdx.hq import TdxHq_API 
from pytdx.util.best_ip import select_best_ip


if __name__ == '__main__':
    agent = TdxDataAgent()
    # code_list = agent.get_code_list_by_excode(TdxDataAgent.EXCODE_SH)
    code_list = agent.get_code_list_all()

    for index, code in enumerate(code_list, start=1):
        print(f"第 {index} 个代码: {code}")
        t0_date = 20260320
        tn_date = 20260330
        stock1 = Stock.create(code)
        stock1.find_up_day(t0_date, tn_date)
    
    Logger.log().info("finished")


   
