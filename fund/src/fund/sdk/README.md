# fund/sdk 模块文档

## 概述

`fund/sdk` 是基金数据 SDK，提供从天天基金网（eastmoney.com）拉取基金列表、基金持仓明细等数据的完整能力，并包含通用的 HTTP 请求工具和 HTML 解析示例。

## 文件结构

```
fund/sdk/
├── __init__.py              # 包初始化（空）
├── fund_list.py             # 基金列表数据获取
├── fund_stock_list.py       # 基金持仓明细获取
├── fund_stock_list.txt      # 持仓数据输出样例
├── link_data_fetcher.py     # 通用 HTTP 请求封装
├── parse_text.py            # HTML 表格解析示例
└── 工作簿1.xlsx             # 数据工作簿
```

---

## 1. fund_list.py — 基金列表获取 + 详细信息爬取

### 类: `FundList`

从东方财富网获取全部公募基金列表，并可爬取单只基金的详细信息（净值、收益率、持仓、规模等）。

### 数据源

| 数据源 | URL | 优先级 | 说明 |
|--------|-----|--------|------|
| ⭐ 基金主页 | `http://fund.eastmoney.com/{code}.html` | **主要** | 服务端渲染，一次提取：名称/净值/规模/持仓/收益率/交易状态等 |
| 实时估值 | `http://fundgz.1234567.com.cn/js/{code}.js` | 补充 | 盘中动态净值估算（JSONP） |
| 品种数据 | `http://fund.eastmoney.com/pingzhongdata/{code}.js` | 补充 | 历史净值走势(nav_trend)、仓位测算 |
| 规模信息 | `https://fundmobapi.eastmoney.com/FundMNewApi/FundMNDetailInformation` | 补充 | 全称/托管人/运营费率/业绩基准/投资策略 |
| 基本概况 | `https://fundf10.eastmoney.com/jbgk_{code}.html` | 补充 | 发行日期、份额规模、成立规模 |
| 交易费率 | `https://fundf10.eastmoney.com/jjfl_{code}.html` | 补充 | 认购/申购/赎回费率明细 |
| 基金列表 | `http://fund.eastmoney.com/js/fundcode_search.js` | 独立 | 全量基金基本信息 |

---

### 方法

#### 基金列表相关

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `fetch_fund_data(url)` | `url: str` | `str` | HTTP GET 获取原始文本，UA 伪装浏览器 |
| `extract_js_array(text)` | `text: str` | `str` | 用正则提取 JS 变量中的数组字面量 |
| `parse_js_array(js_array_str)` | `js_array_str: str` | `List[List]` | 用 `ast.literal_eval` 安全解析 JS 数组 |
| `convert_to_structured_data(raw_list)` | `raw_list: List[List]` | `Generator[Dict]` | 转换为结构化字典的**生成器** |
| `get_fund_structured_list()` | — | `Generator[Dict]` | 主入口：链式调用上述方法，返回迭代器 |

