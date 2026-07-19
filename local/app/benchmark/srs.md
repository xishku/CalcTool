# 编程语言算法性能基准测试 — 软件需求规格说明书 (SRS)

## 1. 项目概述

### 1.1 项目名称
多语言算法性能基准测试工具 (Language Algorithm Benchmark Tool)

### 1.2 项目目标
分别使用 **C、C++、Python、Java** 四种主流语言实现若干典型算法，系统性地测量并对比各语言在相同算法上的运行速度差异，输出量化的基准测试报告。

### 1.3 使用场景
- 开发者评估不同语言在 CPU 密集型计算任务上的性能表现
- 语言选型时的性能参考
- 学习算法在不同语言中实现差异的教学素材

### 1.4 范围约定
- **包含**：纯计算密集型算法（排序、矩阵运算、数值计算等）
- **排除**：I/O 密集型任务、网络请求、多线程并发（本次聚焦单核性能对比）、GPU 加速
- **排除**：内存分配开销的精细测量（仅记录粗粒度内存峰值）
- **约束**：所有算法均为自实现，不得依赖第三方库（如 OpenSSL、NumPy 等）。哈希算法使用 FNV-1a，各语言从零编码，确保公平对比。

---

## 2. 被测算法定义

### 2.1 算法清单

| 编号 | 算法名称 | 类型 | 时间复杂度 | 说明 |
|------|---------|------|-----------|------|
| A01 | 冒泡排序 | 排序 | O(n²) | 小数据量对比基准 |
| A02 | 快速排序 | 排序 | O(n log n) | 递归实现，通用排序算法代表 |
| A03 | 矩阵乘法 | 数值计算 | O(n³) | 三重循环，CPU 密集型典型 |
| A04 | 斐波那契数列 | 递归/迭代 | O(2ⁿ) / O(n) | 对比递归与迭代的性能差异 |
| A05 | 质数筛选（埃拉托色尼筛法） | 数学 | O(n log log n) | 循环与数组访问密集型 |
| A06 | FNV-1a 哈希计算 | 哈希 | O(n) | FNV-1a 64-bit，纯算术实现，零外部依赖 |
| A07 | 字符串查找 (KMP) | 字符串 | O(n+m) | 字符串处理能力对比 |

### 2.2 数据集规格

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 排序数组大小 | 100,000 | 随机整数数组 |
| 矩阵维度 | 500×500 | 方阵，元素为 double |
| 斐波那契项数 | 40 | 递归模式下不宜过大 |
| 质数上限 | 10,000,000 | 筛法上限 |
| 哈希数据量 | 10 MB | 随机字节流 |
| 字符串文本长度 | 1,000,000 | 随机 ASCII 字符串，模式串长 100 |

---

## 3. 功能需求

| 编号 | 需求 | 优先级 |
|------|------|--------|
| F01 | 每种语言独立实现全部 7 个算法（或说明不可实现原因） | P0 |
| F02 | 测量每个算法的执行时间（毫秒精度） | P0 |
| F03 | 测量每个程序的峰值内存占用（可选） | P1 |
| F04 | 每个算法至少运行 5 次取平均值和标准差 | P0 |
| F05 | 输出结构化结果报告（JSON 格式） | P0 |
| F06 | 自动编译并运行所有语言的程序 | P1 |
| F07 | 支持通过配置文件调整数据集参数 | P1 |
| F08 | 支持预热（warm-up）阶段，排除 JIT/JVM 冷启动影响 | P1 |

---

## 4. 非功能需求

| 编号 | 需求 | 说明 |
|------|------|------|
| NF01 | 单核运行 | 所有算法绑定到同一 CPU 核心，减少调度干扰 |
| NF02 | 环境一致性 | 同一台机器、相同 OS、关闭其他重负载进程 |
| NF03 | 公平对比 | 不同语言的实现算法逻辑一致，不针对特定语言优化 |
| NF04 | 可复现 | 记录编译器版本、运行时版本、优化参数等环境信息 |
| NF05 | 结果可读 | 输出汇总对比表格 |

---

## 5. 各语言实现规范

### 5.1 C 语言

| 项目 | 规范 |
|------|------|
| 标准 | C99 / C11 |
| 编译器 | GCC ≥ 9.0 或 Clang ≥ 14.0 |
| 编译参数 | `-O2 -march=native` |
| 时间测量 | `clock_gettime(CLOCK_MONOTONIC, ...)` |
| 内存测量 | `getrusage()` 或平台相关 API |

### 5.2 C++ 语言

