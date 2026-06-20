import requests
import re
import ast
import csv
import json
import time
import random
from typing import List, Dict, Any, Generator, Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
try:
    from curl_cffi import requests as curl_requests
    _HAS_CURL_CFFI = True
except ImportError:
    curl_requests = None
    _HAS_CURL_CFFI = False

# curl_cffi 和标准 requests 的 HTTPError 可能是不同类层级
_HTTP_ERRORS = (requests.exceptions.HTTPError,)
if _HAS_CURL_CFFI:
    try:
        _HTTP_ERRORS = _HTTP_ERRORS + (curl_requests.exceptions.HTTPError,)
    except AttributeError:
        pass

# UTC+8 时区偏移（毫秒）
_UTC8_OFFSET_MS = 8 * 3600 * 1000

# 常见 User-Agent 池（用于 10jqka 反反爬）
_UA_POOL = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
]


# 10jqka 全局限流信号量（最多 3 个并发请求）
_TENJQKA_SEM = threading.BoundedSemaphore(2)
# 10jqka 预热 Cookie（首次访问首页后缓存）
_TENJQKA_COOKIES: Dict[str, str] = {}
_TENJQKA_WARMED = False
_TENJQKA_WARM_LOCK = threading.Lock()

# 线程局部 Session 池——同线程内复用同一个 curl_cffi Session，积累 Cookie 和 TLS 状态
_TENJQKA_POOL = threading.local()


def _get_10jqka_session() -> Any:
    """获取或创建线程局部 curl_cffi Session（自动预热）"""
    if not getattr(_TENJQKA_POOL, 'session', None):
        s = curl_requests.Session(impersonate="chrome131")
        s.headers.update({
            'User-Agent': random.choice(_UA_POOL),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        })
        if _TENJQKA_COOKIES:
            s.cookies.update(_TENJQKA_COOKIES)
        # 预热：先访问一次首页让 Session 建立连接和获取初始 Cookie
        try:
            s.get('https://fund.10jqka.com.cn/', timeout=20)
        except Exception:
            pass
        _TENJQKA_POOL.session = s
        _TENJQKA_POOL.req_count = 0
        _TENJQKA_POOL.fail_streak = 0
    return _TENJQKA_POOL.session


def _refresh_10jqka_session() -> Any:
    """当前 Session 可能已被标记，关闭旧 Session 并创建新的"""
    old = getattr(_TENJQKA_POOL, 'session', None)
    if old:
        try:
            old.close()
        except Exception:
            pass
    _TENJQKA_POOL.session = None
    return _get_10jqka_session()


def _bump_10jqka_fail():
    """记录一次失败，连续失败 5 次则自动刷新 Session"""
    streak = getattr(_TENJQKA_POOL, 'fail_streak', 0) + 1
    _TENJQKA_POOL.fail_streak = streak
    if streak >= 5:
        _refresh_10jqka_session()
        _TENJQKA_POOL.fail_streak = 0