#### 基金详细信息相关

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_fund_page_info(code)` | `code: str` | `Optional[Dict]` | ⭐ **主要入口**：从主页提取名称/净值/规模/持仓/收益率/交易状态 |
| `get_fund_realtime_nav(code)` | `code: str` | `Optional[Dict]` | 获取实时估值（单位净值、估算净值、估算涨幅） |
| `get_fund_pingzhong_data(code)` | `code: str` | `Optional[Dict]` | 获取品种详细数据（历史净值走势、仓位测算） |
| `get_fund_scale_info(code)` | `code: str` | `Optional[Dict]` | 获取基金全称/托管人/运营费率/投资目标（移动API） |
| `get_fund_jbgk_info(code)` | `code: str` | `Optional[Dict]` | 获取基本概况（发行日期、份额规模、成立规模） |
| `get_fund_rate_info(code)` | `code: str` | `Optional[Dict]` | 获取交易费率（认购/申购/赎回费率） |
| `get_fund_detail(code)` | `code: str` | `Optional[Dict]` | **合并6个数据源**，主页为主、API补充，返回完整信息 |
| `get_fund_10jqka_info(code)` | `code: str` | `Optional[Dict]` | 🔶 从**同花顺**（fund.10jqka.com.cn）获取基金信息 |
| `export_fund_list_to_txt(filepath)` | `filepath: str` | `int` | 导出全部基金基本列表到 CSV（逗号分隔，UTF-8 BOM） |
| `export_fund_detail_to_txt(filepath, limit)` | `filepath: str`, `limit: int=0` | `int` | 导出基金详细信息到 CSV（含API补充字段，limit=0全量） |
| `export_all_fund_detail_to_csv(filepath, max_workers)` | `filepath: str`, `max_workers: int=20` | `int` | ⚡ **全量并发导出**：从东方财富获取全部基金主页信息，~118条/秒 |
| `export_all_10jqka_to_csv(filepath, max_workers)` | `filepath: str`, `max_workers: int=15` | `int` | 🔶 **全量并发导出**：从同花顺获取全部基金信息，含收益率+净值+公司名 |

---

### 基金列表格式

每个基金记录为 `dict`，约 13000+ 条：

```python
{
    "code":        "000001",    # 基金代码
    "short_name":  "华夏成长",   # 基金简称
    "full_name":   "华夏成长混合", # 基金全称
    "type":        "混合型",     # 基金类型
    "pinyin":      "HXCHH"      # 拼音简写
}
```

### 基金详细信息格式 (`get_fund_detail`)

> ⭐ 标注的字段来自**主页**（一次请求即可获取），其余来自补充 API。

```python
{
    # ---- 基本信息（来自主页）⭐ ----
    "code":         "001438",           # 基金代码
    "name":         "易方达瑞享混合E",   # ⭐ 基金简称
    "full_name":    "易方达瑞享灵活配置混合型证券投资基金",  # API: 基金全称
    "fund_type":    "混合型-灵活",       # ⭐ 基金类型
    "risk_level":   "中高风险",          # ⭐ 风险等级（中文）

    # ---- 发行与成立 ----
    "issue_date":   "2015年06月24日",    # jbgk: 发行日期
    "establish_date":"2015-06-26",       # ⭐ 成立日期
    "establish_scale":"2.138亿份",       # jbgk: 成立规模

    # ---- 净值（来自主页）⭐ ----
    "latest_nav":   "9.5369",           # ⭐ 最新单位净值
    "latest_nav_date":"2026-05-22",     # ⭐ 净值日期
    "cumulative_nav":"9.5369",          # ⭐ 累计净值
    "daily_change": "4.01",             # ⭐ 日增长率（%）
    # ---- 实时估值（来自 fundgz）----
    "dwjz":         "9.5369",           # 上一交易日单位净值
    "jzrq":         "2026-05-22",       # 净值日期
    "gsz":          "9.92",             # 盘中实时估算净值
    "gszzl":        "4.01",             # 估算涨幅（%）
    "gztime":       "2026-05-23 15:00", # 估算时间

    # ---- 规模 ----
    "scale":        "24.93亿元",        # ⭐ 基金规模（页面文本）
    "scale_date":   "2026-03-31",        # ⭐ 规模截止日期
    "scale_end_nav": 2493172890.64,     # API: 净资产（元，精确值）
    "share_size":   "3.9836亿份",        # jbgk: 份额规模

    # ---- 管理团队（来自主页）⭐ ----
    "company":      "易方达基金",        # ⭐ 基金管理人
    "manager":      "武阳",             # ⭐ 基金经理
    "custodian":    "农业银行",          # API: 基金托管人

    # ---- 交易状态（来自主页）⭐ ----
    "trade_status": "限大额",           # ⭐ 交易状态
    "redeem_status":"开放赎回",          # ⭐ 赎回状态
    "purchase_limit":"10.00万元",        # ⭐ 购买上限

    # ---- 费率 ----
    "purchase_fee": "0.00%",            # ⭐ 购买手续费
    "manage_fee":   "0.80%",            # API: 管理费（运营）
    "custodian_fee":"0.15%",            # API: 托管费（运营）
    "service_fee":  "0.20%",            # API: 销售服务费（运营）
    "subscribe_fee":"0.00%",            # jjfl: 最高认购费率
    "redeem_fee":   "1.50%",            # jjfl: 最高赎回费率
    "redeem_detail":[1.50, 0.50, 0.00],# jjfl: 赎回费率档位
    "source_rate":  "0.00",             # pingzhongdata: 申购原费率
    "rate":         "0.00",             # pingzhongdata: 申购折后费率
    "min_subscribe":"10",               # ⭐ 起购金额（从data-minsg提取）

    # ---- 阶段收益率（来自主页）⭐ ----
    "syl_1m":       "8.80",             # ⭐ 近1月
    "syl_3m":       "58.11",            # ⭐ 近3月
    "syl_6m":       "115.78",           # ⭐ 近6月
    "syl_1y":       "303.58",           # ⭐ 近1年
    "syl_2y":       "324.24",           # ⭐ 近2年
    "syl_3y":       "253.09",           # ⭐ 近3年
    "since_inception":"853.69",         # ⭐ 成立以来

    # ---- 分红/拆分（来自主页）⭐ ----
    "dividend_count":"0",               # ⭐ 分红次数
    "split_count":  "0",                # ⭐ 拆分次数

    # ---- 业绩/指数（来自 API）----
    "benchmark":    "中证500指数收益率*85%+...",  # 业绩比较基准
    "index_code":   "--",               # 跟踪指数代码
    "index_name":   "--",               # 跟踪指数名称
    "investment_goal": "在控制风险的前提下...",  # 投资目标
    "investment_strategy": "...",       # 投资策略

    # ---- 持仓（来自主页）⭐ ----
    "holding_stocks": [                 # ⭐ 前十大持仓（名称+占比）
        {"name": "新易盛", "ratio": "9.78%"},
        {"name": "长芯博创", "ratio": "9.77%"},
        ...
    ],
    "holdings_date":"2026-03-31",       # ⭐ 持仓截止日期

    # ---- 净值走势（来自 pingzhongdata）----
    "nav_trend": [
        {"date": "2026-05-22", "nav": 9.5369, "equity_return": 0.5},
        ...
    ],
    "shares_positions": [              # 仓位测算（最近10条）
        {"date": "2026-05-21", "position": 95.0},
        ...
    ]
}
```

---

### 使用示例

```python
from fund_list import FundList

