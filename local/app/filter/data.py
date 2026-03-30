
import os
import sys
from typing import override
import datetime

from pytdx.hq import TdxHq_API
from pytdx.util.best_ip import select_best_ip

print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.setting import TdxSetting
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
from CalcTool.sdk.data_online import TdxOnlineHqAgent


class Stock(object):
    def __init__(self, code):
        self._code = code

    def load_k_data(self, start_data, end_date):
        return None

    @classmethod
    def create(cls, code, source: str = 'local') -> 'Stock':
        """
        工厂方法：根据条件创建不同的Stock子类对象
        Args:
            code: 股票代码
            source: 数据源类型，可选 'local' 或 'online'，默认为配置决定
        Returns:
            Stock实例
        """
        if source is None:
            # 从环境变量或配置文件决定
            source = os.environ.get('STOCK_DATA_SOURCE', 'local')
        
        if source.lower() == 'local':
            return StockLocal(code)
        elif source.lower() == 'online':
            return StockOnline(code)
        else:
            raise ValueError(f"不支持的数据源: {source}")
    
    def find_up_day(self, t0_date, tn_date):
        df_kdata = self.load_k_data(t0_date, tn_date)

        if df_kdata is None or len(df_kdata) == 0 or df_kdata.empty:
            Logger.log().error(f"没有正确获取到df_kdata")
        else:
            Logger.log().debug(f"str(cur_tick) = {str(self._code)} df_kdata = {df_kdata}") 

        xdxr = TdxOnlineHqAgent().get_xdxr_info(str(self._code))
        # print(xdxr)

        # 前复权
        preadj_df = df_kdata.copy()
        TdxDataAgent().pre_adj(preadj_df, xdxr, int(t0_date), int(tn_date))
        # simple_cols = ['date', 'r_close', 'volume', 'preclose', 'r_preclose']
        # print(preadj_df[simple_cols])

        count = 0
        threshold_high = 0.03
        threshold_low = 0.01
        matched_data = list()
        for i in range(len(preadj_df)):
            percent = preadj_df.loc[i, 'r_close'] / preadj_df.loc[i, 'r_preclose'] - 1

            if percent < threshold_high and percent > threshold_low:
                count += 1
            else:
                count = 0
            
            # if count >= 1:
            #     print(f"{preadj_df.loc[i, 'date']:.2f}\t\
            #     {preadj_df.loc[i, 'r_close']:.2f}\t\
            #     {preadj_df.loc[i, 'r_preclose']:.2f}\t\
            #     {percent:.4f}\
            #     ")
            # else:
            #     print(i, count)

            if count >= 3:
                matched_data.append(preadj_df.loc[i, 'date'])

        if len(matched_data) == 0:
            return

        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "list.txt"), mode="a", newline="", encoding="utf-8") as file:
            file.write(f"\n{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}\t{self._code}\t")
            file.write('\t'.join(str(item) for item in matched_data))


class StockLocal(Stock):
    def __init__(self, code):  # pyright: ignore[reportMissingSuperCall]
        super().__init__(code)
    
    @override
    def load_k_data(self, start_data, end_date):
        agent = TdxDataAgent()
        return agent.read_kdata_cache(self._code, start_data, end_date)

class StockOnline(Stock):
    def __init__(self, code):  # pyright: ignore[reportMissingSuperCall]
        super().__init__(code)

    @override
    def load_k_data(self, start_data, end_date):
        agent = TdxDataAgent()
        df_kdata = agent.read_online_kdata(self._code, start_data, end_date)
        return None


if __name__ == '__main__':
    tick = "000011"
    t0_date = 20260301
    tn_date = 20260330
    stock1 = Stock.create(tick)
    stock1.find_up_day(t0_date, tn_date)
    Logger.log().info("finished")
  

