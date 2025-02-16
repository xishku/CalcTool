from pytdx.hq import TdxHq_API 
from pytdx.util.best_ip import select_best_ip
from .logger import Logger
from .timeit_decorator import Dec


def get_best_tdx_server():    
    """    自动检测最快的通达信服务器地址和端口    :return: 最佳服务器的 IP 和端口    """    
    best_ip = select_best_ip()    
    print(f"最佳服务器：{best_ip['ip']}:{best_ip['port']}")    
    return best_ip['ip'], best_ip['port']

def connect_to_tdx(ip, port):    
    """    连接通达信服务器    :param ip: 服务器 IP 地址    :param port: 服务器端口号    :return: 成功返回 API 对象，失败返回 None    """    
    api = TdxHq_API()    
    try:        
        if api.connect(ip, port):
            print(f"成功连接到通达信服务器 {ip}:{port}") 
            return api        
        else:            
            print(f"连接通达信服务器失败 {ip}:{port}")   
            return None    
    except Exception as e:        
        print(f"连接过程中出现异常: {e}")        
        return None
    
def get_realtime_data(api, market, stock_code):    
    """    获取实时行情数据    :param api: TdxHq_API对象    :param market: 市场代码 (0=深圳, 1=上海)    :param stock_code: 股票代码    """    
    try:        
        data = api.get_security_quotes([(market, stock_code)])        
        print("实时行情数据：", data)        
        return data    
    except Exception as e:        
        print(f"获取实时行情数据失败: {e}")        
        return None
    
def main():    # 自动获取最快的通达信服务器地址和端口    
    ip, port = get_best_tdx_server()    # 连接通达信服务器    
    api = connect_to_tdx(ip, port)    
    if not api:        
        return    # 获取实时行情数据    
    
    market = 0  # 深圳市场    
    stock_code = '000001'  # 平安银行    
    realtime_data = get_realtime_data(api, market, stock_code)    # 断开连接    
    api.disconnect()    
    print("已断开与通达信服务器的连接")

class SingletonMeta(type):
    _instances = {}
 
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Singleton(metaclass=SingletonMeta):
    pass

class TdxOnlineHqAgent(Singleton):
    def __init__(self):
        self.api = TdxHq_API(heartbeat=True, auto_retry=True)
        self.connect = self.api.connect('121.36.81.195', 7709)
        Logger.log().info(f"TdxOnlineHqAgent.__init__ self = {id(self)}")

    def __del__(self):
        self.connect.close()

    def close_connection(self):
        self.connect.close()

        

    @Dec.timeit_decorator
    def get_security_list(self, market, start):
        # api = TdxHq_API(heartbeat=True, auto_retry=True)
        try:
            # with api.connect('121.36.81.195', 7709):
            xdxr = self.api.get_security_list(market, start)
            return xdxr
        except:
            Logger.log().error("get_xdxr_info 网络问题重连中")
            self.connect.close()
            self.connect = self.api.connect('121.36.81.195', 7709)
            return self.get_security_list(market, start)

    @Dec.timeit_decorator
    def get_finance_info(self, code: str):
        # api = TdxHq_API(heartbeat=True, auto_retry=True)
        try:
            # with api.connect('121.36.81.195', 7709):
            xdxr = self.api.get_finance_info(self.get_mkt_code(code), code)
            return xdxr
        except:
            Logger.log().error("get_xdxr_info 网络问题重连中")
            self.connect.close()
            self.connect = self.api.connect('121.36.81.195', 7709)
            return self.get_finance_info(code)
        

    @Dec.timeit_decorator
    def get_xdxr_info(self, code: str):
        # api = TdxHq_API(heartbeat=True, auto_retry=True)
        try:
            # with api.connect('121.36.81.195', 7709):
            xdxr = self.api.get_xdxr_info(self.get_mkt_code(code), code)
            return xdxr
        except:
            Logger.log().error("get_xdxr_info 网络问题重连中")
            self.connect.close()
            self.connect = self.api.connect('121.36.81.195', 7709)
            return self.get_xdxr_info(code)
        
    @Dec.timeit_decorator
    def get_kdata(self, code: str, start_date: str, end_date: str):
        try:
            return self.api.get_k_data(code, start_date, end_date)
        except:
            Logger.log().error("get_xdxr_info 网络问题重连中")
            self.connect.close()
            self.connect = self.api.connect('121.36.81.195', 7709)
            return self.get_xdxr_info(code, start_date, end_date)
        
    def get_mkt_code(self, code):
        if code[0] == '6':
            mkt_code = 1
        else:
            mkt_code = 0

        return mkt_code
    
if __name__ == '__main__':
    

    api = TdxHq_API(heartbeat=True, auto_retry=True)
    with api.connect('121.36.81.195', 7709):
        print("OK")
        # data = api.get_security_bars(9, 0, '000001', 0, 10) #返回普通list
        # print(data)
        data = api.to_df(api.get_security_bars(9, 0, '000001', 0, 10)) # 返回DataFrame
        # print(data)
        xdxr = api.get_xdxr_info(1, '601398')

        print(type(xdxr))
        for item in xdxr:
            print(item)
            # str = ""
            # for key, value in item.items():
            #     str += f"{key}\t{value}\t"
                
            # print(str)
        # print(api.get_k_data('601398','2024-12-31','2025-01-18'))
    # import pytdx
    # print(pytdx.version) 
    # # main()

# import requests
# import pandas as pd

# API_URL = ""
# token = "your_api_token"

# headers = {
#     'Authorization': f'Bearer {token}',
#     'Content-Type': 'application/json'
# }

