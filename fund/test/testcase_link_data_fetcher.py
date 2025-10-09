#!/usr/bin/python#

#-*-coding:UTF-8-*-

import os
import sys
import unittest
import datetime
import numpy

import requests
import json
import time
from requests.exceptions import RequestException, Timeout, HTTPError
import ast


print(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../src"))
from fund.sdk.link_data_fetcher import LinkDataFetcher

import unittest

class TestLinkDataFetcher(unittest.TestCase):
        
    def test_fund(self):
        self.assertEqual('foo'.upper(), 'FOO')

        fetcher = LinkDataFetcher(timeout=15, retries=3)
        
        # 示例URL（您可以根据需要替换）
        test_urls = [
            # "https://httpbin.org/json",  # 返回JSON数据的测试URL
            # "https://httpbin.org/html",   # 返回HTML的测试URL
            "http://fund.eastmoney.com/js/fundcode_search.js"  # 另一个JSON API
        ]
        
        for url in test_urls:
            print(f"\n{'='*50}")
            print(f"获取URL: {url}")
            print('='*50)
            
            result = fetcher.fetch_data(url)
            
            self.assertEqual('foo'.upper(), 'FOO')
            self.assertTrue(result['success'])
            if result['success']:
                print("✅ 请求成功!")
                print(f"状态码: {result['status_code']}")
                print(f"内容类型: {result['content_type']}")
                print(f"数据长度: {len(str(result['data']))} 字符")
                
                # 根据数据类型显示部分内容
                if isinstance(result['data'], dict):
                    print("数据预览 (JSON):")
                    print(json.dumps(result['data'], indent=2, ensure_ascii=False)[:200] + "...")
                elif isinstance(result['data'], str):
                    print("数据预览 (文本):")
                    print(result['data'][:200] + "...")
                else:
                    print("数据预览 (二进制):")
                    # print(str(result['data'])[:200] + "...")
                    data_str = str(result['data'])
                    # print(data_str)

                    # 步骤1：确保字符串是一个完整的列表表达式（添加外层的方括号）
                    if not data_str.strip().startswith('['):
                        data_str = '[' + data_str
                    if not data_str.strip().endswith(']'):
                        data_str = data_str + ']'

                    # 步骤2：使用ast.literal_eval解析字符串
                    try:
                        data_list = ast.literal_eval(data_str)
                        print("data_list长度：", len(data_list))
                    except Exception as e:
                        print("解析错误:", e)
                        data_list = []


            else:
                print("❌ 请求失败!")
                print(f"错误信息: {result['error']}")
            
            # 关闭会话
            fetcher.close()

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

        fetcher = LinkDataFetcher(timeout=15, retries=3)
        
        # 示例URL（您可以根据需要替换）
        test_urls = [
            # "https://httpbin.org/json",  # 返回JSON数据的测试URL
            # "https://httpbin.org/html",   # 返回HTML的测试URL
            # "https://jsonplaceholder.typicode.com/posts/1"  # 另一个JSON API
        ]
        
        for url in test_urls:
            print(f"\n{'='*50}")
            print(f"获取URL: {url}")
            print('='*50)
            
            result = fetcher.fetch_data(url)
            
            self.assertEqual('foo'.upper(), 'FOO')
            self.assertTrue(result['success'])
            if result['success']:
                print("✅ 请求成功!")
                print(f"状态码: {result['status_code']}")
                print(f"内容类型: {result['content_type']}")
                print(f"数据长度: {len(str(result['data']))} 字符")
                
                # 根据数据类型显示部分内容
                if isinstance(result['data'], dict):
                    print("数据预览 (JSON):")
                    print(json.dumps(result['data'], indent=2, ensure_ascii=False)[:200] + "...")
                elif isinstance(result['data'], str):
                    print("数据预览 (文本):")
                    print(result['data'][:200] + "...")
                else:
                    print("数据预览 (二进制):")
                    print(str(result['data'])[:200] + "...")
            else:
                print("❌ 请求失败!")
                print(f"错误信息: {result['error']}")
        
            # 演示POST请求
            print(f"\n{'='*50}")
            print("演示POST请求")
            print('='*50)
            
            post_url = "https://httpbin.org/post"
            post_data = {"key": "value", "test": "data"}
            
            post_result = fetcher.fetch_data(post_url, method='POST', data=post_data)
            
            self.assertTrue(post_result['success'])
            if post_result['success']:
                print("✅ POST请求成功!")
                if isinstance(post_result['data'], dict):
                    print("返回数据:")
                    print(json.dumps(post_result['data'], indent=2, ensure_ascii=False))
            else:
                print("❌ POST请求失败!")
                print(f"错误信息: {post_result['error']}")
            
            # 关闭会话
            fetcher.close()

    def test_isupper(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # 检查当分隔符不为字符串时 s.split 是否失败
        with self.assertRaises(TypeError):
            s.split(2)

if __name__ == '__main__':
    unittest.main()

