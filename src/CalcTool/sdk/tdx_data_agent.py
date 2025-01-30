#!/usr/bin/python#

#-*-coding:UTF-8-*-

# -i https://pypi.tuna.tsinghua.edu.cn/simple

import os
import datetime
import pandas as pd
import numpy as np
import datetime

from .logger import Logger
from .data_online import TdxOnlineHqAgent
from .timeit_decorator import Dec


TDX_BASE = 'C:/new_tdx'

DAY_K_TYPE = np.dtype([
        ('date', 'u4'),
        ('open', 'u4'),
        ('high', 'u4'),
        ('low', 'u4'),
        ('close', 'u4'),
        ('amount', 'f'),
        ('volume', 'u4'),
        ('res', 'u4')])

class TdxDataAgent:    
    def get_exchcode(self, qkey):
        if qkey[0] == '6':
            excode = 'sh'
        else:
            excode = 'sz'

        return excode

    def get_tdxfn(self, qkey, dtype):
        excode = self.get_exchcode(qkey)
        if dtype == 'd':
            fn = '%s/vipdoc/%s/lday/%s%s.day' % (TDX_BASE, excode, excode, qkey)
        elif dtype == '5min':
            fn = '%s/vipdoc/%s/fzline/%s%s.lc5' % (TDX_BASE, excode, excode, qkey)

        if os.path.exists(fn):
            return fn
        else:
            return None

    @Dec.timeit_decorator
    def read_kdata_cache(self, qkey):
        Logger.log().debug(f"qkey = {qkey}")
        fn = self.get_tdxfn(qkey, 'd')
        if not fn: 
            return pd.DataFrame()

        data = np.fromfile(fn, dtype=DAY_K_TYPE)
        df = pd.DataFrame(data, columns=data.dtype.names)
        df = df.sort_values('date').reset_index(drop=True)
        df['preclose'] = df['close'].shift()
        df['r_open'] = df['open'] / 100
        df['r_high'] = df['high'] / 100
        df['r_low'] = df['low'] / 100
        df['r_close'] = df['close'] / 100
        df['r_date'] = df['date']
    
        return df
    
    @Dec.timeit_decorator
    def read_online_kdata(self, code, start_date: str, end_date: str):
        df = TdxOnlineHqAgent().get_kdata(code, start_date, end_date)
        if df is None: 
            return pd.DataFrame()
        
        date_format = "%Y-%m-%d"

        df['preclose'] = df['close'].shift()
        df['r_open'] = df['open']
        df['r_high'] = df['high']
        df['r_low'] = df['low']
        df['r_close'] = df['close']
        df['r_date'] = 0

        for index, item in df.iterrows():
            # Logger.log().info(type(item['date']))
            df.loc[index, "r_date"] = int(datetime.datetime.strptime(item['date'], "%Y-%m-%d").strftime("%Y%m%d"))
        

        return df
    
    def value_post_adj(self, src_value, fenhong, songzhuanggu):
        return src_value * (songzhuanggu + 10) / 10 + fenhong / 10

    def post_adj(self, data_df, xdxr, start_date, end_date):
        if xdxr is None:
            return

        for row in xdxr:
            # print("row = ", type(row), row)
            if row["category"] != 1:
                continue

            year = row["year"]
            month = row["month"]
            day = row["day"]
            date = datetime.date(year=year, month=month, day=day)
            date_format = date.strftime("%Y%m%d")
            date_num = int(date_format)

            # 只处理开始时间之后和结束之前的除权除息，之前的忽略
            if date_num < start_date or date_num > end_date:
                continue

            fenhong = row["fenhong"]
            songzhuanggu = row["songzhuangu"]

            for index, item in data_df.iterrows():
                # 前复权仅仅处理除权当天及以后的，包括当天，因为当天已经除权
                if item["r_date"] < date_num:
                    continue

                data_df.loc[index, 'r_high']= self.value_post_adj(item['r_high'], fenhong, songzhuanggu)
                data_df.loc[index, 'r_low'] = self.value_post_adj(item['r_low'], fenhong, songzhuanggu)
                data_df.loc[index, 'r_open'] = self.value_post_adj(item['r_open'], fenhong, songzhuanggu)
                data_df.loc[index, 'r_close'] = self.value_post_adj(item['r_close'], fenhong, songzhuanggu)

    def value_pre_adj(self, src_value, fenhong, songzhuanggu):
        return (src_value - fenhong / 10) * 10 / (songzhuanggu + 10) 

    def pre_adj(self, data_df, xdxr, start_date, end_date):
        if xdxr is None:
            return
        
        for row in xdxr:
            # print("row = ", type(row), row)
            if row["category"] != 1:
                continue

            year = row["year"]
            month = row["month"]
            day = row["day"]
            date = datetime.date(year=year, month=month, day=day)
            date_format = date.strftime("%Y%m%d")
            date_num = int(date_format)

            # 只处理开始时间之后和结束之前的除权除息，之前的忽略
            if date_num < start_date or date_num > end_date:
                continue

            fenhong = row["fenhong"]
            songzhuanggu = row["songzhuangu"]

            for index, item in data_df.iterrows():
                # 前复权仅仅处理除权当天以前的，不包括当天
                if item["r_date"] >= date_num:
                    continue

                data_df.loc[index, 'r_high']= self.value_pre_adj(item['r_high'], fenhong, songzhuanggu)
                data_df.loc[index, 'r_low'] = self.value_pre_adj(item['r_low'], fenhong, songzhuanggu)
                data_df.loc[index, 'r_open'] = self.value_pre_adj(item['r_open'], fenhong, songzhuanggu)
                data_df.loc[index, 'r_close'] = self.value_pre_adj(item['r_close'], fenhong, songzhuanggu)
    
    @Dec.timeit_decorator
    def get_extreme_value(self, code, result_df, start_date, end_date, adj_function = None, xdxr = None):
        if result_df.shape[0] == 0:
            return None
        
        # agent = TdxOnlineHqAgent()
        # xdxr = agent.get_xdxr_info(code)
        # self.post_adj(result_df, xdxr, start_date)
        if adj_function is not None:
            adj_function(result_df, xdxr, start_date, end_date)
        
        # 找出列'A'中最大值所在的行的索引
        max_index = result_df['r_high'].idxmax()
        # 使用loc方法根据索引获取包含最大值的整行数据
        row_with_max = result_df.loc[max_index]
        highest =  row_with_max["r_high"]
        highest_date =  row_with_max["r_date"]
        Logger.log().debug(f"highest = {highest} highest_date = {highest_date}") 

        low_index = result_df['r_low'].idxmin()
        row_with_low = result_df.loc[low_index]
        lowest = row_with_low['r_low']
        lowest_date = row_with_low["r_date"]
        Logger.log().debug(f"lowest = {lowest} lowest_date = {lowest_date}") 
        return (highest, highest_date, lowest, lowest_date, len(result_df))

    def get_extreme_in_days(self, code, df, cur_day, days):
        dt_from_str = datetime.datetime.strptime(str(cur_day), "%Y%m%d")
        Logger.log().info(f"{dt_from_str}")
        dt_from_str -= datetime.timedelta(days=days)
        Logger.log().info(f"{dt_from_str}")
        target_day_str = dt_from_str.strftime("%Y%m%d")
        Logger.log().info(f"{target_day_str}")
        threshold = int(target_day_str)
 
        Logger.log().info(f"threshold = {threshold}")
        filtered_df = df[df['r_date'] > threshold]
        result_df = filtered_df[filtered_df['r_date'] <= cur_day]
        Logger.log().info(f"result_df count= {len(result_df)}")
        # Logger.log().info(f"result_df = {result_df}")
        agent = TdxOnlineHqAgent()
        xdxr = agent.get_xdxr_info(code)
        return self.get_extreme_value(code, result_df, threshold, cur_day, None, xdxr)

    # 是否除权除息
    # T+1买，最早T+2买
    def get_extreme_between_days(self, code, df, current_day, target_day, xdxr):
        if df is None or df.empty:
            return None
        
        filtered_df = df[df['r_date'] <= target_day]
        result_df = filtered_df[filtered_df['r_date'] >= current_day]

 
        return self.get_extreme_value(code, result_df, current_day, target_day, None, xdxr)
    
    def get_post_extreme_between_days(self, code, df, current_day, target_day, xdxr):
        if df is None or df.empty:
            return None
        
        filtered_df = df[df['r_date'] <= target_day]
        result_df = filtered_df[filtered_df['r_date'] >= current_day]

        return self.get_extreme_value(code, result_df, current_day, target_day, self.post_adj, xdxr)
    
    def get_pre_extreme_between_days(self, code, df, current_day, target_day, xdxr):
        if df is None or df.empty:
            return None
        
        filtered_df = df[df['r_date'] <= target_day]
        result_df = filtered_df[filtered_df['r_date'] >= current_day]

        return self.get_extreme_value(code, result_df, current_day, target_day, self.pre_adj, xdxr)
    
    def get_extreme_in_tradingdays(self, code, df, cur_day, days):
        if days < 0:
            return None
        
        if df is None or df.empty:
            return None
        
        filtered_df = df[df['r_date'] <= cur_day]
        result_df = filtered_df.tail(days)
        agent = TdxOnlineHqAgent()
        xdxr = agent.get_xdxr_info(code)
        return self.get_extreme_value(code, result_df, cur_day - days, cur_day, None, xdxr)

if __name__== "__main__" :
    # print(read_kdata('000001'))
    agent = TdxDataAgent()

    df = agent.read_kdata('601816')
    print(df['date'][0], df['date'][0] == 20200116)
    agent.get_extreme_in_days(df, 20250106, 20)