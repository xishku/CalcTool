import os
import sys
import unittest
import datetime
import numpy

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.data_online import TdxOnlineHqAgent
from pytdx.hq import TdxHq_API 

import unittest



class TestTdxDataAgentFun(unittest.TestCase):
    def test_add(self):
        agent = TdxDataAgent()
        agent1 = TdxOnlineHqAgent()
        agent2 = TdxOnlineHqAgent()
        Logger.log().info(f"id(agent2) = {id(agent2)} id(agent1) = {id(agent1)}")
        self.assertEqual(True, agent1 is agent2)

        df = agent1.get_kdata('601398','2025-01-06','2025-01-08')
        # Logger.log().info(f"{df}")
        self.assertEqual(6.75, df.loc['2025-01-06', 'close'])
        self.assertEqual(6.69, df.loc['2025-01-07', 'close'])
        self.assertEqual(6.76, df.loc['2025-01-08', 'close'])
    
        df = agent.read_kdata('601816')
        # print(df)
        t = agent.get_extreme_in_days('601816', df, 20240210, 20)
        print(t[3])

        self.assertEqual(t[3], 20240123)
        
        t = agent.get_extreme_in_tradingdays('601816', df, 20240210, 20)

        v = agent.value_post_adj(10, 5, 10)
        Logger.log().info(f"v = {v}")
        self.assertEqual(v, 20.5)

        # self.assertEqual(t[3], 20240118)

    def test_add1(self):
        tdx = TdxOnlineHqAgent()
        # print(tdx.get_xdxr_info("000001"))
        self.assertGreaterEqual(len(tdx.get_xdxr_info("000001")), 10)
        # print(tdx.get_xdxr_info("601816"))
        self.assertGreaterEqual(len(tdx.get_xdxr_info("601816")), 10)

if __name__ == '__main__':
    # agent = TdxDataAgent()

    # df = agent.read_kdata('601398')
    # print(df['date'][0], df['date'][0] == 20200107)
    # for cur_row in range(0, len(df)):
    #     Logger.log().info(f"{df['date'][cur_row]} {df['r_high'][cur_row]} {df['close'][cur_row]}")
    # agent.get_extreme_in_days(df, 20250106, 20)
    # unittest.main()

    # from pytdx.hq import TdxHq_API
    # import csv

    api = TdxHq_API(heartbeat=True, auto_retry=True)
    with api.connect('121.36.81.195', 7709):
        date_str = '2024-12-27'
        end_date_str = '2025-01-27'
        df = api.get_k_data('301439', date_str, end_date_str)
        base = 14.31
        tp = base * (1 + 0.15)
        sl = base * (1 - 0.08)
        print(tp, sl)

        tp_df = df[df["close"] >= tp]
        print(f"len(tp_df) = {len(tp_df)}")
        sl_df = df[df["close"] <= sl]
        print(f"len(sl_df) = {len(sl_df)} {sl_df}")        
        # print(df.at[date_str, "close"])
    #     print("OK")
    #     # data = api.get_security_bars(9, 0, '000001', 0, 10) #返回普通list
    #     # print(data)
    #     data = api.to_df(api.get_security_bars(9, 0, '000001', 0, 10)) # 返回DataFrame
    #     # print(data)
    #     s_list = api.get_security_list(0, 0)
    #     print(len(s_list))
    #     for stock in s_list:
    #         print(stock["code"])
    #         break



        

    #     with open('E:\dev\stock1229-20250105\\app\data\output.csv', mode='w', newline='') as file:
    #         writer = csv.writer(file)

    #         s_list = api.get_security_list(0, 0)
    #         print(len(s_list))
    #         for stock in s_list:
    #             print(stock["code"])
                
    #             xdxr = api.get_xdxr_info(0, str(stock["code"]))
    #             for item in xdxr:
    #                 line = ["code"]
    #                 for key, value in item.items():
    #                     line.append(f"{key}")
                    
    #                 writer.writerow(line)
    #                 break

    #             for item in xdxr:
    #                 # print(item)
    #                 line = [stock["code"]]
    #                 for key, value in item.items():
    #                     line.append(f"{value}")   
                    
    #                 writer.writerow(line) 
                
                
    #         # 写入数据
    #         print("CSV 文件写入成功")

        