| 项目 | 规范 |
|------|------|
| 标准 | C++17 |
| 编译器 | GCC ≥ 9.0 或 Clang ≥ 14.0 |
| 编译参数 | `-O2 -march=native -std=c++17` |
| 时间测量 | `std::chrono::high_resolution_clock` |
| 内存测量 | 平台相关 API 或 `/proc/self/status`（Linux） |
| 注意 | 不针对 STL 做特殊优化，尽量手写数据结构保持与 C 版本可比 |

### 5.3 Python 语言

| 项目 | 规范 |
|------|------|
| 版本 | CPython 3.11+ |
| 时间测量 | `time.perf_counter_ns()` |
| 内存测量 | `tracemalloc` 模块 |
| 注意 | 必要时使用 `__slots__` 减少内存开销（记录但不强制） |
| 注意 | 排除 NumPy 等 C 扩展库（保持纯 Python） |

### 5.4 Java 语言

| 项目 | 规范 |
|------|------|
| 版本 | JDK 17+ |
| JVM 参数 | `-Xms512m -Xmx2g` |
| 时间测量 | `System.nanoTime()` |
| 内存测量 | `Runtime.getRuntime().totalMemory() - freeMemory()` |
| 注意 | 每个算法运行前执行 2 次预热，排除 JIT 编译影响 |

---

## 6. 项目目录结构

```
benchmark/
├── srs.md                  # 本文档
├── run.sh                  # 一键运行脚本 (Linux/Mac)
├── run.bat                 # 一键运行脚本 (Windows)
├── config.yaml             # 全局配置文件
├── src/
│   ├── c/
│   │   ├── Makefile
│   │   ├── sort_bubble.c
│   │   ├── sort_quick.c
│   │   ├── matrix_multiply.c
│   │   ├── fibonacci.c
│   │   ├── prime_sieve.c
│   │   ├── hash_fnv1a.c
│   │   └── str_kmp.c
│   ├── cpp/
│   │   ├── Makefile
│   │   ├── sort_bubble.cpp
│   │   ├── sort_quick.cpp
│   │   ├── matrix_multiply.cpp
│   │   ├── fibonacci.cpp
│   │   ├── prime_sieve.cpp
│   │   ├── hash_fnv1a.cpp
│   │   └── str_kmp.cpp
│   ├── python/
│   │   ├── benchmark.py     # 主入口
│   │   ├── sort_bubble.py
│   │   ├── sort_quick.py
│   │   ├── matrix_multiply.py
│   │   ├── fibonacci.py
│   │   ├── prime_sieve.py
│   │   ├── hash_fnv1a.py
│   │   └── str_kmp.py
│   └── java/
│       ├── build.gradle
│       ├── src/main/java/benchmark/
│       │   ├── Benchmark.java         # 主入口
│       │   ├── SortBubble.java
│       │   ├── SortQuick.java
│       │   ├── MatrixMultiply.java
│       │   ├── Fibonacci.java
│       │   ├── PrimeSieve.java
│       │   ├── HashFNV1a.java
│       │   └── StrKMP.java
│       └── ...
└── results/
    └── report_YYYYMMDD_HHMMSS.json    # 输出结果
```

---

## 7. 输出报告格式

### 7.1 JSON 报告结构

```json
{
  "meta": {
    "timestamp": "2026-07-07T16:00:00+08:00",
    "machine": {
      "cpu": "Intel i7-12700H",
      "cores": 14,
      "ram_gb": 32,
      "os": "Windows 11 / Ubuntu 22.04",
      "bound_core": 0
    },
    "environments": {
      "c": { "compiler": "GCC 13.2.0", "flags": "-O2 -march=native" },
      "cpp": { "compiler": "GCC 13.2.0", "flags": "-O2 -march=native -std=c++17" },
      "python": { "version": "CPython 3.11.9" },
      "java": { "version": "JDK 21.0.1", "vm_args": "-Xms512m -Xmx2g" }
    },
    "config": {
      "runs_per_test": 5,
      "warmup_runs": 2,
      "array_size": 100000,
      "matrix_dimension": 500,
      "fibonacci_n": 40,
      "prime_limit": 10000000,
      "hash_data_mb": 10,
      "string_length": 1000000,
      "pattern_length": 100
    }
  },
  "results": [
    {
      "algorithm": "quick_sort",
      "language": "python",
      "runs": [125.3, 123.1, 126.8, 124.5, 122.9],
      "mean_ms": 124.52,
      "stddev_ms": 1.43,
      "peak_memory_mb": 15.2,
      "unit": "ms"
    }
  ],
  "summary": {
    "quick_sort": {
      "c": { "mean_ms": 2.1, "relative": 1.0 },
      "cpp": { "mean_ms": 2.3, "relative": 1.1 },
      "java": { "mean_ms": 5.8, "relative": 2.76 },
      "python": { "mean_ms": 124.5, "relative": 59.3 }
    }
  }
}
```

