#!/usr/bin/python
#-*-coding:UTF-8-*-

import os
from .stock_model import StockDataRecord


class StockDataParser:
    """股票数据解析器"""
    
    def __init__(self):
        self.data = []
        self.file_path = None
    
    def parse(self, file_path):
        """解析文件数据"""
        self.file_path = file_path
        self.data = []
        
        if not self.file_path or not os.path.exists(self.file_path):
            return False, "请选择有效的文件"
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) < 3:
                        continue
                    
                    timestamp_str = parts[0]
                    stock_code = parts[1]
                    focus_dates = parts[2:]
                    
                    for focus_date in focus_dates:
                        if focus_date:
                            record = StockDataRecord(
                                timestamp=timestamp_str,
                                stock_code=stock_code,
                                focus_date=focus_date,
                                full_data=line
                            )
                            self.data.append(record)
            
            return True, f"解析完成，共处理 {len(self.data)} 条记录"
            
        except Exception as e:
            return False, f"解析文件时出错: {e}"
    
    def get_data(self):
        """获取解析后的数据"""
        return self.data
    
    def filter_data(self, stock_filter='', date_filter=''):
        """过滤数据"""
        filtered_data = self.data
        
        if stock_filter:
            filtered_data = [r for r in filtered_data 
                           if stock_filter in r.stock_code]
        
        if date_filter:
            filtered_data = [r for r in filtered_data 
                           if date_filter in r.focus_date]
        
        return filtered_data