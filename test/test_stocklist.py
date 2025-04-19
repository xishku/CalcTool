import os
import sys
import unittest
import datetime
import numpy

import unittest
import pandas as pd
import csv
from pathlib import Path

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.data_online import TdxOnlineHqAgent
from pytdx.hq import TdxHq_API 



class TestStockListFun(unittest.TestCase):
    def test_add1(self):
        src_file = "C:\\new_tdx\\T0002\\export\\全部Ａ股20250419.xlsx"
        file_path = Path(src_file)
        if not (file_path.exists() and file_path.is_file()):
            err = f"文件不存在{src_file}"
            raise Exception(err)

        # 读取Excel文件
        Logger.log().info("打开文件: %s" % src_file)

        sheet_name = "全部Ａ股20250419"
        df = pd.read_excel(src_file, sheet_name=sheet_name, engine="openpyxl")
        # df = pd.read_excel(src_file, sheet_name=sheet_name, dtype=({"代码": str}))

        for cur_row in range(len(df) - 1, -1, -1):
            src_tick = df.at[cur_row, "代码"]
            Logger.log().info(f"{src_tick}")

        self.assertEqual(1, 1)


if __name__ == '__main__':
    agent = TdxDataAgent()
    cur_tick = "002261"
    code = str(int(cur_tick)).zfill(6)
    df_kdata = None
    date_t0 = datetime.date(year=2025, month=1, day=3)
    date_t2 = datetime.date(year=2025, month=1, day=5)
    date_tn = datetime.date(year=2025, month=3, day=23)
    t0_date_f1 = f"{date_t0.strftime("%Y-%m-%d")}"  
    t2_date_f1 = f"{date_t2.strftime("%Y-%m-%d")}"  
    tn_date_f1 = f"{date_tn.strftime("%Y-%m-%d")}"  

    t0_date_f2 = f"{date_t0.strftime("%Y%m%d")}"  
    t2_date_f2 = f"{date_t2.strftime("%Y%m%d")}"  
    tn_date_f2 = f"{date_tn.strftime("%Y%m%d")}"  
    Logger.log().info(f"{t2_date_f1} {tn_date_f1} {t2_date_f2} {tn_date_f2}")

    df_kdata = agent.read_kdata_cache(code, t0_date_f2, tn_date_f2)

    print(df_kdata)
    
    # unittest.main()
    



        