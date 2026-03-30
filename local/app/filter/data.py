
import os
import sys
from typing import override

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
    # 自动测速并返回最优服务器IP和端口
    # best_ip_info = select_best_ip()
    # print(f"最优服务器: IP={best_ip_info['ip']}, 端口={best_ip_info['port']}")    
    print("return:", TdxSetting.get_value("tdx_server"), )

    # 方式1：让工厂决定
    tick = "601398"
    t0_date = 20260301
    tn_date = 20260330
    stock1 = Stock.create(tick)
    print(type(stock1))  # <class '__main__.StockLocal'>

    api = TdxHq_API(heartbeat=True, auto_retry=True)
    with api.connect(TdxSetting.get_value("tdx_server"), TdxSetting.get_value("tdx_port")):
        print("OK")
        # data = api.get_security_bars(9, 0, '000001', 0, 10) #返回普通list
        # print(data)
        data = api.to_df(api.get_security_bars(9, 0, tick, 0, 10)) # 返回DataFrame
        # print(data)
        xdxr = api.get_xdxr_info(1, tick)

        print(type(xdxr))
        # for item in xdxr:
        #     print(item)

        df_kdata = stock1.load_k_data(t0_date, tn_date)
        # print(df_kdata)

        if df_kdata is None or len(df_kdata) == 0 or df_kdata.empty:
            Logger.log().error(f"没有正确获取到df_kdata")
        else:
            Logger.log().debug(f"str(cur_tick) = {str(tick)} df_kdata = {df_kdata}") 

        
            xdxr = TdxOnlineHqAgent().get_xdxr_info(str(tick))

            # 前复权
            preadj_df = df_kdata.copy()
            TdxDataAgent().pre_adj(preadj_df, xdxr, int(t0_date), int(tn_date))
            print(preadj_df)
