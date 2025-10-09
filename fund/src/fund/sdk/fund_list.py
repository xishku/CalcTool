import requests
import re
import ast
from typing import List, Dict, Any

class FundList:
    def fetch_fund_data(self, url: str) -> str:
        """
        从指定URL获取基金数据文本
        
        参数:
            url: 目标URL
            
        返回:
            str: 原始文本数据
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取数据失败: {e}")

    def extract_js_array(self, text: str) -> str:
        """
        从JavaScript文本中提取数组部分
        
        参数:
            text: JavaScript文本
            
        返回:
            str: 数组部分的字符串
        """
        # 匹配常见的JS数组格式
        patterns = [
            r'var\s+fundCodes\s*=\s*(\[.*?\]);',
            r'fundCodes\s*=\s*(\[.*?\]);',
            r'(\[\[.*?\]\])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                return match.group(1)
        
        raise Exception("未找到有效的数组数据")

    def parse_js_array(self, js_array_str: str) -> List[List[Any]]:
        """
        将JavaScript数组字符串解析为Python列表
        
        参数:
            js_array_str: JavaScript数组字符串
            
        返回:
            List[List[Any]]: 解析后的Python列表
        """
        try:
            # 使用ast.literal_eval安全解析
            return ast.literal_eval(js_array_str)
        except (SyntaxError, ValueError) as e:
            raise Exception(f"解析数组失败: {e}")

    def convert_to_structured_data(self, raw_list: List[List[Any]]) -> List[Dict[str, Any]]:
        """
        将原始列表转换为结构化的字典列表
        
        参数:
            raw_list: 原始列表数据
            
        返回:
            List[Dict[str, Any]]: 结构化的基金数据
        """
        structured_data = []
        for item in raw_list:
            if len(item) >= 5:
                fund = {
                    'code': item[0],
                    'short_name': item[1],
                    'full_name': item[2],
                    'type': item[3],
                    'pinyin': item[4]
                }
                structured_data.append(fund)
        return structured_data

    def get_fund_structured_list(self):
        """
        主函数：演示整个流程
        """
        url = "http://fund.eastmoney.com/js/fundcode_search.js"
        
        try:
            # 获取原始数据
            raw_text = self.fetch_fund_data(url)
            print("数据获取成功")
            
            # 提取JS数组部分
            js_array_str = self.extract_js_array(raw_text)
            print("数组提取成功")
            
            # 解析为Python列表
            raw_list = self.parse_js_array(js_array_str)
            print(f"解析成功，共{len(raw_list)}条基金数据")
            
            # 转换为结构化数据
            structured_data = self.convert_to_structured_data(raw_list)
            
            # 打印前5条数据作为示例
            # print("\n前5条基金数据:")
            # for i, fund in enumerate(structured_data, 1):
            #     print(f"{i}. 代码: {fund['code']}, 简称: {fund['short_name']}, 全称: {fund['full_name']}, 类型: {fund['type']}")
                
            return structured_data
            
        except Exception as e:
            print(f"处理过程中出错: {e}")
            return []

if __name__ == "__main__":
    # 执行主函数
    fund_list = FundList()
    result_data = fund_list.get_fund_structured_list()

    for fund in result_data:
        print(fund['code'])
    