fl = FundList()

# --- 获取基金列表 ---
for fund in fl.get_fund_structured_list():
    print(f"{fund['code']} - {fund['short_name']}")

# --- 获取单只基金详细信息（主页为主，API补充）---
detail = fl.get_fund_detail("001438")
print(f"基金简称: {detail['name']}")
print(f"基金全称: {detail['full_name']}")
print(f"基金类型: {detail['fund_type']}  风险: {detail['risk_level']}")
print(f"净值: {detail['latest_nav']} ({detail['latest_nav_date']})  日涨幅: {detail['daily_change']}%")
print(f"累计净值: {detail['cumulative_nav']}")
print(f"规模: {detail['scale']} ({detail['scale_date']})")
print(f"管理人: {detail['company']}  经理: {detail['manager']}")
print(f"申购费: {detail['purchase_fee']}  管理费: {detail['manage_fee']}")
print(f"交易状态: {detail['trade_status']}  赎回: {detail['redeem_status']}")
print(f"收益率: 近1月 {detail['syl_1m']}%  近3月 {detail['syl_3m']}%  近1年 {detail['syl_1y']}%")
print(f"成立来: {detail['since_inception']}%")
print(f"分红: {detail['dividend_count']}次  持仓: {detail['holding_stocks'][:3]}...")

# --- 只获取主页信息（最快，一次请求）---
page = fl.get_fund_page_info("001438")
if page:
    print(f"名称: {page['name']}  净值: {page['latest_nav']}  规模: {page['scale']}")

# --- 只获取规模信息 ---
scale = fl.get_fund_scale_info("001438")
if scale:
    print(f"净资产规模: {float(scale['scale_end_nav'])/1e8:.2f}亿（{scale['scale_date']}）")
    print(f"管理人: {scale['company']}  托管人: {scale['custodian']}")
    print(f"基金全称: {scale['full_name']}  类型: {scale['fund_type']}")

# --- 只获取基本概况 ---
jbgk = fl.get_fund_jbgk_info("001438")
if jbgk:
    print(f"发行日期: {jbgk['issue_date']}  份额规模: {jbgk['share_size']}")

# --- 只获取交易费率 ---
rate = fl.get_fund_rate_info("001438")
if rate:
    print(f"认购费: {rate['subscribe_fee']}  申购费: {rate['purchase_fee']}")
    print(f"最高赎回费: {rate['redeem_fee']}")

# --- 只获取实时估值（最快）---
nav = fl.get_fund_realtime_nav("001438")
print(f"估算净值: {nav['gsz']}  涨幅: {nav['gszzl']}%")
```

> **注意**：`get_fund_structured_list()` 返回生成器，只能迭代一次。如需多次使用，请先 `list()` 包装。

### 导出使用示例

```python
from fund_list import FundList

fl = FundList()

# --- 导出全部基金基本列表（code, name, type, pinyin）---
fl.export_fund_list_to_txt("fund_list.csv")

# --- 导出前 N 只基金详细信息（含API补充字段）---
fl.export_fund_detail_to_txt("fund_detail_top100.csv", limit=100)

# --- ⚡ 全量并发导出全部基金主页信息（东方财富，推荐，~3-4分钟完成 26800 只）---
fl.export_all_fund_detail_to_csv("fund_detail_eastmoney.csv", max_workers=30)

