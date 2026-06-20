"""
测试同花顺爱基金数据抓取 - 前10只基金
"""
import sys
import os
import time
import random

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fund_list import FundList

def main():
    fl = FundList()
    
    print("=" * 60)
    print("测试：同花顺爱基金数据抓取（前10只基金）")
    print("=" * 60)
    
    # 获取前10只基金代码
    print("\n正在获取前10只基金代码...")
    all_funds = list(fl.get_fund_structured_list())
    test_codes = [fund['code'] for fund in all_funds[:10]]
    
    print(f"\n测试基金列表:")
    for i, code in enumerate(test_codes, 1):
        fund_info = next((f for f in all_funds if f['code'] == code), None)
        name = fund_info['short_name'] if fund_info else ''
        print(f"  {i}. {code} - {name}")
    
    print(f"\n开始抓取同花顺数据（单线程，带重试机制）...")
    print("-" * 60)
    
    # 逐个抓取并显示结果
    success_count = 0
    fail_count = 0
    
    for i, code in enumerate(test_codes, 1):
        print(f"\n[{i}/10] 正在抓取 {code}...")
        
        max_retries = 3
        info = None
        
        for attempt in range(max_retries):
            try:
                # 使用已存在的 get_fund_10jqka_info 方法
                info = fl.get_fund_10jqka_info(code)
                
                if info:
                    success_count += 1
                    print(f"  ✓ 成功（尝试 {attempt + 1}/{max_retries}）")
                    print(f"    名称: {info.get('name', 'N/A')}")
                    print(f"    类型: {info.get('fund_type', 'N/A')}")
                    print(f"    净值: {info.get('latest_nav', 'N/A')} ({info.get('latest_nav_date', 'N/A')})")
                    print(f"    涨幅: {info.get('daily_change', 'N/A')}%")
                    print(f"    近1月: {info.get('syl_1m', 'N/A')}%")
                    print(f"    近1年: {info.get('syl_1y', 'N/A')}%")
                    print(f"    公司: {info.get('company', 'N/A')}")
                    print(f"    经理: {info.get('manager', 'N/A')}")
                    break  # 成功则跳出重试循环
                else:
                    if attempt < max_retries - 1:
                        wait_time = random.uniform(3, 6)
                        print(f"  ⚠ 未获取到数据，{wait_time:.1f}秒后重试 ({attempt + 2}/{max_retries})...")
                        time.sleep(wait_time)
                    else:
                        fail_count += 1
                        print(f"  ✗ 失败：重试 {max_retries} 次后仍未获取到数据")
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2 + random.uniform(2, 4)
                    print(f"  ⚠ 异常: {type(e).__name__}: {e}")
                    print(f"    {wait_time:.1f}秒后重试 ({attempt + 2}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    fail_count += 1
                    print(f"  ✗ 异常: {type(e).__name__}: {e}")
                    print(f"    重试 {max_retries} 次后仍失败")
        
        # 每个基金之间间隔（无论成功失败）
        if i < len(test_codes):
            delay = random.uniform(2, 4)
            print(f"  等待 {delay:.1f} 秒后继续下一个...")
            time.sleep(delay)
    
    # 总结
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print(f"  总计: {len(test_codes)} 只基金")
    print(f"  成功: {success_count} 只")
    print(f"  失败: {fail_count} 只")
    print(f"  成功率: {success_count/len(test_codes)*100:.1f}%")
    
    if success_count > 0:
        print(f"\n✓ 数据抓取正常，可以扩大范围")
    else:
        print(f"\n✗ 全部失败，需要检查网络或调整参数")

if __name__ == "__main__":
    main()