import os
import sys
import unittest
import datetime
import numpy

import unittest
import pandas as pd
import csv

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.data_online import TdxOnlineHqAgent
from pytdx.hq import TdxHq_API 



class TestAdjFun(unittest.TestCase):
    def test_add1(self):
        tdx = TdxOnlineHqAgent()
        dl = list()

        for base in range(0, 10000, 1000):
            stock_list = tdx.get_security_list(0, base)
            if stock_list is None:
                break

            
            if stock_list[0]["code"][:2] not in ("00", "39", "60", "68"):
                break
            else:
                print("match: ", stock_list[0]["code"])

            print(f"len(stock_list) = {len(stock_list)} : {stock_list[0]}")
            # print(stock_list)
            # break

            for stock in stock_list:
                code = stock["code"]
                print(code)

                fi = tdx.get_finance_info(code)

                # print(f"{fi}")
                
                row_list = list()
                row_list.append(f"{stock["name"]}")
                for item in fi:
                    row_list.append(f"{item}")
                    row_list.append(f"{fi[item]}")

                dl.append(row_list)

        # print(dl)
        # df = pd.DataFrame(fi)
        # print(df)

        csv_file = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), 'data\\finance.csv')
        # 打开一个文件以写入模式（'w'）打开，并使用newline=''来避免在Windows上产生额外的空行
        with open(csv_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            # 写入数据到CSV文件
            writer.writerows(dl)

        print("CSV文件写入成功")

        self.assertEqual(1, 1)


if __name__ == '__main__':
    unittest.main()
    



        