import requests
import json
import re
from typing import List, Dict, Any
from datetime import datetime

from bs4 import BeautifulSoup
from fund_list import FundList

def get_fund_holdings(fund_code: str, topline: int = 100) -> List[Dict[str, Any]]:
    """
    获取基金持仓信息
    
    参数:
        fund_code: 基金代码
        topline: 显示条数，默认10条
        
    返回:
        List[Dict[str, Any]]: 持仓信息列表
    """
    # 构建请求URL
    url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
    params = {
        'type': 'jjcc',
        'code': fund_code,
        'topline': topline,
        'year': '2025',
        'month': '',
        'rt': int(datetime.now().timestamp() * 1000)  # 添加时间戳防止缓存
    }
    
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': f'http://fundf10.eastmoney.com/{fund_code}.html',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        # 发送请求
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        # 检查响应状态
        response.raise_for_status()
        
        # print(response.text)

        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')  # 解析 HTML

        report_cycles = soup.find_all(class_="right lab2 xq505")
        report_labels = [cycle.find("font").get_text() for cycle in report_cycles if cycle.find("font") is not None]

        tables = soup.find_all('table')  # 查找第一个 <table> 标签
        
        holdings = []
        for i, table in enumerate(tables):
            if i < len(tables):
                print(report_labels[i])

            ths = table.find_all("th")
            ths_content = [col.text for col in ths]  # 获取列数据
            print(ths_content)
            col_index_dict = dict()
            for j, col in enumerate(ths):
                col_index_dict[col.text] = j
                
            print("col_index_dict['股票代码']", col_index_dict['股票代码'])
            print("col_index_dict['股票名称']", col_index_dict['股票名称'])
            print("col_index_dict['占净值比例']", col_index_dict['占净值比例'])
            print("col_index_dict['持股数（万股）']", col_index_dict['持股数（万股）'])
            print("col_index_dict['持仓市值（万元）']", col_index_dict['持仓市值（万元）'])


            rows = table.find_all('tr')  # 查找所有行
            for row in rows:
                cols = row.find_all('td')  # 查找所有列
                data = [col.text for col in cols]  # 获取列数据
                # print("len(data)", len(data), "len(col_index_dict)", len(col_index_dict))
                if len(data) < len(col_index_dict):
                    continue

# ['序号', '股票代码', '股票名称', '最新价', '涨跌幅', '相关资讯', '占净值比例', '持股数（万股）', '持仓市值（万元）']
# ['序号', '股票代码', '股票名称', '相关资讯', '占净值比例', '持股数（万股）', '持仓市值（万元）']
                holdings.append({
                    'code': fund_code,
                    'report_cycle': report_labels[i],
                    'stock_code': data[col_index_dict['股票代码']], 
                    'stock_name': data[col_index_dict['股票名称']],      
                    'holding_ratio': data[col_index_dict['占净值比例']],   
                    'shares_held': data[col_index_dict['持股数（万股）']],     
                    'market_value': data[col_index_dict['持仓市值（万元）']]     
                })
        
        return holdings
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON解析失败: {e}")
    except Exception as e:
        raise Exception(f"获取持仓信息失败: {e}")

def main():
    """
    主函数：演示如何使用上述函数
    """
    fund_list = FundList()
    result_data = fund_list.get_fund_structured_list()

    fund_codes = []
    for fund in result_data:
        fund_codes.append(fund['code'])
    
    with open('example.txt', 'w', encoding='utf-8') as f:
        for fund_code in fund_codes:
            print(f"\n{'='*50}")
            print(f"获取基金 {fund_code} 的持仓信息")
            print('='*50)
            
            try:
                # 获取简单持仓信息
                holdings = get_fund_holdings(fund_code, 100)  # 获取前5大持仓
                
                print(f"基金 {fund_code} 的前100大持仓:")
                for i, holding in enumerate(holdings, 1):
                    data = f"{str(fund_code)}\t{holding['report_cycle']}\t{holding['stock_name']}({holding['stock_code']}):\t"\
                            f"{holding['holding_ratio']}\t"\
                            f"持股数\t{holding['shares_held']}\t万股\t"\
                            f"市值\t{holding['market_value']}\t万元\n"
                    # print(data)
                    f.write(data)
                
            except Exception as e:
                print(f"获取基金 {fund_code} 信息失败: {e}")

        # break

if __name__ == "__main__":
    main()
