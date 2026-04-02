
#!/usr/bin/python
#-*-coding:UTF-8-*-

import os
import sys
import argparse

from kline_viewer import KLineViewer

def main():
    """命令行入口点"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票K线图查看器')
    parser.add_argument('--stock', type=str, default='601398', help='股票代码')
    parser.add_argument('--start', type=str, default='20260101', help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, default='20260401', help='结束日期 (YYYYMMDD)')
    parser.add_argument('--target', type=str, help='默认定位到的目标日期 (YYYYMMDD 或 YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # 创建查看器并显示
    viewer = KLineViewer(
        stock_code=args.stock,
        start_date=args.start,
        end_date=args.end,
        target_date=args.target
    )
    
    viewer.show()


if __name__ == '__main__':
    main()