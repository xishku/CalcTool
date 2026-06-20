# LeetCode 自动化刷题工具 — 软件需求规格说明书 (SRS)

## 1. 项目概述

### 1.1 项目名称
LeetCode 自动化刷题工具

### 1.2 项目目标
构建一个自动化工具，遍历 LeetCode 中文站（https://leetcode.cn/problemset/）题库，读取题目内容，解析题目结构，自动生成 JavaScript 解法代码，提交并获取判题结果，最终输出提交分析报告。

### 1.3 目标用户
- 需要批量刷题验证算法能力的开发者
- 需要自动化测试 LeetCode 提交流程的工具开发者

### 1.4 技术栈
- 语言：Python（爬虫/解析/调度）+ JavaScript（解题代码生成）
- HTTP 客户端：requests / httpx
- HTML/Markdown 解析：BeautifulSoup / markdown
- GraphQL 接口：LeetCode 内部 API

---

## 2. 功能需求

### 2.1 用户认证 (Authentication)
| 编号 | 需求 | 优先级 |
|------|------|--------|
| F1.1 | 支持用户提供 LeetCode Cookie / Token 进行身份认证 | P0 |
| F1.2 | 验证 Token 有效性，无效时提示用户重新提供 | P0 |
| F1.3 | 支持从环境变量或配置文件读取 Token | P1 |

### 2.2 题库遍历 (Problem Set Traversal)
| 编号 | 需求 | 优先级 |
|------|------|--------|
| F2.1 | 获取全量题库列表（通过 LeetCode GraphQL API） | P0 |
| F2.2 | 支持按难度（Easy/Medium/Hard）筛选 | P1 |
| F2.3 | 支持按标签/类型（数组、字符串、动态规划等）筛选 | P1 |
| F2.4 | 支持分页/分批获取，避免请求过于密集 | P1 |
| F2.5 | 支持指定题目 ID 或 Slug 精确获取单题 | P0 |

### 2.3 题目解析 (Problem Parsing)
| 编号 | 需求 | 优先级 |
|------|------|--------|
| F3.1 | 解析题目基本信息：题号、标题、难度、标签（题目类型） | P0 |
| F3.2 | 解析题目内容（Markdown/HTML 转纯文本或结构化数据） | P0 |
| F3.3 | 解析输入/输出示例，保留格式 | P0 |
| F3.4 | 解析代码模板（JavaScript 默认模板） | P0 |
| F3.5 | 解析题目约束条件（数据范围、时间复杂度要求等） | P1 |
| F3.6 | 输出结构化 JSON 供后续代码生成使用 | P0 |

### 2.4 代码生成 (Code Generation)
| 编号 | 需求 | 优先级 |
|------|------|--------|
| F4.1 | 基于题目解析结果，调用大模型生成 JavaScript 解法代码 | P0 |
| F4.2 | 生成的代码须符合 LeetCode 函数签名要求 | P0 |
| F4.3 | 支持指定生成策略（暴力解 / 最优解） | P2 |
| F4.4 | 生成代码附带简要注释说明思路 | P1 |

### 2.5 代码提交 (Submission)
| 编号 | 需求 | 优先级 |
|------|------|--------|
| F5.1 | 通过 LeetCode API 提交代码（需携带 CSRF Token） | P0 |
| F5.2 | 提交后获取 submission_id | P0 |
| F5.3 | 轮询判题结果（最多等待 N 秒，可配置） | P0 |

### 2.6 结果处理 (Result Processing)
| 编号 | 需求 | 优先级 |
|------|------|--------|
| F6.1 | 解析判题结果：Accepted / Wrong Answer / TLE / MLE / Runtime Error / Compile Error | P0 |
| F6.2 | 提取运行时间（ms）和内存消耗（MB） | P0 |
| F6.3 | 提取击败百分比 | P1 |
| F6.4 | 若错误，提取错误信息 / 失败用例 | P1 |
| F6.5 | 汇总生成提交报告（CSV/JSON/Markdown） | P0 |

