import akshare as ak

# 获取中国工商银行（601398）最近10天的K线数据
stock_code = "601398"
stock_data = ak.stock_zh_a_daily(symbol=stock_code, adjust="qfq")

# 获取最近10天的数据
recent_10_days_data = stock_data.tail(10)

print(recent_10_days_data)