### 7.2 汇总对比表（控制台输出）

```
==================== Benchmark Summary ====================
Algorithm      | C (ms) | C++ (ms) | Java (ms) | Python (ms)
-----------------------------------------------------------
bubble_sort    |    xxx |      xxx |       xxx |        xxx
quick_sort     |    xxx |      xxx |       xxx |        xxx
matrix_multiply|    xxx |      xxx |       xxx |        xxx
fibonacci_iter |    xxx |      xxx |       xxx |        xxx
fibonacci_rec  |    xxx |      xxx |       xxx |        xxx
prime_sieve    |    xxx |      xxx |       xxx |        xxx
hash_fnv1a     |    xxx |      xxx |       xxx |        xxx
str_kmp        |    xxx |      xxx |       xxx |        xxx
===========================================================
* C as baseline (relative = 1.0)
```

---

## 8. 执行流程

```
                                    ┌─────────────────┐
                                    │  读取 config.yaml │
                                    └────────┬────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              ▼              ▼              ▼              ▼
                      ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
                      │ 编译 C    │   │ 编译 C++ │   │ 编译 Java│   │ Python   │
                      │ 程序      │   │ 程序     │   │ 程序     │   │ (跳过)   │
                      └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
                           │              │              │              │
                           └──────────────┼──────────────┘              │
                                          │                             │
                                          ▼                             │
                               ┌─────────────────────┐                  │
                               │ 依次执行 7 个算法    │◄─────────────────┘
                               │ 每个算法 5 次测量    │
                               └──────────┬──────────┘
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │ 汇总结果 → JSON 报告 │
                               └──────────┬──────────┘
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │ 控制台打印对比表      │
                               └─────────────────────┘
```

---

## 9. 配置文件 (config.yaml)

```yaml
# 运行参数
runs_per_test: 5
warmup_runs: 2

# 数据集参数
array_size: 100000
matrix_dimension: 500
fibonacci_n: 40
prime_limit: 10000000
hash_data_mb: 10
string_length: 1000000
pattern_length: 100

# 编译器设置
c_compiler: "gcc"
c_flags: "-O2 -march=native"
cpp_compiler: "g++"
cpp_flags: "-O2 -march=native -std=c++17"
java_home: "/usr/lib/jvm/java-17-openjdk"
java_vm_args: "-Xms512m -Xmx2g"
python_bin: "python3"

# 输出
output_dir: "./results"
```

---

## 10. 错误处理策略

| 场景 | 处理方式 |
|------|---------|
| 编译器未找到 | 跳过该语言的所有测试，报告缺失 |
| 单个程序编译失败 | 跳过该语言该算法，记录错误原因 |
| 运行超时（> 300 秒） | 终止进程，标记为 timeout |
| 内存不足 | 捕获 OOM，标记为该数据规模不可测 |
| 结果文件无法写入 | 回退到控制台输出，提示用户 |

---

## 11. 开发里程碑

| 阶段 | 内容 | 预计工时 |
|------|------|----------|
| M1 | 项目骨架搭建（目录、config、run 脚本） | 0.5h |
| M2 | Python 版全部算法实现 | 2h |
| M3 | C 版全部算法实现 | 2h |
| M4 | C++ 版全部算法实现 | 1.5h |
| M5 | Java 版全部算法实现 | 1.5h |
| M6 | 结果汇总脚本 + JSON 报告生成 | 1h |
| M7 | 一键运行脚本 + 环境检测 | 1h |
| M8 | 测试验证 + 文档完善 | 1h |
| **合计** | | **~10.5h** |

---

## 12. 验收标准

- [ ] 四种语言各 7 个算法程序均可编译/运行
- [ ] `run.sh` 一键执行全部测试，无需手动操作
- [ ] 输出 `results/report_*.json` 符合定义格式
- [ ] 控制台输出清晰的汇总对比表格
- [ ] 同一算法在不同语言间实现逻辑等价
- [ ] 配置文件中修改参数（如数组大小）后测试数据随之变化
- [ ] C 语言基线性能正常（相对于其他语言不异常慢）
