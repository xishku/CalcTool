from bs4 import BeautifulSoup
import json

# 假设html_content是提供的HTML片段
html_content = """
<div class='box'><div class='boxitem w790'><h4 class='t'><label class='left'><a href='http://fund.eastmoney.com/110022.html'>易方达消费行业股票</a>&nbsp;&nbsp;2025年2季度股票投资明细</label><label class='right lab2 xq505'>&nbsp;&nbsp;&nbsp;&nbsp;来源：天天基金&nbsp;&nbsp;&nbsp;&nbsp;截止至：<font class='px12'>2025-06-30</font></label></h4><div class='space0'></div><table class='w782 comm tzxq'><thead><tr><th class='first'>序号</th><th>股票代码</th><th>股票名称</th><th>最新价</th><th>涨跌幅</th><th class='xglj'>相关资讯</th><th>占净值<br />比例</th><th class='cgs'>持股数 <br />（万股）</th><th class='last ccs'>持仓市值<br />（万元）</th></tr></thead><tbody><tr><td>1</td><td><a href='//quote.eastmoney.com/unify/r/0.000333'>000333</a></td><td class='tol'><a href='//quote.eastmoney.com/unify/r/0.000333'>美的集团</a></td><td class='tor'><span data-id='dq000333'></span></td><td class='tor'><span data-id='zd000333'></span></td><td class='xglj'><a href='ccbdxq_110022_000333.html' class='red'>变动详情</a><a href='//guba.e
"""

# 解析HTML
soup = BeautifulSoup(html_content, 'html.parser')

# 提取表格数据
table = soup.find('table', {'class': 'w782 comm tzxq'})
rows = table.find_all('tr')[1:]  # 跳过表头

data = []
for row in rows:
    cols = row.find_all('td')
    if len(cols) >= 8:  # 确保有足够的列
        item = {
            "序号": cols[0].get_text(strip=True),
            "股票代码": cols[1].get_text(strip=True),
            "股票名称": cols[2].get_text(strip=True),
            "占净值比例": cols[6].get_text(strip=True),
            "持股数(万股)": cols[7].get_text(strip=True),
            "持仓市值(万元)": cols[8].get_text(strip=True)
        }
        data.append(item)

# 转换为JSON格式
json_data = json.dumps(data, ensure_ascii=False, indent=4)
print(json_data)
