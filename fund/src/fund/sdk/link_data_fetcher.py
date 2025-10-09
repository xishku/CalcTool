import requests
import json
import time
from requests.exceptions import RequestException, Timeout, HTTPError

class LinkDataFetcher:
    """链接数据获取器"""
    
    def __init__(self, timeout=10, retries=3):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        
        # 设置默认请求头，模拟浏览器访问
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })
    
    def fetch_data(self, url, params=None, headers=None, method='GET', data=None):
        """
        从指定URL获取数据
        
        参数:
            url: 目标链接
            params: 查询参数
            headers: 自定义请求头
            method: HTTP方法 (GET/POST)
            data: POST请求的数据
        
        返回:
            dict: 包含状态和数据的结果
        """
        # 合并请求头
        final_headers = self.session.headers.copy()
        if headers:
            final_headers.update(headers)
        
        for attempt in range(self.retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, 
                        params=params, 
                        headers=final_headers, 
                        timeout=self.timeout
                    )
                elif method.upper() == 'POST':
                    response = self.session.post(
                        url, 
                        data=data, 
                        params=params, 
                        headers=final_headers, 
                        timeout=self.timeout
                    )
                else:
                    return {
                        'success': False,
                        'error': f'不支持的HTTP方法: {method}'
                    }
                
                # 检查响应状态
                response.raise_for_status()
                
                # 根据内容类型处理响应
                content_type = response.headers.get('Content-Type', '').lower()
                
                if 'application/json' in content_type:
                    result_data = response.json()
                elif 'text/html' in content_type or 'text/plain' in content_type:
                    result_data = response.text
                else:
                    # 对于其他类型，返回原始内容
                    result_data = response.content
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'content_type': content_type,
                    'data': result_data,
                    'headers': dict(response.headers),
                    'url': response.url
                }
                
            except Timeout:
                print(f"第 {attempt + 1} 次请求超时，{self.timeout}秒后重试...")
                if attempt == self.retries - 1:
                    return {
                        'success': False,
                        'error': f'请求超时（尝试{self.retries}次）'
                    }
                time.sleep(1)  # 等待1秒后重试
                
            except HTTPError as e:
                return {
                    'success': False,
                    'error': f'HTTP错误: {e}',
                    'status_code': e.response.status_code if e.response else None
                }
                
            except RequestException as e:
                return {
                    'success': False,
                    'error': f'请求异常: {e}'
                }
        
        return {
            'success': False,
            'error': '未知错误'
        }
    
    def close(self):
        """关闭会话"""
        self.session.close()

def main():
    """主函数示例"""
    fetcher = LinkDataFetcher(timeout=15, retries=3)
    
    # 示例URL（您可以根据需要替换）
    test_urls = [
        "https://httpbin.org/json",  # 返回JSON数据的测试URL
        "https://httpbin.org/html",   # 返回HTML的测试URL
        "https://jsonplaceholder.typicode.com/posts/1"  # 另一个JSON API
    ]
    
    for url in test_urls:
        print(f"\n{'='*50}")
        print(f"获取URL: {url}")
        print('='*50)
        
        result = fetcher.fetch_data(url)
        
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

if __name__ == "__main__":
    # 检查requests库是否已安装
    try:
        import requests
    except ImportError:
        print("错误: 请先安装requests库")
        print("运行: pip install requests")
        exit(1)
    
    main()