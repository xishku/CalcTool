#!/usr/bin/python#

#-*-coding:UTF-8-*-

# -i https://pypi.tuna.tsinghua.edu.cn/simple

import os
import datetime
import pandas as pd
import numpy

import openpyxl
from openpyxl.comments import Comment
from .logger import Logger
from .tdx_data_agent import TdxDataAgent
from .data_online import TdxOnlineHqAgent


class CalcLast1YearCount:
    
    def __init__(self, kdata_src = 0):
        self._kdata_src = int(kdata_src) # 0 from online; 1 from tdx local lday
        Logger.log().info(f"self._kdata_src = {self._kdata_src}")
        

    def _FormatTime2Str(self, date_time):
        if date_time is None:
            return ""
        
        if not isinstance(date_time, datetime.datetime):
            return ""
        
        return f"{date_time.strftime("%Y-%m-%d %H:%M:%S")}"

    def _FormatDate2Str(self, date_time):
        if date_time is None:
            return ""
        
        if not isinstance(date_time, datetime.datetime):
            return ""
    
        return f"{date_time.strftime("%Y%m%d")}"  

    def _IsTickRight(self, tick, row):
        if not isinstance(tick, numpy.float64):
            Logger.log().warning(f"{type(tick)}, invalid tick = {tick}, row = {row}")
            return False
        
        if numpy.isnan(tick):
            Logger.log().warning(f"{type(tick)}, invalid tick = {tick}, row = {row}")
            return False
        
        return True

    def WriteCount2Sheet(self, count: dict, sheet):
        if len(count) == 0:
            Logger.log().info("从下往上更新，遇到大于0的结束，没有需要更新的数据")
            return
        
        for key, value in count.items():
            cell_coordinate = 'AD' + str(key + 2)
            if value == sheet[cell_coordinate].value:
                continue

            log_txt = f"Key: {cell_coordinate}, oldValue: {sheet[cell_coordinate].value}, Value: {value}"
            Logger.log().info(log_txt)
            sheet[cell_coordinate] = value # 将A1单元格的值修改为10
            comment = Comment(f"{self._FormatTime2Str(datetime.datetime.now())}, {log_txt}", author='pytool')
            sheet[cell_coordinate].comment = comment

    def FormatDate(self, date_num):
        return datetime.date(year=date_num // 10000, month=(date_num % 10000) // 100, day=date_num % 100)


    def WriteExtreme2Sheet(self, extreme: dict, sheet):
        Logger.log().info(f"len(extreme) = {len(extreme)}")
        if len(extreme) == 0:
            Logger.log().info("从下往上更新，遇到大于0的结束，没有需要更新的数据")
            return
        
        for key, value in extreme.items():
            if value[0] is None:
                Logger.log().warning("获取除权数据失败")
                break
            
            if value[1] is None:
                Logger.log().warning("获取前复权数据失败")
                break

            if value[2] is None:
                Logger.log().warning("获取后复权数据失败")
                break
            
            row = str(key + 2)
            sheet['Q' + row] = value[0][0]
            sheet['R' + row] = self.FormatDate(int(value[0][1]))
            sheet['S' + row] = value[0][2]
            sheet['T' + row] = self.FormatDate(int(value[0][3]))
            sheet['U' + row] = value[0][4]

            sheet['V' + row] = value[1][0]
            sheet['W' + row] = self.FormatDate(int(value[1][1]))
            sheet['X' + row] = value[1][2]
            sheet['Y' + row] = self.FormatDate(int(value[1][3]))

            sheet['Z' + row] = value[2][0]
            sheet['AA' + row] = self.FormatDate(int(value[2][1]))
            sheet['AB' + row] = value[2][2]
            sheet['AC' + row] = self.FormatDate(int(value[2][3]))

            sheet['AL' + row] = value[3][0]
            sheet['AM' + row] = value[3][0] / value[0][4]
            sheet['AO' + row] = value[3][1]
            sheet['AP' + row] = value[3][1] / value[0][4]

    @staticmethod
    def can_convert_to_int(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def read_data_2_cache(self, df, data_cache):
        for cur_row in range(len(df) - 1, -1, -1):
            src_tick = df.at[cur_row, "代码"]
            if not CalcLast1YearCount.can_convert_to_int(src_tick):
                continue

            cur_tick = int(src_tick)
            Logger.log().debug(f"src_tick = {src_tick} type(src_tick) = {type(src_tick)} type(cur_tick) = {type(cur_tick)}")
            
            # if not self._IsTickRight(cur_tick, cur_row):
            #     continue

            date_str = self._FormatDate2Str(df.at[cur_row , "日期"])
            if date_str not in data_cache:
                data_cache[date_str] = set()

            data_cache[date_str].add(cur_tick)

            Logger.log().debug(f'Key: {date_str}, Value: {cur_tick}')
            if cur_tick == "300960":
                Logger.log().info(f'Key: {date_str}, Value: {cur_tick}')

    def prepare_data(self, df, hot_set_list, data_cache, count_cache, extreme_cache, hot_cache):
        for cur_row in range(len(df) - 1, -1, -1):
        # for cur_row in (17488, 0):
            src_tick = df.at[cur_row, "代码"]
            if not CalcLast1YearCount.can_convert_to_int(src_tick):
                continue

            cur_tick = int(src_tick)
            # Logger.log().info(f"{cur_row} {cur_tick}")
            # if not self._IsTickRight(cur_tick, cur_row):
            #     continue

            cur_count = df.at[cur_row, "最近一年出现次数"]
            if cur_count > 0:
                break

            # cell_coordinate = 'R' + str(cur_row + 2)

            tick_num = 0
            for day in range(365, 0, -1):
                target_date_tmp = self._FormatDate2Str(df.at[cur_row, "日期"] - datetime.timedelta(days=day))
                Logger.log().debug(f"{target_date_tmp}")
                if target_date_tmp in data_cache:
                    Logger.log().debug("日期存在")
                    if cur_tick in data_cache[target_date_tmp]:
                        Logger.log().debug("tick存在")
                        tick_num += 1
                    else:
                        Logger.log().debug("tick不存在")
        
            date_cur = df.at[cur_row, "日期"]
            date_target = df.at[cur_row, "目标日期"]
            date_t2 = date_cur + datetime.timedelta(days=2)
            cur_date = self._FormatDate2Str(date_cur)
            target_date = self._FormatDate2Str(date_target)
            t2_date = self._FormatDate2Str(date_t2)
            Logger.log().info(f"cur_row = {cur_row}, cur_date = {cur_date}，target_date= {target_date}, 当前tick = {cur_tick}, 最终tick_num = {tick_num}")
            count_cache[cur_row] = tick_num
            
            agent = TdxDataAgent()
            code = str(int(cur_tick)).zfill(6)
            df_kdata = None
            Logger.log().debug(f"self._kdata_src = {self._kdata_src} type(self._kdata_src) = {type(self._kdata_src)}")
            if self._kdata_src == 0:
                t2_str = date_t2.strftime("%Y-%m-%d")
                target_str = date_target.strftime("%Y-%m-%d")
                Logger.log().debug(f"code = {code} t2_str = {t2_str} target_str = {target_str}")
                df_kdata = agent.read_online_kdata(code, t2_str, target_str)
            else:
                df_kdata = agent.read_kdata_cache(code)
            
            if df_kdata is None or len(df_kdata) == 0:
                Logger.log().error(f"没有正确获取到df_kdata")

            Logger.log().debug(f"str(cur_tick) = {str(cur_tick)} df_kdata = {df_kdata}") 
            if not df_kdata.empty:
                xdxr = TdxOnlineHqAgent().get_xdxr_info(str(cur_tick))
                origin = agent.get_extreme_between_days(str(cur_tick), df_kdata, int(t2_date), int(target_date), xdxr)
                pre = agent.get_pre_extreme_between_days(str(cur_tick), df_kdata, int(t2_date), int(target_date), xdxr)
                post = agent.get_post_extreme_between_days(str(cur_tick), df_kdata, int(t2_date), int(target_date), xdxr)

                base_price = df.at[cur_row, "收盘价"]
                tp_price = base_price * (1 + df.at[cur_row, "止盈线"])
                sl_price = base_price * (1 + df.at[cur_row, "止损线"])
                tpsl = agent.get_post_takeprofit_stoploss_between_days(df_kdata, int(t2_date), int(target_date), xdxr, tp_price, sl_price)
                extreme_cache[cur_row] = (origin, pre, post, tpsl)
                

            cur_tick
            hot_cache[cur_row] = 0
            for index, element in enumerate(hot_set_list):
                # Logger.log().info(f"index = {index} type(element) = {type(element)}")
                if int(cur_tick) in element:
                    hot_cache[cur_row] |= (1 << index)

    def write_hotmap_2_sheet(self, hot_map_df, hot_cache, sheet):
        if len(hot_cache) == 0:
            Logger.log().info("从下往上更新，遇到大于0的结束，没有需要更新的数据")
            return
        
        hot_map = dict()
        for cur_row in range(len(hot_map_df)):
            hot_name = hot_map_df.at[cur_row, "热点"]
            sheet_name = hot_map_df.at[cur_row, "sheet名称"]
            hot_map[cur_row] = hot_name
            Logger.log().info(f"cur_row = {cur_row} hot_name = {hot_name} sheet_name = {sheet_name}")

        for key, value in hot_cache.items():
            label = ""
            for bit_index in range(5):
                if (1 << bit_index) & value == (1 << bit_index):
                    label += hot_map[bit_index] + ";"
            
            if label == "":
                continue

            row = str(key + 2)
            sheet['AE' + row] = label
            Logger.log().info(f"write to {'AE' + row} : {label}")
     

    def prepare_hot_set(self, hot_df):
        hot_set = set()
        for cur_row in range(len(hot_df) - 1, -1, -1): 
            src_tick = hot_df.at[cur_row, "代码"]
            if not CalcLast1YearCount.can_convert_to_int(src_tick):
                continue
            
            hot_set.add(int(src_tick))
            # Logger.log().info(f"add to hot set: {src_tick} then len(hot_set) = {len(hot_set)}")

        return hot_set

    def count(self, src_file, dst_file, sheet_name):
        from pathlib import Path
 
        file_path = Path(src_file)
        if not (file_path.exists() and file_path.is_file()):
            err = f"文件不存在{src_file}"
            raise Exception(err)

        # 读取Excel文件
        Logger.log().info("打开文件: %s" % src_file)

        df = pd.read_excel(src_file, sheet_name=sheet_name, dtype=({"代码": str}))
        hot_map_df = pd.read_excel(src_file, sheet_name="概念映射", dtype=({"代码": str}))

        hot_map = dict()
        hot_set_list = []
        for cur_row in range(len(hot_map_df)):
            hot_sheet_name = hot_map_df.at[cur_row, "sheet名称"]
            hot_map[cur_row] = hot_sheet_name
            Logger.log().info(f"cur_row = {cur_row} hot_sheet_name = {hot_sheet_name}")

            hot_df = pd.read_excel(src_file, sheet_name=hot_sheet_name, dtype=({"代码": str}))
            hot_set = self.prepare_hot_set(hot_df)
            hot_set_list.append(hot_set)
            Logger.log().info(f"len(hot_set) = {len(hot_set)} len(hot_set_list) = {len(hot_set_list)}")

        # blackhorse_df = pd.read_excel(src_file, sheet_name="黑马", dtype=({"代码": str}))
        # hot1_df = pd.read_excel(src_file, sheet_name="概念1", dtype=({"代码": str}))
        # hot2_df = pd.read_excel(src_file, sheet_name="概念2", dtype=({"代码": str}))
        # hot3_df = pd.read_excel(src_file, sheet_name="概念3", dtype=({"代码": str}))
        # hot4_df = pd.read_excel(src_file, sheet_name="概念4", dtype=({"代码": str}))

        # balckhorse_set = self.prepare_hot_set(blackhorse_df)
        # hot1_set = self.prepare_hot_set(hot1_df)
        # hot2_set = self.prepare_hot_set(hot2_df)
        # hot3_set = self.prepare_hot_set(hot3_df)
        # hot4_set = self.prepare_hot_set(hot4_df)

        # hot_set_tuple = (balckhorse_set, hot1_set, hot2_set, hot3_set, hot4_set)

        # Logger.log().info(f"{hot_map_df} {hot1_df} {hot2_df} {hot2_df} {hot3_df}")
        Logger.log().info("打开文件完成: %s" % src_file)

        count_cache = dict()
        extreme_cache = dict()
        hot_cache = dict()
        print("总行数len(df) = ", len(df))

        data_cache = dict()
        self.read_data_2_cache(df, data_cache)
        
        Logger.log().info(f"len(data_cache) = {len(data_cache)}")
        for key, value in data_cache.items():
            for tick in value:
                Logger.log().debug(f'Key: {key}, Value: {tick}')
                            
                if tick == "300960":
                    Logger.log().info(f'Key: {key}, Value: {tick}')
    
        
        self.prepare_data(df, hot_set_list, data_cache, count_cache, extreme_cache, hot_cache)

        # 保存并关闭Excel文件
        Logger.log().debug(f"count_cache = {count_cache} extreme_cache = {extreme_cache}")

        Logger.log().info("Load workbook: %s" % src_file)
        book = openpyxl.load_workbook(src_file)
        Logger.log().info("Load workbook完成: %s" % src_file)
        sheet = book[sheet_name] # 选择工作表
     
        try:
            self.WriteCount2Sheet(count_cache, sheet)
            self.WriteExtreme2Sheet(extreme_cache, sheet)
            self.write_hotmap_2_sheet(hot_map_df, hot_cache, sheet)

        finally:
            # 保存并关闭Excel文件
            Logger.log().info("save workbook: %s" % dst_file)
            book.save(dst_file)
            book.close()
            Logger.log().info("save workbook完成: %s" % dst_file)
            a = TdxOnlineHqAgent()
            a.close_connection()
            a = None


if __name__== "__main__" :
    src_file = os.path.join(os.path.dirname(
                os.path.realpath(__file__)), '2024条件选股x.xlsx')
    dst_file = os.path.join(os.path.dirname(
            os.path.realpath(__file__)), '2024条件选股x1.xlsx')
    Logger.log().info("开始打开文件: %s" % src_file)
    cnt = CalcLast1YearCount()
    cnt.count(src_file, dst_file, '条件选股2021')
    Logger.log().info("处理完成")
