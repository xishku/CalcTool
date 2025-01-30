# -i https://pypi.tuna.tsinghua.edu.cn/simple

import datetime
import pandas as pd
import numpy

import openpyxl
from openpyxl.comments import Comment


class CalcLast1YearCount:
    def count(self):
        # 读取Excel文件
        df = pd.read_excel('date.xlsx', sheet_name='Sheet1')
        book = openpyxl.load_workbook('date.xlsx')
        sheet = book['Sheet1'] # 选择工作表

        print("总行数len(df) = ", len(df))
        for cur_row in range(0, len(df)):
            cell_coordinate = 'C' + str(cur_row + 2)
            print("sheet[cell_coordinate].value: ", cell_coordinate, sheet[cell_coordinate].value)
            if sheet[cell_coordinate].value is not None:
                continue

            cur_tick = df.at[cur_row, "ID"]

            tick_num = 0
            print("当前cur_row = ", cur_row, "; 当前tick = ", cur_tick)
            for record_row in range(0, cur_row):
                data_diff = df.at[cur_row, "DATE"] - df.at[record_row , "DATE"]
                # print("record_row = ", record_row, "; data_diff = ", data_diff, "; 是否最近一年 = ",data_diff <= datetime.timedelta(days=365))

                if data_diff > datetime.timedelta(days=365):
                    continue

                if cur_tick == df.at[record_row, "ID"]:
                    tick_num += 1

            print("当前cur_row = ", cur_row, "; 当前tick = ", cur_tick, "; 最终tick_num = ", tick_num)
            df.at[cur_row, "COUNT"] = tick_num


            sheet[cell_coordinate] = tick_num # 将A1单元格的值修改为10
            comment = Comment(datetime.datetime.now(), author='pytool')
            sheet[cell_coordinate].comment = comment

        # 保存并关闭Excel文件
        book.save('date.xlsx')

if __name__== "__main__" :
    cnt = CalcLast1YearCount()
    cnt.count()