# def get_adjusted_data(stock_code, start_date, end_date):
#     params = {
#         'code': stock_code,
#         'start': start_date,
#         'end': end_date
#     }
#     response = requests.get(API_URL, headers=headers, params=params)
#     if response.status_code == 200:
#         return response.json()
#     else:
#         raise Exception("Error fetching data: " + response.text)

# def process_data(raw_data):
#     df = pd.DataFrame(raw_data)
#     df['date'] = pd.to_datetime(df['date'])
#     df.set_index('date', inplace=True)
#     return df

# def save_data_to_csv(df, filename):
#     df.to_csv(filename)

# # 主程序
# if __name__ == "__main__":
#     stock_code = "600519"  # 茅台的股票代码
#     start_date = "2022-01-01"
#     end_date = "2023-01-01"
    
#     # 获取复权数据
#     raw_data = get_adjusted_data(stock_code, start_date, end_date)
#     # 处理数据
#     df = process_data(raw_data)
#     # 保存数据
#     save_data_to_csv(df, "adjusted_data.csv")

# [OrderedDict({'year': 2020, 'month': 1, 'day': 16, 'category': 5, 'name': '股本变化', 'fenhong': None, 'peigujia': None, 'songzhuangu':
#  None, 'peigu': None, 'suogu': None, 'panqianliutong': 0, 'panhouliutong': 260421.03125, 'qianzongguben': 0, 'houzongguben': 4910648.5,
#  'fenshu': None, 'xingquanjia': None}), 
#  OrderedDict({'year': 2020, 'month': 7, 'day': 16, 'category': 5, 'name': '股本变化', 'fenhong':
#  None, 'peigujia': None, 'songzhuangu': None, 'peigu': None, 'suogu': None, 'panqianliutong': 260421.03125, 'panhouliutong': 321185.937
# 5, 'qianzongguben': 4910648.5, 'houzongguben': 4910648.5, 'fenshu': None, 'xingquanjia': None}), 
# OrderedDict({'year': 2020, 'month': 8, 'day': 19, 'category': 1, 'name': '除权除息', 'fenhong': 0.527999997138977, 'peigujia': 0.0, 'songzhuangu': 0.0, 'peigu': 0.0, 'suogu'
# : None, 'panqianliutong': None, 'panhouliutong': None, 'qianzongguben': None, 'houzongguben': None, 'fenshu': None, 'xingquanjia': None
# }), 
# OrderedDict({'year': 2020, 'month': 12, 'day': 31, 'category': 5, 'name': '股本变化', 'fenhong': None, 'peigujia': None, 'songzhuan
# gu': None, 'peigu': None, 'suogu': None, 'panqianliutong': 321185.9375, 'panhouliutong': 260421.03125, 'qianzongguben': 4910648.5, 'hou
# zongguben': 4910648.5, 'fenshu': None, 'xingquanjia': None}), 
# OrderedDict({'year': 2021, 'month': 1, 'day': 21, 'category': 5, 'name':'股本变化', 'fenhong': None, 'peigujia': None, 'songzhuangu': None, 'peigu': None, 'suogu': None, 'panqianliutong': 260421.03125, 'panh
# ouliutong': 2732869.5, 'qianzongguben': 4910648.5, 'houzongguben': 4910648.5, 'fenshu': None, 'xingquanjia': None}), OrderedDict({'year
# ': 2021, 'month': 7, 'day': 30, 'category': 1, 'name': '除权除息', 'fenhong': 0.32899999618530273, 'peigujia': 0.0, 'songzhuangu': 0.0,
#  'peigu': 0.0, 'suogu': None, 'panqianliutong': None, 'panhouliutong': None, 'qianzongguben': None, 'houzongguben': None, 'fenshu': Non
# e, 'xingquanjia': None}), 
# OrderedDict({'year': 2022, 'month': 7, 'day': 29, 'category': 1, 'name': '除权除息', 'fenhong': 0.49099999666
# 21399, 'peigujia': 0.0, 'songzhuangu': 0.0, 'peigu': 0.0, 'suogu': None, 'panqianliutong': None, 'panhouliutong': None, 'qianzongguben'
# : None, 'houzongguben': None, 'fenshu': None, 'xingquanjia': None}), 
# OrderedDict({'year': 2023, 'month': 1, 'day': 16, 'category': 5, '
# name': '股本变化', 'fenhong': None, 'peigujia': None, 'songzhuangu': None, 'peigu': None, 'suogu': None, 'panqianliutong': 2732869.5, '
# panhouliutong': 4910648.5, 'qianzongguben': 4910648.5, 'houzongguben': 4910648.5, 'fenshu': None, 'xingquanjia': None}), OrderedDict({'
# year': 2023, 'month': 7, 'day': 28, 'category': 1, 'name': '除权除息', 'fenhong': 0.11400000005960464, 'peigujia': 0.0, 'songzhuangu':
# 0.0, 'peigu': 0.0, 'suogu': None, 'panqianliutong': None, 'panhouliutong': None, 'qianzongguben': None, 'houzongguben': None, 'fenshu':
#  None, 'xingquanjia': None}), 
# OrderedDict({'year': 2024, 'month': 6, 'day': 28, 'category': 1, 'name': '除权除息', 'fenhong': 1.1160000
# 562667847, 'peigujia': 0.0, 'songzhuangu': 0.0, 'peigu': 0.0, 'suogu': None, 'panqianliutong': None, 'panhouliutong': None, 'qianzonggu
# ben': None, 'houzongguben': None, 'fenshu': None, 'xingquanjia': None})]