class FundList:
    # ---------- 通用工具 ----------

    def _headers(self, domain: str = 'eastmoney') -> Dict[str, str]:
        """获取请求头，支持不同域名使用不同 Referer"""
        if domain == '10jqka':
            return {
                'User-Agent': random.choice(_UA_POOL),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://fund.10jqka.com.cn/',
                'Cache-Control': 'max-age=0',
            }
        else:
            return {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Referer': 'http://fund.eastmoney.com/',
            }

    @staticmethod
    def _warmup_10jqka():
        """预热 10jqka：使用 curl_cffi 模拟多个浏览器指纹访问首页获取 Cookie"""
        global _TENJQKA_COOKIES, _TENJQKA_WARMED
        if not _HAS_CURL_CFFI:
            print("  ⚠ curl_cffi 未安装，预热跳过")
            return
        with _TENJQKA_WARM_LOCK:
            if _TENJQKA_WARMED:
                return

            # 多个 impersonate 目标轮换尝试
            impersonates = ["chrome131", "chrome124", "chrome120", "edge101", "safari17_0"]
            # 尝试不同路径（首页可能校验严格，用子页面可能宽松）
            warmup_paths = [
                '/',
                '/300000/',      # 试试一个存在的基金页面
            ]

            print("正在预热 10jqka 连接（curl_cffi + 多指纹轮换）...")
            for attempt in range(6):
                imp = impersonates[attempt % len(impersonates)]
                path = warmup_paths[attempt % len(warmup_paths)]
                try:
                    s = curl_requests.Session(impersonate=imp)
                    s.headers.update({
                        'User-Agent': random.choice(_UA_POOL),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Cache-Control': 'max-age=0',
                        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'Upgrade-Insecure-Requests': '1',
                    })
                    resp = s.get(f'https://fund.10jqka.com.cn{path}', timeout=20)
                    if resp.status_code in (403, 429):
                        raise Exception(f"HTTP {resp.status_code}")
                    resp.raise_for_status()
                    _TENJQKA_COOKIES = dict(s.cookies.get_dict())
                    s.close()
                    _TENJQKA_WARMED = True
                    print(f"  10jqka 预热成功（{imp} + {path}），获取到 {len(_TENJQKA_COOKIES)} 个 Cookie")
                    return
                except Exception as e:
                    print(f"  10jqka 预热失败 (尝试 {attempt + 1}/6, {imp}{path}): {e}")
                    time.sleep(6)
            print("  10jqka 预热失败，将直接尝试请求")

    def fetch_fund_data(self, url: str) -> str:
        """
        从指定URL获取基金数据文本
        
        参数:
            url: 目标URL
            
        返回:
            str: 原始文本数据
        """
        try:
            response = requests.get(url, headers=self._headers(), timeout=10)
            response.encoding = 'utf-8'
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取数据失败: {e}")

    # ---------- 基金列表 ----------

    def extract_js_array(self, text: str) -> str:
        """
        从JavaScript文本中提取数组部分
        
        参数:
            text: JavaScript文本
            
        返回:
            str: 数组部分的字符串
        """
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
            return ast.literal_eval(js_array_str)
        except (SyntaxError, ValueError) as e:
            raise Exception(f"解析数组失败: {e}")

    def convert_to_structured_data(self, raw_list: List[List[Any]]) -> Generator[Dict[str, Any], None, None]:
        """
        将原始列表转换为结构化的字典列表（生成器）
        
        参数:
            raw_list: 原始列表数据
            
        产出:
            Dict[str, Any]: 结构化的基金数据
        """
        for item in raw_list:
            if len(item) >= 5:
                yield {
                    'code': item[0],
                    'short_name': item[1],
                    'full_name': item[2],
                    'type': item[3],
                    'pinyin': item[4]
                }

    def get_fund_structured_list(self) -> Generator[Dict[str, Any], None, None]:
        """
        获取全部基金列表（生成器，约13000+条）
        """
        url = "http://fund.eastmoney.com/js/fundcode_search.js"
        
        try:
            raw_text = self.fetch_fund_data(url)
            print("数据获取成功")
            
            js_array_str = self.extract_js_array(raw_text)
            print("数组提取成功")
            
            raw_list = self.parse_js_array(js_array_str)
            print(f"解析成功，共{len(raw_list)}条基金数据")
            
            yield from self.convert_to_structured_data(raw_list)
        except Exception as e:
            print(f"处理过程中出错: {e}")
            return

    # ========== 基金详细信息 ==========

    def get_fund_scale_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金规模/资产净值/履历等详细信息

        数据源: https://fundmobapi.eastmoney.com/FundMNewApi/FundMNDetailInformation

        参数:
            code: 6位基金代码

        返回:
            dict 或 None:
                - scale_end_nav: 期末资产净值（元），季度报告
                - scale_net_nav: 净值（可能与规模不同含义）
                - scale_date: 期末报告日期
                - company: 基金管理人
                - custodian: 基金托管人
                - manager: 基金经理
                - establish_date: 成立日期
                - risk_level: 风险等级（1-5）
                - manage_fee: 管理费率（%）
                - custodian_fee: 托管费率（%）
                - service_fee: 销售服务费率（%）
                - benchmark: 业绩比较基准
                - index_code: 跟踪指数代码（指数基金）
                - index_name: 跟踪指数名称（指数基金）
                - investment_goal: 投资目标
                - investment_strategy: 投资策略
        """
        url = "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNDetailInformation"
        params = {
            'FCODE': code,
            'deviceid': 'fund_sdk',
            'plat': 'Android',
            'product': 'EFund',
            'version': '6.2.4',
        }
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            datas = data.get('Datas', {})
            if not datas:
                print(f"  基金规模数据为空: {code}")
                return None

            return {
                # 基本信息
                'full_name': datas.get('FULLNAME', ''),
                'fund_type': datas.get('FTYPE', ''),
                # 规模
                'scale_end_nav': datas.get('ENDNAV', ''),
                'scale_net_nav': datas.get('NETNAV', ''),
                'scale_date': datas.get('FEGMRQ', ''),
                # 管理人
                'company': datas.get('JJGS', ''),
                'custodian': datas.get('TGYH', ''),
                'manager': datas.get('JJJL', ''),
                'establish_date': datas.get('ESTABDATE', ''),
                'risk_level': datas.get('RISKLEVEL', ''),
                # 费率
                'manage_fee': datas.get('MGREXP', ''),
                'custodian_fee': datas.get('TRUSTEXP', ''),
                'service_fee': datas.get('SALESEXP', ''),
                # 业绩/指数
                'benchmark': datas.get('BENCH', ''),
                'index_code': datas.get('INDEXCODE', ''),
                'index_name': datas.get('INDEXNAME', ''),
                # 投资
                'investment_goal': datas.get('INVTGT', ''),
                'investment_strategy': datas.get('INVSTRA', ''),
                'buy_time': datas.get('BUYTIME', ''),
            }
        except Exception as e:
            print(f"  获取基金规模失败 {code}: {e}")
            return None

    def get_fund_page_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        从基金详情主页一次性提取大部分信息（服务端渲染，无需多API聚合）

        数据源: http://fund.eastmoney.com/{code}.html

        参数:
            code: 6位基金代码

        返回:
            dict 或 None:
                - 基本: code, name, fund_type, risk_level, establish_date
                - 净值: latest_nav, latest_nav_date, cumulative_nav, daily_change
                - 规模: scale, scale_date
                - 管理: company, manager
                - 费率: purchase_fee, min_subscribe
                - 收益率: syl_1m, syl_3m, syl_6m, syl_1y, syl_2y, syl_3y, since_inception
                - 持仓: holding_stocks, holdings_date
                - 交易: trade_status, redeem_status, purchase_limit
                - 分红: dividend_count, split_count
        """
        url = f"http://fund.eastmoney.com/{code}.html"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            resp.encoding = 'utf-8'
            resp.raise_for_status()
            raw_html = resp.text

            result: Dict[str, Any] = {'code': code}

            # ---- 从原始 HTML 属性提取 ----
            # 最小申购金额
            m = re.search(r'data-minsg\s*=\s*"([^"]+)"', raw_html)
            if m:
                result['min_subscribe'] = m.group(1)

            # ---- 去掉标签得到纯文本 ----
            text = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            # 统一空白字符（含 &nbsp; HTML 实体）
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            # ---- 基金名称（从 title 或页面标题区域）----
            m = re.search(r'([\u4e00-\u9fa5A-Za-z0-9]+?)\s*[\(（]\s*0*' + code + r'\s*[\)）]', text)
            if m:
                result['name'] = m.group(1).strip()

            # ---- 单位净值 + 日期 + 日涨幅 ----
            m = re.search(
                r'单位净值[^0-9]*?[\(（]\s*(\d{4}-\d{2}-\d{2})\s*[\)）]\s*([\d.]+)\s*([+-]?\d+\.?\d*)%?',
                text
            )
            if m:
                result['latest_nav_date'] = m.group(1)
                result['latest_nav'] = m.group(2)
                result['daily_change'] = m.group(3)
            else:
                # 回退：可能没有日期括号
                m = re.search(r'单位净值\s*([\d.]+)', text)
                if m:
                    result['latest_nav'] = m.group(1)

            # ---- 累计净值 ----
            m = re.search(r'累计净值\s*([\d.]+)', text)
            if m:
                result['cumulative_nav'] = m.group(1)

            # ---- 基金类型 + 风险等级 ----
            m = re.search(r'类型\s*[：:]\s*([\u4e00-\u9fa5A-Za-z·-]+)', text)
            if m:
                result['fund_type'] = m.group(1).strip()
            m = re.search(r'(中低风险|中高风险|低风险|高风险|中等风险)', text)
            if m:
                result['risk_level'] = m.group(1)

            # ---- 规模 + 日期 ----
            m = re.search(r'规模\s*[：:]\s*([\d.]+亿元)[^\d]*?(\d{4}-\d{2}-\d{2})', text)
            if m:
                result['scale'] = m.group(1)
                result['scale_date'] = m.group(2)
            else:
                m = re.search(r'规模\s*[：:]\s*([\d.]+亿元)', text)
                if m:
                    result['scale'] = m.group(1)

            # ---- 基金经理 ----
            m = re.search(r'基金经理\s*[：:]\s*(\S+)', text)
            if m:
                result['manager'] = m.group(1).strip()

            # ---- 成立日期 ----
            m = re.search(r'成\s*立\s*日\s*[：:]\s*(\d{4}-\d{2}-\d{2})', text)
            if m:
                result['establish_date'] = m.group(1)

            # ---- 基金管理人 ----
            m = re.search(r'管\s*理\s*人\s*[：:]\s*(\S+)', text)
            if m:
                result['company'] = m.group(1).strip()

            # ---- 阶段收益率（页面顶部区域，含冒号）----
            return_map = {
                r'近1月\s*[：:]\s*([+-]?\d+\.?\d*)%': 'syl_1m',
                r'近3月\s*[：:]\s*([+-]?\d+\.?\d*)%': 'syl_3m',
                r'近6月\s*[：:]\s*([+-]?\d+\.?\d*)%': 'syl_6m',
                r'近1年\s*[：:]\s*([+-]?\d+\.?\d*)%': 'syl_1y',
                r'近3年\s*[：:]\s*([+-]?\d+\.?\d*)%': 'syl_3y',
                r'成立来\s*[：:]\s*([+-]?\d+\.?\d*)%': 'since_inception',
            }
            for pattern, key in return_map.items():
                m = re.search(pattern, text)
                if m:
                    result[key] = m.group(1)

            # ---- 阶段收益率表格（从HTML table解析：header行+data行分离）----
            table_match = re.search(
                r'id="increaseAmount_stage"[^>]*>(.*?)</table>',
                raw_html, re.DOTALL
            )
            if table_match:
                tbl = table_match.group(1)
                headers = re.findall(r'<th[^>]*>\s*(?:<div[^>]*>)?\s*(近\d[周月年]|今年来|成立来)', tbl)
                values = re.findall(r'<td[^>]*>\s*<div[^>]*>\s*([+-]?\d+\.?\d+)%', tbl)
                table_label_map = {'近1周': 'syl_1w', '近1月': 'syl_1m', '近3月': 'syl_3m',
                                  '近6月': 'syl_6m', '今年来': 'syl_ytd',
                                  '近1年': 'syl_1y', '近2年': 'syl_2y', '近3年': 'syl_3y',
                                  '成立来': 'since_inception'}
                for i, h in enumerate(headers):
                    key = table_label_map.get(h, '')
                    if key and key not in result and i < len(values):
                        result[key] = values[i]

            # ---- 交易状态 / 赎回状态 / 购买限制 ----
            m = re.search(r'交易状态\s*[：:]\s*(\S+)', text)
            if m:
                result['trade_status'] = m.group(1).strip()
            if '开放赎回' in text:
                result['redeem_status'] = '开放赎回'
            elif '暂停赎回' in text:
                result['redeem_status'] = '暂停赎回'
            m = re.search(r'单日累计购买上限\s*(\d+\.?\d*万元)', text)
            if m:
                result['purchase_limit'] = m.group(1)

            # ---- 购买手续费 ----
            m = re.search(r'购买手续费\s*[：:]\s*(\d+\.?\d*)%', text)
            if m:
                result['purchase_fee'] = m.group(1) + '%'

            # ---- 分红/拆分 ----
            m = re.search(r'分红\s*(\d+)\s*次', text)
            if m:
                result['dividend_count'] = m.group(1)
            m = re.search(r'拆分\s*(\d+)\s*次', text)
            if m:
                result['split_count'] = m.group(1)

            # ---- 前十大持仓 ----
            # 匹配模式: 股票名 持仓占比% 涨跌幅%(可选) 股吧
            holdings = re.findall(
                r'([\u4e00-\u9fa5A-Za-z·]+)\s+(\d+\.\d+)%\s+[+-]?\d+\.\d+%\s+股吧',
                text
            )
            if holdings:
                result['holding_stocks'] = [
                    {'name': h[0], 'ratio': h[1] + '%'}
                    for h in holdings
                ]
            # 持仓截止日期
            m = re.search(r'持仓截止日期\s*[：:]\s*(\d{4}-\d{2}-\d{2})', text)
            if m:
                result['holdings_date'] = m.group(1)

            return result if len(result) > 1 else None

        except Exception as e:
            print(f"  获取基金页面信息失败 {code}: {e}")
            return None

    # ---------- 同花顺（10jqka）基金数据 ----------

    def _retry_10jqka(self, url: str, session, max_retries: int = 3, use_sem: bool = True,
                      referer: str = 'https://fund.10jqka.com.cn/', is_sub_request: bool = False):
        """
        带重试 + 全局限流的 10jqka 请求（使用 curl_cffi session）

        参数:
            url: 请求 URL
            session: curl_cffi.requests.Session
            max_retries: 最大重试次数
            use_sem: 是否使用全局限流信号量
            referer: 自定义 Referer（默认首页）
            is_sub_request: 是否为子资源请求（JSON API），决定 sec-fetch 头

        返回:
            curl_cffi.requests.Response
        """
        # 根据请求类型设置浏览器级请求头
        if is_sub_request:
            extra_headers = {
                'Referer': referer,
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
            }
        else:
            extra_headers = {
                'Referer': referer,
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
            }

        for attempt in range(max_retries):
            if use_sem:
                _TENJQKA_SEM.acquire()
            try:
                # 每次重试换 UA + 设置正确的上下文头
                session.headers.update({
                    'User-Agent': random.choice(_UA_POOL),
                    **extra_headers,
                })
                resp = session.get(url, timeout=25)

                # 404 不重试，直接抛出让调用方处理
                if resp.status_code == 404:
                    raise requests.exceptions.HTTPError(
                        f"404 Not Found: {url}", response=resp
                    )

                if resp.status_code in (403, 429):
                    wait = (2 ** attempt) + random.uniform(1.5, 3.5)
                    if attempt < max_retries - 1:
                        time.sleep(wait)
                        continue
                resp.raise_for_status()
                return resp
            except _HTTP_ERRORS:
                # HTTP 错误不吞，直接抛出（含404,403,429,5xx）
                raise
            except Exception as e:
                # 网络/超时等临时错误可重试
                if attempt < max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(1.0, 2.0)
                    time.sleep(wait)
                    continue
                raise e
            finally:
                if use_sem:
                    _TENJQKA_SEM.release()
        raise Exception(f"10jqka 重试 {max_retries} 次均失败: {url}")

    def get_fund_10jqka_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        从同花顺爱基金网（fund.10jqka.com.cn）获取基金详细信息

        数据源:
        1. https://fund.10jqka.com.cn/{code}/              — 页面内嵌 JS 变量（名称/类型/成立日/规模/经理/资产配置）
        2. /{code}/json/jsondwjz.json                      — 单位净值历史
        3. /ifindRank/quarter_year_{code}.json             — 阶段收益率 + 同类平均 + 沪深300

        参数:
            code: 6位基金代码

        返回:
            dict 或 None
        """
        base = "https://fund.10jqka.com.cn"
        result: Dict[str, Any] = {'code': code, 'source': '10jqka'}

        # 复用线程局部 Session（积累 Cookie 和 TLS 状态，避免每次都创建新连接被 403）
        session = _get_10jqka_session()

        fund_page_url = f"{base}/{code}/"

        try:
            # ---- 1. 获取页面 HTML，提取 JS 变量 ----
            try:
                resp = self._retry_10jqka(fund_page_url, session, is_sub_request=False)
            except _HTTP_ERRORS as e:
                if '404' in str(e):
                    return None  # 该基金不存在，Session 复用
                # 403/429 等反爬错误，记录失败，跳过当前基金
                _bump_10jqka_fail()
                return None
            except Exception:
                # 网络错误等，跳过当前基金
                _bump_10jqka_fail()
                return None
            resp.encoding = 'utf-8'
            raw_html = resp.text

            # 页面请求成功，重置连续失败计数
            _TENJQKA_POOL.fail_streak = 0

            # 模拟页面渲染延迟
            time.sleep(random.uniform(0.2, 0.5))

            # 更新 Cookie（页面可能返回新的）
            if _TENJQKA_WARM_LOCK.acquire(blocking=False):
                try:
                    _TENJQKA_COOKIES.update(session.cookies.get_dict())
                finally:
                    _TENJQKA_WARM_LOCK.release()

            # 基金名称/类型/成立日
            m = re.search(r"fundName\s*=\s*'([^']+)'", raw_html)
            if m:
                result['name'] = m.group(1).strip()
            m = re.search(r"fundType\s*=\s*'([^']+)'", raw_html)
            if m:
                result['fund_type'] = m.group(1).strip()
            m = re.search(r"fundClrq\s*=\s*'([^']+)'", raw_html)
            if m:
                result['establish_date'] = m.group(1).strip()

            # 资产配置
            m = re.search(r"configTotal\s*=\s*'([\d.]+)'", raw_html)
            if m:
                result['scale'] = m.group(1) + '亿元'

            # 资产配置明细
            m = re.search(r'var\s+fundconfig\s*=\s*(\[.*?\])\s*;', raw_html, re.DOTALL)
            if m:
                try:
                    config = json.loads(m.group(1))
                    result['asset_config'] = config
                except json.JSONDecodeError:
                    pass

            # 基金经理
            m = re.search(r'var\s+managers\s*=\s*(\{.*?\})\s*;', raw_html, re.DOTALL)
            if m:
                try:
                    mgr = json.loads(m.group(1))
                    result['manager'] = '、'.join(mgr.keys())
                    # 第一个经理的任职回报
                    first_returns = list(mgr.values())[0] if mgr else []
                    if first_returns:
                        result['manager_return'] = first_returns[0]  # 任职回报
                except json.JSONDecodeError:
                    pass

            # 持有人结构
            m = re.search(r'var\s+ownerconstr\s*=\s*(\{.*?\})\s*;', raw_html, re.DOTALL)
            if m:
                try:
                    result['owner_structure'] = json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass

            # 基金管理人（从 HTML 文本）
            text = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            # 管理人 / 公司名称
            m = re.search(r'公司名称\s*[：:]\s*([\u4e00-\u9fa5A-Za-z（）()·]+)', text)
            if m:
                result['company'] = m.group(1).strip()
            if not result.get('company'):
                m = re.search(r'管理人\s*[：:]\s*([\u4e00-\u9fa5A-Za-z（）()·]+)', text)
                if m and m.group(1) not in ('基金档案', ''):
                    result['company'] = m.group(1).strip()

            # 基金规模（页面文本）
            m = re.search(r'基金规模\s*[：:]\s*([\d.]+亿份)', text)
            if m:
                result['share_size'] = m.group(1)

            # 成立时间
            if not result.get('establish_date'):
                m = re.search(r'成立时间\s*[：:]\s*(\d{4}-\d{2}-\d{2})', text)
                if m:
                    result['establish_date'] = m.group(1)

            # 基金评级
            m = re.search(r'基金评级\s*[：:]\s*(\S+)', text)
            if m:
                result['rating'] = m.group(1).strip()

        except Exception as e:
            print(f"  10jqka 页面解析失败 {code}: {e}")

        # ---- 2. 获取阶段收益率（ifindRank API）----
        try:
            time.sleep(random.uniform(0.2, 0.5))
            rank_url = f"{base}/ifindRank/quarter_year_{code}.json"
            rank_resp = self._retry_10jqka(rank_url, session, referer=fund_page_url, is_sub_request=True)
            rank_data = rank_resp.json()

            fq = rank_data.get('nowFqNetRate', {})
            # 字段映射
            rate_map = {
                'week': 'syl_1w', 'month': 'syl_1m',
                'tmonth': 'syl_3m', 'hyear': 'syl_6m',
                'nowyear': 'syl_ytd', 'year': 'syl_1y',
                'twoyear': 'syl_2y', 'tyear': 'syl_3y',
                'fyear': 'syl_5y', 'now': 'since_inception',
            }
            for src, dst in rate_map.items():
                val = fq.get(src, '')
                if val and val != '--':
                    result[dst] = val

            # 同类平均 + 沪深300
            avg = rank_data.get('nowCommonTypeAvgRate', {})
            if avg:
                result['benchmark_avg'] = avg
            hs300 = rank_data.get('now1B0300Rate', {})
            if hs300:
                result['benchmark_hs300'] = hs300

        except _HTTP_ERRORS as e:
            if '404' not in str(e):
                _bump_10jqka_fail()
                print(f"  10jqka 收益率获取失败 {code}: {e}")
        except Exception as e:
            print(f"  10jqka 收益率获取失败 {code}: {e}")

        # ---- 3. 获取最新净值（单位净值历史 JSON）----
        try:
            time.sleep(random.uniform(0.2, 0.5))
            nav_url = f"{base}/{code}/json/jsondwjz.json"
            nav_resp = self._retry_10jqka(nav_url, session, referer=fund_page_url, is_sub_request=True)
            nav_text = nav_resp.text

            # 格式: var dwjz_008983=[["20200707","1.0000"],...];
            m = re.search(r'=\s*(\[\[.*?\]\])\s*;?$', nav_text, re.DOTALL)
            if m:
                nav_data = json.loads(m.group(1))
                if nav_data:
                    raw_date = nav_data[-1][0]
                    if len(raw_date) == 8:
                        result['latest_nav_date'] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                    else:
                        result['latest_nav_date'] = raw_date
                    result['latest_nav'] = nav_data[-1][1]
                    # 前一日净值用于计算日涨幅
                    if len(nav_data) >= 2:
                        prev_nav = float(nav_data[-2][1])
                        cur_nav = float(nav_data[-1][1])
                        if prev_nav != 0:
                            result['daily_change'] = f"{(cur_nav - prev_nav) / prev_nav * 100:.2f}"

                    # 净值走势（最近20条）
                    result['nav_trend'] = [
                        {'date': item[0], 'nav': item[1]}
                        for item in nav_data[-20:]
                    ]
        except _HTTP_ERRORS as e:
            if '404' not in str(e):
                _bump_10jqka_fail()
                print(f"  10jqka 净值获取失败 {code}: {e}")
        except Exception as e:
            print(f"  10jqka 净值获取失败 {code}: {e}")

        # ---- 4. 获取累计净值 ----
        try:
            time.sleep(random.uniform(0.2, 0.5))
            ljjz_url = f"{base}/{code}/json/jsonljjz.json"
            ljjz_resp = self._retry_10jqka(ljjz_url, session, referer=fund_page_url, is_sub_request=True)
            ljjz_text = ljjz_resp.text
            m = re.search(r'=\s*(\[\[.*?\]\])\s*;?$', ljjz_text, re.DOTALL)
            if m:
                ljjz_data = json.loads(m.group(1))
                if ljjz_data:
                    result['cumulative_nav'] = ljjz_data[-1][1]
        except Exception:
            pass  # 累计净值非必须

        # Session 复用到下一个基金，不关闭
        return result if len(result) > 2 else None

    def get_fund_10jqka_full_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取同花顺爱基金完整详细信息（字段与天天基金保持一致）
        
        数据源:
        1. https://fund.10jqka.com.cn/{code}/              — 页面内嵌 JS 变量
        2. /{code}/json/jsondwjz.json                      — 单位净值历史
        3. /{code}/json/jsonljjz.json                      — 累计净值历史
        4. /ifindRank/quarter_year_{code}.json             — 阶段收益率
        
        参数:
            code: 6位基金代码
            
        返回:
            dict 或 None，字段结构与 get_fund_detail 保持一致
        """
        print(f"\n获取同花顺 {code} 详细信息...")
        
        base = "https://fund.10jqka.com.cn"
        result: Dict[str, Any] = {'code': code, 'source': '10jqka'}
        
        session = _get_10jqka_session()
        fund_page_url = f"{base}/{code}/"
        
        page_success = False
        
        try:
            try:
                resp = self._retry_10jqka(fund_page_url, session, max_retries=3, is_sub_request=False)
            except _HTTP_ERRORS as e:
                if '404' in str(e):
                    return None
                print(f"  10jqka 页面请求失败 {code}: {e}")
                _bump_10jqka_fail()
                return None
            except Exception as e:
                print(f"  10jqka 页面请求异常 {code}: {e}")
                _bump_10jqka_fail()
                return None
            
            resp.encoding = 'utf-8'
            raw_html = resp.text
            _TENJQKA_POOL.fail_streak = 0
            page_success = True
            
            time.sleep(random.uniform(0.3, 0.6))
            
            if _TENJQKA_WARM_LOCK.acquire(blocking=False):
                try:
                    _TENJQKA_COOKIES.update(session.cookies.get_dict())
                finally:
                    _TENJQKA_WARM_LOCK.release()
            
            text = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            m = re.search(r"fundName\s*=\s*'([^']+)'", raw_html)
            if m:
                result['name'] = m.group(1).strip()
            result['full_name'] = result.get('name', '')
            result['short_name'] = result.get('name', '')
            
            m = re.search(r"fundType\s*=\s*'([^']+)'", raw_html)
            if m:
                result['fund_type'] = m.group(1).strip()
            
            m = re.search(r"fundClrq\s*=\s*'([^']+)'", raw_html)
            if m:
                result['establish_date'] = m.group(1).strip()
            if not result.get('establish_date'):
                m = re.search(r'成立时间\s*[：:]\s*(\d{4}-\d{2}-\d{2})', text)
                if m:
                    result['establish_date'] = m.group(1)
            
            m = re.search(r'公司名称\s*[：:]\s*([\u4e00-\u9fa5A-Za-z（）()·]+)', text)
            if m:
                result['company'] = m.group(1).strip()
            if not result.get('company'):
                m = re.search(r'管理人\s*[：:]\s*([\u4e00-\u9fa5A-Za-z（）()·]+)', text)
                if m and m.group(1) not in ('基金档案', ''):
                    result['company'] = m.group(1).strip()
            
            m = re.search(r'var\s+managers\s*=\s*(\{.*?\})\s*;', raw_html, re.DOTALL)
            if m:
                try:
                    mgr = json.loads(m.group(1))
                    result['manager'] = '、'.join(mgr.keys())
                except json.JSONDecodeError:
                    pass
            if not result.get('manager'):
                m = re.search(r'基金经理\s*[：:]\s*(\S+)', text)
                if m:
                    result['manager'] = m.group(1).strip()
            
            m = re.search(r"configTotal\s*=\s*'([\d.]+)'", raw_html)
            if m:
                result['scale'] = m.group(1) + '亿元'
            if not result.get('scale'):
                m = re.search(r'基金规模\s*[：:]\s*([\d.]+亿元)', text)
                if m:
                    result['scale'] = m.group(1)
            
            m = re.search(r'基金规模\s*[：:]\s*([\d.]+亿份)', text)
            if m:
                result['share_size'] = m.group(1)
            
            m = re.search(r'基金评级\s*[：:]\s*(\S+)', text)
            if m:
                rating = m.group(1).strip()
                rating_map = {
                    '★★★★★': '低风险',
                    '★★★★': '中低风险',
                    '★★★': '中等风险',
                    '★★': '中高风险',
                    '★': '高风险',
                }
                result['risk_level'] = rating_map.get(rating, rating)
            
            if '开放申购' in text:
                result['trade_status'] = '开放申购'
            elif '暂停申购' in text:
                result['trade_status'] = '暂停申购'
            
            if '开放赎回' in text:
                result['redeem_status'] = '开放赎回'
            elif '暂停赎回' in text:
                result['redeem_status'] = '暂停赎回'
            
            m = re.search(r'最低申购\s*[：:]?\s*(\d+)元', text)
            if m:
                result['min_subscribe'] = m.group(1)
            
            m = re.search(r'累计分红\s*(\d+)\s*次', text)
            if m:
                result['dividend_count'] = m.group(1)
            
        except Exception as e:
            print(f"  10jqka 页面解析失败 {code}: {e}")
            if not page_success:
                return None
        
        if page_success:
            try:
                time.sleep(random.uniform(0.5, 1.0))
                rank_url = f"{base}/ifindRank/quarter_year_{code}.json"
                rank_resp = self._retry_10jqka(rank_url, session, max_retries=2, referer=fund_page_url, is_sub_request=True)
                rank_data = rank_resp.json()
                
                fq = rank_data.get('nowFqNetRate', {})
                rate_map = {
                    'week': 'syl_1w', 'month': 'syl_1m',
                    'tmonth': 'syl_3m', 'hyear': 'syl_6m',
                    'nowyear': 'syl_ytd', 'year': 'syl_1y',
                    'twoyear': 'syl_2y', 'tyear': 'syl_3y',
                    'fyear': 'syl_5y', 'now': 'since_inception',
                }
                for src, dst in rate_map.items():
                    val = fq.get(src, '')
                    if val and val != '--':
                        result[dst] = val
                
                hs300 = rank_data.get('now1B0300Rate', {})
                if hs300:
                    result['benchmark'] = f"沪深300: {hs300.get('now', '')}"
                
            except Exception as e:
                print(f"  ⚠ 10jqka 收益率获取失败 {code}（非致命）: {type(e).__name__}")
        
        nav_success = False
        if page_success:
            try:
                time.sleep(random.uniform(0.5, 1.0))
                nav_url = f"{base}/{code}/json/jsondwjz.json"
                nav_resp = self._retry_10jqka(nav_url, session, max_retries=3, referer=fund_page_url, is_sub_request=True)
                nav_text = nav_resp.text
                
                m = re.search(r'=\s*(\[\[.*?\]\])\s*;?$', nav_text, re.DOTALL)
                if m:
                    nav_data = json.loads(m.group(1))
                    if nav_data:
                        raw_date = nav_data[-1][0]
                        if len(raw_date) == 8:
                            result['latest_nav_date'] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                        else:
                            result['latest_nav_date'] = raw_date
                        result['latest_nav'] = nav_data[-1][1]
                        
                        if len(nav_data) >= 2:
                            prev_nav = float(nav_data[-2][1])
                            cur_nav = float(nav_data[-1][1])
                            if prev_nav != 0:
                                result['daily_change'] = f"{(cur_nav - prev_nav) / prev_nav * 100:.2f}"
                        
                        result['nav_trend'] = [
                            {'date': item[0], 'nav': item[1], 'equity_return': 0}
                            for item in nav_data[-20:]
                        ]
                        nav_success = True
            except Exception as e:
                print(f"  ⚠ 10jqka 净值获取失败 {code}（非致命）: {type(e).__name__}")
        
        if page_success and nav_success:
            try:
                time.sleep(random.uniform(0.5, 1.0))
                ljjz_url = f"{base}/{code}/json/jsonljjz.json"
                ljjz_resp = self._retry_10jqka(ljjz_url, session, max_retries=2, referer=fund_page_url, is_sub_request=True)
                ljjz_text = ljjz_resp.text
                m = re.search(r'=\s*(\[\[.*?\]\])\s*;?$', ljjz_text, re.DOTALL)
                if m:
                    ljjz_data = json.loads(m.group(1))
                    if ljjz_data:
                        result['cumulative_nav'] = ljjz_data[-1][1]
            except Exception:
                pass
        
        if not page_success or not nav_success:
            print(f"  ✗ 10jqka {code} 关键数据获取失败，跳过")
            return None
        
        defaults = [
            'name', 'full_name', 'short_name', 'fund_type', 'risk_level',
            'latest_nav', 'latest_nav_date', 'cumulative_nav', 'daily_change',
            'scale', 'scale_date', 'share_size',
            'company', 'custodian', 'manager',
            'establish_date', 'issue_date',
            'manage_fee', 'custodian_fee', 'service_fee',
            'subscribe_fee', 'purchase_fee', 'source_rate', 'rate', 'min_subscribe',
            'redeem_fee', 'redeem_detail',
            'syl_1w', 'syl_1m', 'syl_3m', 'syl_6m', 'syl_ytd',
            'syl_1y', 'syl_2y', 'syl_3y', 'since_inception',
            'dwjz', 'gsz', 'gszzl', 'jzrq', 'gztime',
            'trade_status', 'redeem_status', 'purchase_limit',
            'dividend_count', 'split_count',
            'benchmark', 'index_code', 'index_name',
            'holding_stocks', 'holdings_date',
        ]
        for key in defaults:
            result.setdefault(key, '')
        
        result.setdefault('nav_trend', [])
        result.setdefault('holding_stocks', [])
        result.setdefault('redeem_detail', [])
        
        return result if len(result) > 2 else None

    def get_fund_jbgk_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金基本概况（发行日期、份额规模、成立规模等）

        数据源: https://fundf10.eastmoney.com/jbgk_{code}.html

        参数:
            code: 6位基金代码

        返回:
            dict 或 None:
                - issue_date: 发行日期
                - share_size: 份额规模（亿份）
                - establish_scale: 成立规模（亿份）
        """
        url = f"https://fundf10.eastmoney.com/jbgk_{code}.html"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            resp.encoding = 'utf-8'
            resp.raise_for_status()
            # 去掉 HTML 标签，压缩空白
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()

            result: Dict[str, Any] = {}

            # 发行日期
            m = re.search(r'发行日期[：:]?\s*(\d{4}年\d{2}月\d{2}日)', text)
            if m:
                result['issue_date'] = m.group(1)

            # 份额规模
            m = re.search(r'份额规模[：:]?\s*([\d.]+)亿份', text)
            if m:
                result['share_size'] = m.group(1) + '亿份'

            # 成立规模
            m = re.search(r'成立规模[：:]?\s*([\d.]+)亿份', text)
            if m:
                result['establish_scale'] = m.group(1) + '亿份'

            return result if result else None
        except Exception as e:
            print(f"  获取基金概况失败 {code}: {e}")
            return None

    def get_fund_rate_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金交易费率（认购/申购/赎回费率）

        数据源: https://fundf10.eastmoney.com/jjfl_{code}.html

        参数:
            code: 6位基金代码

        返回:
            dict 或 None:
                - subscribe_fee: 最高认购费率
                - purchase_fee: 最高申购费率
                - redeem_fee: 最高赎回费率
                - redeem_detail: 赎回费率档位列表
        """
        url = f"https://fundf10.eastmoney.com/jjfl_{code}.html"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            resp.encoding = 'utf-8'
            resp.raise_for_status()
            # 去掉 HTML 标签，压缩空白
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()

            result: Dict[str, Any] = {}

            # 认购费率
            m = re.search(r'认购费率[^%]*?(\d+\.?\d*)%', text, re.DOTALL)
            if m:
                result['subscribe_fee'] = m.group(1) + '%'

            # 申购费率
            m = re.search(r'申购费率[^%]*?(\d+\.?\d*)%', text, re.DOTALL)
            if m:
                result['purchase_fee'] = m.group(1) + '%'

            # 赎回费率（取所有档位中的最大值）
            redeem_match = re.search(
                r'赎回费率(.+?)(?:运作费用|注[：:]|管理费率)',
                text, re.DOTALL
            )
            if redeem_match:
                redeem_text = redeem_match.group(1)
                rates = re.findall(r'(\d+\.?\d*)%', redeem_text)
                if rates:
                    max_rate = max(float(r) for r in rates)
                    result['redeem_fee'] = f"{max_rate}%"
                    result['redeem_detail'] = [
                        float(r) for r in rates
                    ]

            return result if result else None
        except Exception as e:
            print(f"  获取费率信息失败 {code}: {e}")
            return None

    def get_fund_realtime_nav(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金实时估值（盘中动态数据）
        
        数据源: http://fundgz.1234567.com.cn/js/{code}.js
        
        参数:
            code: 6位基金代码
            
        返回:
            dict 或 None:
                - fundcode: 基金代码
                - name: 基金简称
                - jzrq: 最新净值日期
                - dwjz: 最新单位净值（前一交易日真实值）
                - gsz: 实时估算净值
                - gszzl: 估算涨幅（%）
                - gztime: 估算数据生成时间
        """
        url = f"http://fundgz.1234567.com.cn/js/{code}.js"
        try:
            text = self.fetch_fund_data(url)

            # JSONP 格式: jsonpgz({...});
            match = re.search(r'jsonpgz\((.*?)\)\s*;', text, re.DOTALL)
            if not match:
                print(f"  实时估值解析失败: {code}")
                return None

            data = json.loads(match.group(1))
            return {
                'fundcode': data.get('fundcode', ''),
                'name': data.get('name', ''),
                'jzrq': data.get('jzrq', ''),
                'dwjz': data.get('dwjz', ''),
                'gsz': data.get('gsz', ''),
                'gszzl': data.get('gszzl', ''),
                'gztime': data.get('gztime', ''),
            }
        except Exception as e:
            print(f"  获取实时估值失败 {code}: {e}")
            return None

    def get_fund_pingzhong_data(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金品种详细数据（历史净值、收益率、持仓等）
        
        数据源: http://fund.eastmoney.com/pingzhongdata/{code}.js
        
        参数:
            code: 6位基金代码
            
        返回:
            dict 或 None:
                - code: 基金代码
                - name: 基金全称
                - source_rate: 原始申购费率（%）
                - rate: 折扣费率（%）
                - min_subscribe: 最小申购金额（元）
                - syl_1y: 近1月收益率（%）
                - syl_3y: 近3月收益率（%）
                - syl_6y: 近6月收益率（%）
                - syl_1n: 近1年收益率（%）
                - latest_nav: 最新单位净值
                - latest_nav_date: 最新净值日期
                - nav_trend: 单位净值走势列表（最近20条）
                - holding_stocks: 持仓股票代码列表（新格式）
                - shares_positions: 仓位测算列表（最近10条）
        """
        url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
        try:
            text = self.fetch_fund_data(url)

            result: Dict[str, Any] = {'code': code}

            # ---- 基本字段（正则提取 JS 变量） ----
            result['name'] = self._extract_js_string(text, 'fS_name')
            result['source_rate'] = self._extract_js_string(text, 'fund_sourceRate')
            result['rate'] = self._extract_js_string(text, 'fund_Rate')
            result['min_subscribe'] = self._extract_js_string(text, 'fund_minsg')

            # ---- 阶段收益率 ----
            result['syl_1y'] = self._extract_js_string(text, 'syl_1y')
            result['syl_3y'] = self._extract_js_string(text, 'syl_3y')
            result['syl_6y'] = self._extract_js_string(text, 'syl_6y')
            result['syl_1n'] = self._extract_js_string(text, 'syl_1n')

            # ---- 单位净值走势 Data_netWorthTrend ----
            nav_trend_raw = self._extract_js_json_array(text, 'Data_netWorthTrend')
            if nav_trend_raw:
                # 只保留最近 20 条，减少数据量
                trend = nav_trend_raw[-20:]
                result['nav_trend'] = [
                    {
                        'date': self._ts_to_date_str(item.get('x', 0)),
                        'nav': item.get('y', ''),
                        'equity_return': item.get('equityReturn', 0),
                    }
                    for item in trend
                ]
                # 最新净值
                latest = nav_trend_raw[-1]
                result['latest_nav'] = latest.get('y', '')
                result['latest_nav_date'] = self._ts_to_date_str(latest.get('x', 0))
            else:
                result['latest_nav'] = ''
                result['latest_nav_date'] = ''
                result['nav_trend'] = []

            # ---- 持仓股票代码 stockCodesNew ----
            result['holding_stocks'] = self._extract_js_array_literal(text, 'stockCodesNew')

            # ---- 仓位测算 Data_fundSharesPositions ----
            shares_raw = self._extract_js_array_literal_no_json(text, 'Data_fundSharesPositions')
            if shares_raw:
                result['shares_positions'] = [
                    {
                        'date': self._ts_to_date_str(item[0] if len(item) > 0 else 0),
                        'position': item[1] if len(item) > 1 else 0,
                    }
                    for item in shares_raw[-10:]  # 最近 10 条
                ]
            else:
                result['shares_positions'] = []

            return result

        except Exception as e:
            print(f"  获取品种数据失败 {code}: {e}")
            return None

    def get_fund_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单只基金完整详细信息

        数据源优先级：
        1. 主页 fund.eastmoney.com/{code}.html — 名称/净值/规模/持仓/收益率等大部分字段
        2. pingzhongdata — 历史净值走势(nav_trend)、仓位测算(shares_positions)
        3. fundgz — 盘中实时估值(dwjz/gsz/gszzl)
        4. FundMNDetailInformation — 全称/托管人/运营费率/业绩基准/投资策略
        5. jbgk — 发行日期/份额规模/成立规模
        6. jjfl — 认购/申购/赎回费率明细

        参数:
            code: 6位基金代码

        返回:
            dict 或 None
        """
        print(f"\n获取基金 {code} 详细信息...")

        # 主要数据源：主页（一次性获取大部分信息）
        page = self.get_fund_page_info(code)

        # 补充数据源（不阻塞，并行获取）
        pingzhong = self.get_fund_pingzhong_data(code)
        realtime = self.get_fund_realtime_nav(code)
        scale = self.get_fund_scale_info(code)
        jbgk = self.get_fund_jbgk_info(code)
        rate = self.get_fund_rate_info(code)

        if page is None and pingzhong is None:
            return None

        # 主页数据作为基础
        result = page if page else {'code': code}

        # ---- 合并 pingzhongdata（走势 + 持仓代码 + 折扣费率）----
        if pingzhong:
            result['source_rate'] = pingzhong.get('source_rate', '')
            result['rate'] = pingzhong.get('rate', '')
            result['nav_trend'] = pingzhong.get('nav_trend', [])
            result['shares_positions'] = pingzhong.get('shares_positions', [])
            # 如果主页没有持仓则用品种数据
            if not result.get('holding_stocks'):
                result['holding_stocks'] = pingzhong.get('holding_stocks', [])

        # ---- 合并实时估值 ----
        if realtime:
            result['dwjz'] = realtime.get('dwjz', '')
            result['gsz'] = realtime.get('gsz', '')
            result['gszzl'] = realtime.get('gszzl', '')
            result['jzrq'] = realtime.get('jzrq', '')
            result['gztime'] = realtime.get('gztime', '')

        # ---- 合并 FundMNDetailInformation（主页缺失的字段）----
        if scale:
            # 主页没有全称，用 API 补充
            result.setdefault('full_name', scale.get('full_name', ''))
            result['custodian'] = scale.get('custodian', '')
            result['manage_fee'] = scale.get('manage_fee', '')
            result['custodian_fee'] = scale.get('custodian_fee', '')
            result['service_fee'] = scale.get('service_fee', '')
            result['benchmark'] = scale.get('benchmark', '')
            result['index_code'] = scale.get('index_code', '')
            result['index_name'] = scale.get('index_name', '')
            result['investment_goal'] = scale.get('investment_goal', '')
            result['investment_strategy'] = scale.get('investment_strategy', '')
            # 主页已用中文显示风险等级；若缺失则从API数字映射
            scale_risk = scale.get('risk_level', '')
            if scale_risk and not result.get('risk_level'):
                risk_map = {'1': '低风险', '2': '中低风险', '3': '中等风险',
                            '4': '中高风险', '5': '高风险'}
                result['risk_level'] = risk_map.get(scale_risk, scale_risk)
            # 主页规模可能只有亿元文本，保留API精确数值
            result['scale_end_nav'] = scale.get('scale_end_nav', '')
            result['scale_net_nav'] = scale.get('scale_net_nav', '')
            if not result.get('scale_date'):
                result['scale_date'] = scale.get('scale_date', '')

        # ---- 合并 jbgk ----
        if jbgk:
            result['issue_date'] = jbgk.get('issue_date', '')
            result['share_size'] = jbgk.get('share_size', '')
            result['establish_scale'] = jbgk.get('establish_scale', '')

        # ---- 合并 jjfl ----
        if rate:
            result['subscribe_fee'] = rate.get('subscribe_fee', '')
            # 主页已有 purchase_fee（购买手续费），jjfl 作为补充
            if not result.get('purchase_fee'):
                result['purchase_fee'] = rate.get('purchase_fee', '')
            result['redeem_fee'] = rate.get('redeem_fee', '')
            result['redeem_detail'] = rate.get('redeem_detail', [])

        # ---- 填充默认值 ----
        defaults = [
            'name', 'full_name', 'fund_type', 'risk_level',
            'latest_nav', 'latest_nav_date', 'cumulative_nav', 'daily_change',
            'scale', 'scale_date', 'scale_end_nav', 'scale_net_nav',
            'company', 'custodian', 'manager', 'establish_date',
            'issue_date', 'share_size', 'establish_scale',
            'manage_fee', 'custodian_fee', 'service_fee',
            'subscribe_fee', 'purchase_fee', 'redeem_fee',
            'source_rate', 'rate', 'min_subscribe',
            'syl_1w', 'syl_1m', 'syl_3m', 'syl_6m', 'syl_ytd',
            'syl_1y', 'syl_2y', 'syl_3y', 'since_inception',
            'dwjz', 'gsz', 'gszzl', 'jzrq', 'gztime',
            'trade_status', 'redeem_status', 'purchase_limit',
            'dividend_count', 'split_count',
            'holdings_date',
            'index_code', 'index_name',
            'benchmark', 'investment_goal', 'investment_strategy',
        ]
        for key in defaults:
            result.setdefault(key, '')

        result.setdefault('nav_trend', [])
        result.setdefault('shares_positions', [])
        result.setdefault('holding_stocks', [])
        result.setdefault('redeem_detail', [])

        return result

    # ========== 内部解析工具 ==========

    @staticmethod
    def _extract_js_string(text: str, var_name: str) -> str:
        """从 JS 文本中提取字符串变量值，如 var fS_name = "xxx";"""
        pattern = rf'{var_name}\s*=\s*"([^"]*)"'
        match = re.search(pattern, text)
        return match.group(1) if match else ''

    @staticmethod
    def _extract_js_json_array(text: str, var_name: str) -> Optional[List[Any]]:
        """
        提取 JS 中的 JSON 对象数组，如:
          var Data_netWorthTrend = [{...}, {...}];
        """
        pattern = rf'{var_name}\s*=\s*(\[.*?\])\s*;'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_js_array_literal(text: str, var_name: str) -> List[Any]:
        """提取 JS 中的简单数组字面量，如 var stockCodesNew = ["a", "b"];"""
        pattern = rf'{var_name}\s*=\s*(\[.*?\])\s*;'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _extract_js_array_literal_no_json(text: str, var_name: str) -> Optional[List[Any]]:
        """
        提取 JS 中非标准 JSON 的数组（数字元组），如:
          var Data_fundSharesPositions = [[ts, num], [ts, num]];
        用 ast.literal_eval 解析。
        """
        pattern = rf'{var_name}\s*=\s*(\[\[.*?\]\])\s*;'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None
        try:
            return ast.literal_eval(match.group(1))
        except (SyntaxError, ValueError):
            return None

    # ---------- 导出 ----------

    def export_fund_list_to_txt(self, filepath: str) -> int:
        """
        将全部基金基本信息导出为逗号分隔的 csv 文件

        参数:
            filepath: 输出文件路径

        返回:
            int: 导出的基金数量
        """
        headers = ['code', 'short_name', 'full_name', 'type', 'pinyin']
        count = 0
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for fund in self.get_fund_structured_list():
                row = [str(fund.get(h, '')) for h in headers]
                writer.writerow(row)
                count += 1
                if count % 1000 == 0:
                    print(f"  已导出 {count} 条...")
        print(f"导出完成，共 {count} 条基金，保存至: {filepath}")
        return count

    def export_fund_detail_to_txt(self, filepath: str, limit: int = 0) -> int:
        """
        将基金详细信息导出为制表符分隔的 txt 文件

        参数:
            filepath: 输出文件路径
            limit: 最多导出数量，0 表示全部

        返回:
            int: 导出的基金数量
        """
        headers = [
            'code', 'name', 'full_name', 'short_name', 'fund_type', 'risk_level',
            'latest_nav', 'latest_nav_date', 'cumulative_nav', 'daily_change',
            'scale', 'scale_date', 'share_size',
            'company', 'custodian', 'manager',
            'establish_date', 'issue_date',
            'manage_fee', 'custodian_fee', 'service_fee',
            'subscribe_fee', 'purchase_fee', 'source_rate', 'rate', 'min_subscribe',
            'redeem_fee', 'redeem_detail',
            'syl_1w', 'syl_1m', 'syl_3m', 'syl_6m', 'syl_ytd',
            'syl_1y', 'syl_2y', 'syl_3y', 'since_inception',
            'dwjz', 'gsz', 'gszzl', 'jzrq', 'gztime',
            'trade_status', 'redeem_status', 'purchase_limit',
            'dividend_count', 'split_count',
            'benchmark', 'index_code', 'index_name',
            'holding_stocks', 'holdings_date',
            'nav_trend',
        ]

        count = 0
        # utf-8-sig 会在文件头写入 BOM，确保 Excel 正确识别中文编码
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for fund in self.get_fund_structured_list():
                code = fund['code']
                detail = self.get_fund_detail(code)
                if not detail:
                    print(f"  [{count + 1}] {code} 获取失败，跳过")
                    continue

                # 扁平化列表字段
                holdings = detail.get('holding_stocks', [])
                if isinstance(holdings, list) and holdings:
                    holdings_str = ';'.join(
                        f"{h['name']}:{h['ratio']}" if isinstance(h, dict) else str(h)
                        for h in holdings
                    )
                else:
                    holdings_str = ''

                nav_trend = detail.get('nav_trend', [])
                nav_trend_str = json.dumps(nav_trend, ensure_ascii=False) if nav_trend else ''

                redeem_detail = detail.get('redeem_detail', [])
                redeem_detail_str = ';'.join(str(r) for r in redeem_detail) if redeem_detail else ''

                row = [
                    str(detail.get('code', '')),
                    str(detail.get('name', '')),
                    str(detail.get('full_name', '')),
                    str(detail.get('short_name', fund.get('short_name', ''))),
                    str(detail.get('fund_type', '')),
                    str(detail.get('risk_level', '')),
                    str(detail.get('latest_nav', '')),
                    str(detail.get('latest_nav_date', '')),
                    str(detail.get('cumulative_nav', '')),
                    str(detail.get('daily_change', '')),
                    str(detail.get('scale', '')),
                    str(detail.get('scale_date', '')),
                    str(detail.get('share_size', '')),
                    str(detail.get('company', '')),
                    str(detail.get('custodian', '')),
                    str(detail.get('manager', '')),
                    str(detail.get('establish_date', '')),
                    str(detail.get('issue_date', '')),
                    str(detail.get('manage_fee', '')),
                    str(detail.get('custodian_fee', '')),
                    str(detail.get('service_fee', '')),
                    str(detail.get('subscribe_fee', '')),
                    str(detail.get('purchase_fee', '')),
                    str(detail.get('source_rate', '')),
                    str(detail.get('rate', '')),
                    str(detail.get('min_subscribe', '')),
                    str(detail.get('redeem_fee', '')),
                    redeem_detail_str,
                    str(detail.get('syl_1w', '')),
                    str(detail.get('syl_1m', '')),
                    str(detail.get('syl_3m', '')),
                    str(detail.get('syl_6m', '')),
                    str(detail.get('syl_ytd', '')),
                    str(detail.get('syl_1y', '')),
                    str(detail.get('syl_2y', '')),
                    str(detail.get('syl_3y', '')),
                    str(detail.get('since_inception', '')),
                    str(detail.get('dwjz', '')),
                    str(detail.get('gsz', '')),
                    str(detail.get('gszzl', '')),
                    str(detail.get('jzrq', '')),
                    str(detail.get('gztime', '')),
                    str(detail.get('trade_status', '')),
                    str(detail.get('redeem_status', '')),
                    str(detail.get('purchase_limit', '')),
                    str(detail.get('dividend_count', '')),
                    str(detail.get('split_count', '')),
                    str(detail.get('benchmark', '')),
                    str(detail.get('index_code', '')),
                    str(detail.get('index_name', '')),
                    holdings_str,
                    str(detail.get('holdings_date', '')),
                    nav_trend_str,
                ]
                writer.writerow(row)
                count += 1
                print(f"  [{count}] {code} {detail.get('name', '')} 已导出")

                if limit and count >= limit:
                    break

        print(f"导出完成，共 {count} 条基金详细数据，保存至: {filepath}")
        return count

    def export_all_fund_detail_to_csv(self, filepath: str, max_workers: int = 20) -> int:
        """
        多线程并发导出全部基金详细信息到 CSV（逗号分隔，UTF-8 BOM）

        每只基金仅请求主页（get_fund_page_info，1次HTTP），使用线程池加速。

        参数:
            filepath: 输出文件路径
            max_workers: 并发线程数（默认20）

        返回:
            int: 导出的基金数量
        """
        # 字段与 export_fund_detail_to_txt 保持一致
        headers = [
            'code', 'name', 'full_name', 'short_name', 'fund_type', 'risk_level',
            'latest_nav', 'latest_nav_date', 'cumulative_nav', 'daily_change',
            'scale', 'scale_date', 'share_size',
            'company', 'custodian', 'manager',
            'establish_date', 'issue_date',
            'manage_fee', 'custodian_fee', 'service_fee',
            'subscribe_fee', 'purchase_fee', 'source_rate', 'rate', 'min_subscribe',
            'redeem_fee', 'redeem_detail',
            'syl_1w', 'syl_1m', 'syl_3m', 'syl_6m', 'syl_ytd',
            'syl_1y', 'syl_2y', 'syl_3y', 'since_inception',
            'dwjz', 'gsz', 'gszzl', 'jzrq', 'gztime',
            'trade_status', 'redeem_status', 'purchase_limit',
            'dividend_count', 'split_count',
            'benchmark', 'index_code', 'index_name',
            'holding_stocks', 'holdings_date',
            'nav_trend',
        ]

        # 先获取全部基金列表（生成器一次性消费）
        print("正在获取基金列表...")
        fund_list = list(self.get_fund_structured_list())
        total = len(fund_list)
        print(f"共 {total} 只基金，开始并发获取详细信息（{max_workers} 线程）...")

        # 单线程收集结果，按期货号保序写入
        results: List[List[str]] = [[''] * len(headers) for _ in range(total)]

        # 预先填充每行已知字段
        for i, fund in enumerate(fund_list):
            results[i][0] = str(fund.get('code', ''))          # code
            results[i][3] = str(fund.get('short_name', ''))    # short_name

        completed = [0]
        lock = threading.Lock()

        def fetch_one(idx: int, code: str):
            try:
                info = self.get_fund_page_info(code)
            except Exception as e:
                print(f"  [{idx + 1}/{total}] {code} 请求异常: {e}")
                info = None

            if info is None:
                with lock:
                    completed[0] += 1
                return idx, None

            # 扁平化列表字段
            holdings = info.get('holding_stocks', [])
            if isinstance(holdings, list) and holdings:
                holdings_str = ';'.join(
                    f"{h['name']}:{h['ratio']}" if isinstance(h, dict) else str(h)
                    for h in holdings
                )
            else:
                holdings_str = ''

            row = [
                str(info.get('code', '')),
                str(info.get('name', '')),
                '',                                                          # full_name (API)
                '',                                                          # short_name (已预填)
                str(info.get('fund_type', '')),
                str(info.get('risk_level', '')),
                str(info.get('latest_nav', '')),
                str(info.get('latest_nav_date', '')),
                str(info.get('cumulative_nav', '')),
                str(info.get('daily_change', '')),
                str(info.get('scale', '')),
                str(info.get('scale_date', '')),
                '',                                                          # share_size (API)
                str(info.get('company', '')),
                '',                                                          # custodian (API)
                str(info.get('manager', '')),
                str(info.get('establish_date', '')),
                '',                                                          # issue_date (API)
                '',                                                          # manage_fee (API)
                '',                                                          # custodian_fee (API)
                '',                                                          # service_fee (API)
                '',                                                          # subscribe_fee (API)
                str(info.get('purchase_fee', '')),
                '',                                                          # source_rate (API)
                '',                                                          # rate (API)
                str(info.get('min_subscribe', '')),
                '',                                                          # redeem_fee (API)
                '',                                                          # redeem_detail (API)
                str(info.get('syl_1w', '')),
                str(info.get('syl_1m', '')),
                str(info.get('syl_3m', '')),
                str(info.get('syl_6m', '')),
                str(info.get('syl_ytd', '')),
                str(info.get('syl_1y', '')),
                str(info.get('syl_2y', '')),
                str(info.get('syl_3y', '')),
                str(info.get('since_inception', '')),
                '', '', '', '', '',                                          # 实时估值 (未请求)
                str(info.get('trade_status', '')),
                str(info.get('redeem_status', '')),
                str(info.get('purchase_limit', '')),
                str(info.get('dividend_count', '')),
                str(info.get('split_count', '')),
                '', '', '',                                                  # benchmark/index (API)
                holdings_str,
                str(info.get('holdings_date', '')),
                '',                                                          # nav_trend (API)
            ]
            with lock:
                completed[0] += 1
            return idx, row

        # 线程池并发请求
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_one, i, fund['code']): i
                for i, fund in enumerate(fund_list)
            }
            for future in as_completed(futures):
                idx, row = future.result()
                if row is not None:
                    results[idx] = row
                # 每100条打印进度
                c = completed[0]
                if c % 100 == 0 or c == total:
                    elapsed = time.time() - start_time
                    pct = c / total * 100
                    rate = c / elapsed if elapsed > 0 else 0
                    eta = (total - c) / rate if rate > 0 else 0
                    print(f"  进度 {c}/{total} ({pct:.1f}%)  速度 {rate:.1f}条/秒  预计剩余 {eta:.0f}秒")

        # 写入 CSV
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for i, row in enumerate(results):
                # 将预填的 short_name 合并进去
                row[3] = str(fund_list[i].get('short_name', ''))
                writer.writerow(row)

        elapsed = time.time() - start_time
        print(f"导出完成！共 {total} 条基金，耗时 {elapsed:.1f} 秒，保存至: {filepath}")
        return total

    def export_all_10jqka_to_csv(self, filepath: str, max_workers: int = 2) -> int:
        """
        多线程并发从同花顺（10jqka）导出全部基金详细信息到 CSV

        每只基金请求 4 个数据源（页面+收益率+净值+累计净值）。
        内部信号量限制真实并发为 2，每只基金间有随机延迟避免被限流。
        max_workers 建议 1-3，默认 2。

        参数:
            filepath: 输出文件路径
            max_workers: 线程池大小（默认2，信号量限流2）

        返回:
            int: 导出的基金数量
        """
        headers = [
            'code', 'name', 'fund_type', 'establish_date',
            'company', 'manager', 'manager_return',
            'scale', 'share_size', 'rating',
            'latest_nav', 'latest_nav_date', 'cumulative_nav', 'daily_change',
            'syl_1w', 'syl_1m', 'syl_3m', 'syl_6m', 'syl_ytd',
            'syl_1y', 'syl_2y', 'syl_3y', 'syl_5y', 'since_inception',
            'source',
        ]

        # 预热：先访问 10jqka 首页获取 Cookie
        self._warmup_10jqka()

        print("正在获取基金列表...")
        fund_list = list(self.get_fund_structured_list())
        total = len(fund_list)
        print(f"共 {total} 只基金，开始从 10jqka 并发获取详细信息（{max_workers} 线程，信号量限流2，基金间随机延迟0.5-1.5秒）...")

        results: List[List[str]] = [[''] * len(headers) for _ in range(total)]
        for i, fund in enumerate(fund_list):
            results[i][0] = str(fund.get('code', ''))

        completed = [0]
        lock = threading.Lock()

        def fetch_one(idx: int, code: str):
            # 每只基金间随机延迟，避免触发频率限制
            time.sleep(random.uniform(0.5, 1.5))
            try:
                info = self.get_fund_10jqka_info(code)
            except Exception as e:
                print(f"  [{idx + 1}/{total}] {code} 请求异常: {e}")
                info = None

            if info is None:
                with lock:
                    completed[0] += 1
                return idx, None

            nav_trend = info.get('nav_trend', [])
            nav_trend_str = json.dumps(nav_trend, ensure_ascii=False) if nav_trend else ''

            row = [
                str(info.get('code', '')),
                str(info.get('name', '')),
                str(info.get('fund_type', '')),
                str(info.get('establish_date', '')),
                str(info.get('company', '')),
                str(info.get('manager', '')),
                str(info.get('manager_return', '')),
                str(info.get('scale', '')),
                str(info.get('share_size', '')),
                str(info.get('rating', '')),
                str(info.get('latest_nav', '')),
                str(info.get('latest_nav_date', '')),
                str(info.get('cumulative_nav', '')),
                str(info.get('daily_change', '')),
                str(info.get('syl_1w', '')),
                str(info.get('syl_1m', '')),
                str(info.get('syl_3m', '')),
                str(info.get('syl_6m', '')),
                str(info.get('syl_ytd', '')),
                str(info.get('syl_1y', '')),
                str(info.get('syl_2y', '')),
                str(info.get('syl_3y', '')),
                str(info.get('syl_5y', '')),
                str(info.get('since_inception', '')),
                str(info.get('source', '10jqka')),
            ]
            with lock:
                completed[0] += 1
            return idx, row

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_one, i, fund['code']): i
                for i, fund in enumerate(fund_list)
            }
            for future in as_completed(futures):
                idx, row = future.result()
                if row is not None:
                    results[idx] = row
                c = completed[0]
                if c % 100 == 0 or c == total:
                    elapsed = time.time() - start_time
                    pct = c / total * 100
                    rate = c / elapsed if elapsed > 0 else 0
                    eta = (total - c) / rate if rate > 0 else 0
                    print(f"  进度 {c}/{total} ({pct:.1f}%)  速度 {rate:.1f}条/秒  预计剩余 {eta:.0f}秒")

        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in results:
                writer.writerow(row)

        elapsed = time.time() - start_time
        print(f"导出完成！共 {total} 条基金，耗时 {elapsed:.1f} 秒，保存至: {filepath}")
        return total

    @staticmethod
    def _ts_to_date_str(ts_ms: int) -> str:
        """毫秒 UTC 时间戳 → YYYY-MM-DD 字符串（北京时间）"""
        if not ts_ms:
            return ''
        dt = datetime.fromtimestamp((ts_ms + _UTC8_OFFSET_MS) / 1000, tz=timezone.utc)
        return dt.strftime('%Y-%m-%d')


if __name__ == "__main__":
    fl = FundList()

    # --- 演示 1：基金列表 ---
    print("=" * 50)
    print("基金列表（前5条）")
    print("=" * 50)
    count = 0
    for fund in fl.get_fund_structured_list():
        print(f"  {fund['code']}  {fund['short_name']}")
        count += 1
        if count >= 5:
            break

    # --- 演示 2：单只基金详细信息 ---
    print("\n" + "=" * 50)
    print("基金详细信息")
    print("=" * 50)
    detail = fl.get_fund_detail("001438")
    if detail:
        # ---- 基本信息 ----
        print(f"\n{'基金代码':<14}{detail.get('code', '')}")
        print(f"{'基金简称':<14}{detail.get('name', '')}")
        print(f"{'基金全称':<14}{detail.get('full_name', '')}")
        print(f"{'基金类型':<14}{detail.get('fund_type', '')}")
        print(f"{'风险等级':<14}{detail.get('risk_level', '')}")

        # ---- 发行/成立 ----
        print(f"\n--- 发行与成立 ---")
        print(f"{'发行日期':<14}{detail.get('issue_date', '')}")
        print(f"{'成立日期':<14}{detail.get('establish_date', '')}")
        print(f"{'成立规模':<14}{detail.get('establish_scale', '')}")

        # ---- 规模 ----
        print(f"\n--- 规模 ---")
        scale_str = detail.get('scale', '')
        scale_date = detail.get('scale_date', '')
        scale_end = detail.get('scale_end_nav', '')
        end_nav_str = f"{float(scale_end)/1e8:.2f}亿" if scale_end else ''
        print(f"{'基金规模':<14}{scale_str} ({scale_date})")
        if end_nav_str:
            print(f"{'净资产(精确)':<14}{end_nav_str}")
        print(f"{'份额规模':<14}{detail.get('share_size', '')}")

        # ---- 管理团队 ----
        print(f"\n--- 管理团队 ---")
        print(f"{'基金管理人':<14}{detail.get('company', '')}")
        print(f"{'基金托管人':<14}{detail.get('custodian', '')}")
        print(f"{'基金经理':<14}{detail.get('manager', '')}")

        # ---- 交易状态 ----
        print(f"\n--- 交易 ---")
        trade = detail.get('trade_status', '')
        redeem = detail.get('redeem_status', '')
        limit = detail.get('purchase_limit', '')
        print(f"{'交易状态':<14}{trade}")
        if redeem:
            print(f"{'赎回状态':<14}{redeem}")
        if limit:
            print(f"{'购买上限':<14}{limit}")

        # ---- 费率 ----
        print(f"\n--- 费率 ---")
        print(f"{'管理费':<14}{detail.get('manage_fee', '')}")
        print(f"{'托管费':<14}{detail.get('custodian_fee', '')}")
        print(f"{'销售服务费':<14}{detail.get('service_fee', '')}")
        print(f"{'最高认购费率':<14}{detail.get('subscribe_fee', '')}")
        print(f"{'申购费率':<14}{detail.get('purchase_fee', '')}")
        print(f"{'最高赎回费率':<14}{detail.get('redeem_fee', '')}")
        redeem_detail = detail.get('redeem_detail', [])
        if redeem_detail:
            print(f"{'赎回费率档位':<14}{redeem_detail}")
        source_rate = detail.get('source_rate', '')
        rate = detail.get('rate', '')
        if source_rate:
            print(f"{'申购原费率':<14}{source_rate}%")
        if rate:
            print(f"{'申购折后费率':<14}{rate}%")
        print(f"{'起购金额':<14}{detail.get('min_subscribe', '')}元")

        # ---- 跟踪指数 ----
        index_code = detail.get('index_code', '')
        index_name = detail.get('index_name', '')
        if index_code and index_code != '--':
            print(f"\n{'跟踪指数':<14}{index_name}({index_code})")

        # ---- 业绩基准 ----
        benchmark = detail.get('benchmark', '')
        if benchmark:
            print(f"{'业绩基准':<14}{benchmark}")

        # ---- 净值 ----
        print(f"\n--- 净值 ---")
        print(f"{'单位净值':<14}{detail.get('latest_nav', '')} "
              f"({detail.get('latest_nav_date', '')})  "
              f"日涨幅: {detail.get('daily_change', '')}%")
        print(f"{'累计净值':<14}{detail.get('cumulative_nav', '')}")
        print(f"{'盘中估算净值':<14}{detail.get('gsz', '')}  "
              f"估算涨幅: {detail.get('gszzl', '')}%")
        print(f"{'上一交易日净值':<14}{detail.get('dwjz', '')}  "
              f"({detail.get('jzrq', '')})")

        # ---- 收益率 ----
        print(f"\n--- 收益率 ---")
        print(f"{'近1周':<14}{detail.get('syl_1w', '')}%")
        print(f"{'近1月':<14}{detail.get('syl_1m', '')}%")
        print(f"{'近3月':<14}{detail.get('syl_3m', '')}%")
        print(f"{'近6月':<14}{detail.get('syl_6m', '')}%")
        print(f"{'今年来':<14}{detail.get('syl_ytd', '')}%")
        print(f"{'近1年':<14}{detail.get('syl_1y', '')}%")
        print(f"{'近2年':<14}{detail.get('syl_2y', '')}%")
        print(f"{'近3年':<14}{detail.get('syl_3y', '')}%")
        print(f"{'成立来':<14}{detail.get('since_inception', '')}%")

        # ---- 分红 ----
        dividend = detail.get('dividend_count', '')
        split_count = detail.get('split_count', '')
        if dividend or split_count:
            print(f"\n--- 分红/拆分 ---")
            print(f"{'分红次数':<14}{dividend}")
            print(f"{'拆分次数':<14}{split_count}")

        # ---- 持仓 ----
        holdings = detail.get('holding_stocks', [])
        if holdings:
            print(f"\n前十大持仓 ({detail.get('holdings_date', '')}):")
            for h in holdings[:10]:
                if isinstance(h, dict):
                    print(f"  {h.get('name', ''):<12} {h.get('ratio', '')}")
                else:
                    print(f"  {h}")

        # ---- 走势 ----
        nav_trend = detail.get('nav_trend', [])
        if nav_trend:
            print(f"\n最近净值走势:")
            for nav in nav_trend[-5:]:
                print(f"  {nav['date']}  NAV={nav['nav']}  回报率={nav['equity_return']}%")
    else:
        print("获取详细信息失败")

    # --- 演示 3：全量导出 CSV ---
    print("\n" + "=" * 50)
    print("全量导出基金信息到 CSV")
    print("=" * 50)
    import os
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fund_detail_export.csv")
    fl.export_all_fund_detail_to_csv(output_path, max_workers=30)