### 2.7 批量处理 (Batch Processing)
| 编号 | 需求 | 优先级 |
|------|------|--------|
| F7.1 | 支持批量处理多道题目 | P1 |
| F7.2 | 批量提交间有可配置的间隔时间（避免限流） | P1 |
| F7.3 | 失败自动重试（可配置次数） | P2 |

---

## 3. 非功能需求

| 编号 | 需求 | 说明 |
|------|------|------|
| NF1 | 请求频率控制 | 最小间隔 2s，避免触发 LeetCode 反爬 |
| NF2 | 异常处理 | 网络超时、API 变更、Token 过期等情况需妥善处理并记录日志 |
| NF3 | 日志记录 | 关键步骤记录日志，便于排查问题 |
| NF4 | 配置化 | Token、请求间隔、超时时间等可配置 |
| NF5 | 幂等性 | 同一题目重复执行不产生副作用 |

---

## 4. 系统架构

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  config.yaml │────▶│   main.py    │────▶│  输出报告     │
│  (Token等)   │     │  (调度中心)   │     │  (CSV/JSON)  │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │  fetcher.py  │ │  solver.py   │ │ submitter.py │
   │  题库获取     │ │  LLM代码生成  │ │  提交+判题    │
   │  题目解析     │ │              │ │              │
   └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                  ┌────────────────┐
                  │  LeetCode API  │
                  │  leetcode.cn   │
                  └────────────────┘
```

### 4.1 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 配置管理 | `config.yaml` / `config.py` | Token、请求参数、LLM 配置等 |
| HTTP 客户端 | `client.py` | 统一请求封装（Header、Cookie、CSRF、重试、限流） |
| 题库获取 | `fetcher.py` | 获取题目列表、单题详情、题目解析 |
| 代码生成 | `solver.py` | 调用 LLM 或模板生成 JavaScript 解法 |
| 提交判题 | `submitter.py` | 提交代码、轮询结果、解析判题响应 |
| 报告输出 | `reporter.py` | 汇总结果，输出 CSV/JSON/Markdown |
| 主调度 | `main.py` | 串联全流程，支持单题/批量模式 |

---

## 5. 核心数据结构

### 5.1 题目数据 (Problem)
```json
{
  "id": "1",
  "frontend_id": "1",
  "title": "Two Sum",
  "title_slug": "two-sum",
  "difficulty": "Easy",
  "tags": ["Array", "Hash Table"],
  "content": "给定一个整数数组 nums 和一个整数目标值 target...",
  "examples": [
    {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "因为 nums[0] + nums[1] == 9"}
  ],
  "constraints": ["2 <= nums.length <= 10^4", "..."],
  "code_template": "/**\n * @param {number[]} nums\n * @param {number} target\n * @return {number[]}\n */\nvar twoSum = function(nums, target) {\n    \n};",
  "function_signature": "var twoSum = function(nums, target)"
}
```

### 5.2 提交结果 (SubmissionResult)
```json
{
  "submission_id": "12345678",
  "problem_id": "1",
  "status": "Accepted",
  "runtime_ms": 68,
  "memory_mb": 42.3,
  "runtime_percentile": 85.2,
  "memory_percentile": 60.1,
  "language": "javascript",
  "code": "var twoSum = function(nums, target) { ... }",
  "error_message": null,
  "failed_testcase": null,
  "timestamp": "2026-06-19T15:30:00+08:00"
}
```

---

## 6. API 接口说明

LeetCode 中文站主要 GraphQL 端点：`https://leetcode.cn/graphql/`

### 6.1 关键 GraphQL 查询

**获取题目列表：**
```graphql
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      frontendQuestionId
      title
      titleSlug
      difficulty
      topicTags { name slug }
    }
  }
}
```

**获取题目详情：**
```graphql
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    topicTags { name slug }
    codeSnippets { lang langSlug code }
    sampleTestCase
    exampleTestcases
  }
}
```

**提交代码：**
```
POST https://leetcode.cn/problems/{titleSlug}/submit/
Headers: { Content-Type: application/json, x-csrftoken: xxx, Cookie: xxx }
Body: { lang: "javascript", question_id: "1", typed_code: "..." }
```

**查询判题结果：**
```
GET https://leetcode.cn/submissions/detail/{submission_id}/check/
```