# --- 🔶 全量并发导出全部基金信息（同花顺，~30-40分钟，3个API/基金）---
fl.export_all_10jqka_to_csv("fund_detail_10jqka.csv", max_workers=10)
```

### 同花顺（10jqka）数据源

数据来自 `https://fund.10jqka.com.cn/{code}/`，通过 3 个端点获取：

| 数据源 | URL | 说明 |
|--------|-----|------|
| 基金主页 | `https://fund.10jqka.com.cn/{code}/` | 页面内嵌 JS 变量：名称/类型/成立日/规模/经理/资产配置 |
| 阶段收益率 | `/ifindRank/quarter_year_{code}.json` | 含同类平均/沪深300对比：近1周~近5年/成立来 |
| 单位净值 | `/{code}/json/jsondwjz.json` | 全量历史净值 + 20条走势 |
| 累计净值 | `/{code}/json/jsonljjz.json` | 累计净值 |

**10jqka 导出字段（24列）：**

| code | name | fund_type | establish_date | company | manager |
| scale | latest_nav | latest_nav_date | cumulative_nav | daily_change |
| syl_1w | syl_1m | syl_3m | syl_6m | syl_ytd | syl_1y | syl_2y | syl_3y | syl_5y | since_inception |

### CSV 导出字段说明

导出 CSV 包含 **53 个字段**，逗号分隔，UTF-8 BOM（Excel 直接打开不乱码）：

| 分类 | 字段 | `export_all_fund_detail_to_csv`（主页） | `export_fund_detail_to_txt`（全API） |
|------|------|:---:|:---:|
| 基本 | code, name, full_name, short_name, fund_type, risk_level | ✅(部分) | ✅ |
| 净值 | latest_nav, latest_nav_date, cumulative_nav, daily_change | ✅ | ✅ |
| 实时估值 | dwjz, gsz, gszzl, jzrq, gztime | | ✅ |
| 规模 | scale, scale_date, share_size, scale_end_nav | ✅(部分) | ✅ |
| 管理 | company, custodian, manager | ✅(部分) | ✅ |
| 日期 | establish_date, issue_date | ✅(部分) | ✅ |
| 费率 | manage_fee, custodian_fee, service_fee, subscribe_fee, purchase_fee, source_rate, rate, min_subscribe, redeem_fee, redeem_detail | ✅(部分) | ✅ |
| 收益率 | syl_1w, syl_1m, syl_3m, syl_6m, syl_ytd, syl_1y, syl_2y, syl_3y, since_inception | ✅ | ✅ |
| 交易 | trade_status, redeem_status, purchase_limit | ✅ | ✅ |
| 分红 | dividend_count, split_count | ✅ | ✅ |
| 持仓 | holding_stocks, holdings_date | ✅ | ✅ |
| 净值走势 | nav_trend | | ✅ |
| 其他 | benchmark, index_code, index_name | | ✅ |

---

## 2. fund_stock_list.py — 基金持仓明细

### 类: `FundStockListTool`

获取指定基金在历年各报告期的股票持仓明细。

### 数据源

`http://fundf10.eastmoney.com/FundArchivesDatas.aspx`（天天基金网基金档案）

### 依赖

- `FundList` (from `fund_list`)
- `requests` + `BeautifulSoup` (from `bs4`)

### 方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_fund_list()` | — | `Generator` | 委托 `FundList.get_fund_structured_list()`，获取全量基金列表 |
| `get_all_fund_codes()` | — | `Generator` | 从基金列表 yield 每个基金的 `code` |
| `get_fund_holdings_by_year(fund_code, year, topline)` | `fund_code: str`, `year: int`, `topline: int=100` | `List[Dict]` | 获取指定基金、指定年份的持仓数据 |
| `get_fund_stock_list_to_file(fund_codes, file_path)` | `fund_codes: list`, `file_path: str` | `None` | 批量获取并写入文件 |

### `get_fund_holdings_by_year` 返回格式

```python
{
    "code":           "011665",         # 基金代码
    "report_cycle":   "2025-06-30",     # 报告期
    "stock_code":     "000333",         # 股票代码
    "stock_name":     "美的集团",        # 股票名称
    "holding_ratio":  "9.16%",          # 占净值比例
    "shares_held":    "51.86",          # 持股数（万股）
    "market_value":   "29,529.60"       # 持仓市值（万元）
}
```

### 处理流程

```
获取基金列表 → 遍历每个基金 → 从当前年份回溯到2016年
  → 每年请求持仓页面 → BeautifulSoup 解析 HTML 表格
  → 提取股票代码/名称/净值比例/持股数/市值 → 写入文件
```

