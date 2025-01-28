#!/usr/bin/python#

#-*-coding:UTF-8-*-

import os
import sys

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger

if __name__== "__main__" :
    # sys.argv[0] 是脚本的名称
    script_name = sys.argv[0]
    print(script_name)
    # 从 sys.argv[1] 开始是传递给脚本的参数

    if len(sys.argv) < 4:
        raise Exception("传入参数不够")

    src_file = sys.argv[1]
    dst_file = sys.argv[2]
    sheet_name = sys.argv[3]
    
    print(f"Script name: {script_name}")
    Logger.log().info(f"{src_file} {dst_file} {sheet_name}")

    # src_file = os.path.join(os.path.dirname(
    #             os.path.realpath(__file__)), '2024条件选股x.xlsx')
    # dst_file = os.path.join(os.path.dirname(
    #         os.path.realpath(__file__)), '2024条件选股x1.xlsx')
    # Logger.log().info("开始打开文件: %s" % src_file)
    cnt = CalcLast1YearCount()
    cnt.Count(src_file, dst_file, '条件选股2021')
    Logger.log().info("处理完成")