### 6.2 判题状态枚举

| 状态码 | 含义 |
|--------|------|
| PENDING | 等待判题 |
| STARTED | 判题中 |
| SUCCESS | 判题完成 |
| 10 | Accepted |
| 11 | Wrong Answer |
| 12 | Memory Limit Exceeded |
| 13 | Output Limit Exceeded |
| 14 | Time Limit Exceeded |
| 15 | Runtime Error |
| 20 | Compile Error |
| 21 | Unknown Error |

---

## 7. 执行流程

### 7.1 单题模式
```
1. 读取配置（Token、题目 ID/Slug）
2. 初始化 HTTP 客户端（设置 Cookie、CSRF Token、User-Agent）
3. 获取题目详情（GraphQL API）
4. 解析题目 → Problem 结构体
5. 提取代码模板 → JavaScript 函数签名
6. 调用 LLM 生成解题代码
7. 通过 API 提交代码 → 获取 submission_id
8. 轮询判题结果（最多 30s）
9. 解析结果 → SubmissionResult
10. 输出报告
```

### 7.2 批量模式
```
1. 读取配置（Token、筛选条件）
2. 获取题库列表
3. 按筛选条件过滤
4. for each 题目:
   4.1 等待间隔（避免限流）
   4.2 执行单题流程（步骤 3-9）
   4.3 记录结果到汇总列表
5. 输出批量汇总报告
```

---

## 8. 错误处理

| 场景 | 处理策略 |
|------|----------|
| Token 过期 / 401 | 提示用户重新提供 Token，停止执行 |
| 网络超时 | 重试 3 次，指数退避 |
| 题目不存在 | 跳过并记录警告 |
| 判题超时 | 标记为 Unknown，继续下一题 |
| 限流 429 | 等待 Retry-After 头指定的时间后重试 |
| LLM 生成失败 | 重试 LLM 调用，最多 2 次 |
| 编译错误 | 记录错误信息，可选自动修复重试 |

---

## 9. 配置文件示例

```yaml
# config.yaml
leetcode:
  base_url: "https://leetcode.cn"
  graphql_url: "https://leetcode.cn/graphql/"
  
auth:
  cookie: "LEETCODE_SESSION=xxx; csrftoken=xxx"
  
request:
  timeout_seconds: 30
  interval_seconds: 3      # 请求间隔
  max_retries: 3
  
llm:
  provider: "openai"       # openai / deepseek / local
  model: "deepseek-chat"
  api_key: "${LLM_API_KEY}"
  temperature: 0.1

batch:
  difficulty_filter: []    # ["Easy", "Medium", "Hard"] 为空则全部
  tag_filter: []           # ["Array", "Dynamic Programming"]
  max_problems: 10         # 单次最多处理数量
  start_from_id: 1         # 起始题号

output:
  format: "csv"            # csv / json / markdown
  directory: "./output"
```

---

## 10. 输出报告格式

### 10.1 CSV 输出
| 题号 | 标题 | 难度 | 标签 | 状态 | 耗时(ms) | 内存(MB) | 击败% | 错误信息 |
|------|------|------|------|------|----------|----------|-------|----------|
| 1 | Two Sum | Easy | Array,Hash | Accepted | 68 | 42.3 | 85.2 | — |
| 2 | Add Two Numbers | Medium | Linked List | WA | — | — | — | Output mismatch |

### 10.2 Markdown 总结
- 总题数 / 通过数 / 通过率
- 按难度分布统计
- 错误题目汇总及原因分析

---

## 11. 开发里程碑

| 阶段 | 内容 | 预计产出 |
|------|------|----------|
| Phase 1 | 认证 + 题目获取 + 解析 | `fetcher.py` 可独立运行 |
| Phase 2 | 代码提交 + 判题轮询 | `submitter.py` 可独立运行 |
| Phase 3 | LLM 代码生成 | `solver.py` |
| Phase 4 | 全流程串联 | `main.py` 单题模式 |
| Phase 5 | 批量处理 + 报告 | `main.py` 批量模式 |
| Phase 6 | 配置化 + 日志 + 异常处理 | 完整工具 |