### 使用示例

```python
from fund_stock_list import FundStockListTool

tool = FundStockListTool()

# 获取指定基金的持仓
holdings = tool.get_fund_holdings_by_year("011665", 2025, 20)
for h in holdings:
    print(f"{h['stock_name']}: {h['holding_ratio']}")

# 批量获取并保存到文件
tool.get_fund_stock_list_to_file(
    fund_codes=["011665", "011399"],
    file_path="fund_stock_list.txt"
)
```

---

## 3. link_data_fetcher.py — 通用 HTTP 请求封装

### 类: `LinkDataFetcher`

一个可复用的 HTTP 客户端，支持重试、超时控制、Session 复用。

### 构造函数

```python
LinkDataFetcher(timeout=10, retries=3)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `timeout` | `int` | 10 | 请求超时（秒） |
| `retries` | `int` | 3 | 失败重试次数 |

### 方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `fetch_data(url, params, headers, method, data)` | 见下方 | `dict` | 核心请求方法 |
| `close()` | — | — | 关闭 Session |

### `fetch_data` 返回值

```python
# 成功
{
    "success": True,
    "status_code": 200,
    "content_type": "application/json",
    "data": { ... },           # JSON→dict, HTML/Text→str, 其他→bytes
    "headers": { ... },
    "url": "https://..."
}

# 失败
{
    "success": False,
    "error": "错误描述"
}
```

### 特点

- **Session 复用**：同 host 连接复用，减少握手开销
- **重试机制**：超时时自动重试（间隔 1 秒），HTTP 错误直接返回不重试
- **智能解析**：根据 `Content-Type` 自动判断 JSON / HTML / 二进制

---

## 4. parse_text.py — HTML 表格解析示例

独立的 HTML 解析脚本，演示如何用 BeautifulSoup 从天天基金网持仓页面 HTML 片段中提取结构化数据。

### 功能

解析 `<table class="w782 comm tzxq">` 表格，提取基金持仓明细：

| 列 | 说明 |
|----|------|
| 序号 | 持仓排名 |
| 股票代码 | 股票代码 |
| 股票名称 | 股票名称 |
| 占净值比例 | 第 7 列 |
| 持股数(万股) | 第 8 列 |
| 持仓市值(万元) | 第 9 列 |

最终输出 JSON。

### 使用

```bash
python parse_text.py
```

---

## 5. fund_stock_list.txt — 输出样例

分隔符为 `\t`，单行格式：

```
基金代码	报告期	股票名称(股票代码):	占净值比例	持股数	X	万股	市值	X	万元
```

示例：

```
011665	2026-03-31	中际旭创(300308):	9.16%	持股数	51.86	万股	市值	29,529.60	万元
```

---

## 依赖

```
requests >= 2.28
beautifulsoup4 >= 4.11
```

安装：

```bash
pip install requests beautifulsoup4
```

---

## 模块关系图

```
link_data_fetcher.py          parse_text.py
  (通用 HTTP 工具)              (HTML 解析示例)
        │
        ▼
  fund_list.py ◄──────────── fund_stock_list.py
  (基金列表 + 详细信息)          (基金持仓明细)
        │                           │
        │  ┌─ fund.eastmoney.com/{code}.html  (⭐ 主页，主要数据源)
        │  │ (名称/净值/规模/持仓/收益率/交易状态)
        │  ├─ pingzhongdata ────────┤
        │  │ (历史净值走势/仓位测算)  │
        │  ├─ fundgz ───────────────┘
        │  │ (实时估值)              ▼
        │  ├─ FundMNDetailInformation  fund_stock_list.txt
        │  │ (全称/托管人/运营费率)     (输出文件)
        │  ├─ jbgk (基本概况页)
        │  │ (发行日期/份额规模)
        │  ├─ jjfl (费率页)
        │  │ (认购/申购/赎回费率)
        │  └─ fundcode_search
        │     (全量基金列表)
        │
        ▼
  get_fund_detail(code)
    → 主页为主 + API补充 → 完整信息
```

- **数据源优先级**：主页（⭐）为主，一次请求获取大部分字段；API 作为补充
- `fund_list.py` 内部有独立的 HTTP 请求和 JS 解析逻辑，不依赖 `link_data_fetcher.py`
- HTML 页面（主页/jbgk/jjfl）通过正则解析提取数据
- `fund_stock_list.py` 依赖 `fund_list.py`（复用基金列表）

获取那个url失败要等0.5s后重试，并打印重试提示

增加另外一种实现同花顺爱基金的数据，输出数据和文件格式与现有的天天基金一致