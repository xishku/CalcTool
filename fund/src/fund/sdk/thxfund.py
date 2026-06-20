from fund_list import FundList
fl = FundList()
# fl.export_all_10jqka_to_csv("fund_10jqka_test.csv")
# 然后 Ctrl+C 停止，检查 CSV 中前几条数据是否正确

# 如果遇到大量 403，可以：

# 1. 降低并发数
fl.export_all_10jqka_to_csv("output.csv", max_workers=1)

# 2. 增加延迟（修改 fetch_one 中的 sleep）
time.sleep(random.uniform(1.5, 2.5))  # 原来是 0.8-1.5

# 3. 分批处理
codes_batch1 = [fund['code'] for fund in list(fl.get_fund_structured_list())[:5000]]
fl.export_all_10jqka_to_csv("batch1.csv", codes=codes_batch1, max_workers=2)
