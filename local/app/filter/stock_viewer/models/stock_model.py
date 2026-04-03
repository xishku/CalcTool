#!/usr/bin/python
#-*-coding:UTF-8-*-

from datetime import datetime, timedelta


class StockDataRecord:
    """股票数据记录"""
    
    def __init__(self, timestamp='', stock_code='', focus_date='', full_data=''):
        self.timestamp = timestamp
        self.stock_code = stock_code
        self.focus_date = focus_date
        self.full_data = full_data
    
    def to_dict(self):
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'stock_code': self.stock_code,
            'focus_date': self.focus_date,
            'full_data': self.full_data
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            timestamp=data.get('timestamp', ''),
            stock_code=data.get('stock_code', ''),
            focus_date=data.get('focus_date', ''),
            full_data=data.get('full_data', '')
        )


class StockStats:
    """股票数据统计"""
    
    def __init__(self):
        self.total_records = 0
        self.unique_stocks = 0
        self.date_range = []
        self.file_name = ""
        self.date_counts = {}
    
    def calculate(self, data_records, file_name):
        """计算统计数据"""
        self.total_records = len(data_records)
        self.unique_stocks = len(set(record.stock_code for record in data_records))
        self.date_range = sorted(set(record.focus_date for record in data_records))
        self.file_name = file_name
        
        # 统计每个日期的记录数
        self.date_counts = {}
        for record in data_records:
            date = record.focus_date
            self.date_counts[date] = self.date_counts.get(date, 0) + 1
        
        return self
    
    def get_stats_text(self, limit=20):
        """获取统计文本"""
        if not self.date_range:
            return "无数据"
        
        min_date = min(self.date_range) if self.date_range else "N/A"
        max_date = max(self.date_range) if self.date_range else "N/A"
        
        stats_text = f"=== 数据统计 ===\n"
        stats_text += f"总记录数: {self.total_records}\n"
        stats_text += f"唯一股票数: {self.unique_stocks}\n"
        stats_text += f"日期范围: {min_date} 到 {max_date}\n"
        stats_text += f"数据文件: {self.file_name}\n"
        
        stats_text += "=== 日期分布 ===\n"
        stats_text += "-" * 30 + "\n"
        
        # 只显示前limit个日期的统计
        sorted_dates = sorted(self.date_counts.items(), key=lambda x: x[0])
        for date, count in sorted_dates[:limit]:
            stats_text += f"{date}: {count} 条记录\n"
        
        if len(self.date_counts) > limit:
            stats_text += f"... 还有 {len(self.date_counts) - limit} 个日期\n"
        
        return stats_text