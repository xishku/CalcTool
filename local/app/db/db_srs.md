# SQLite 数据库访问接口 (DB Access Layer)

## 1. 项目概述

### 1.1 背景

本机已安装 SQLite，项目内多个子模块（leetcode 刷题数据、财经爬虫、benchmark 结果、股票筛选记录等）均需要本地持久化存储。目前各模块各自为政（文件存储、内存缓存等），缺乏统一的数据库访问层。本模块封装一个轻量、通用、可复用的 SQLite 访问接口，供所有 Python 子项目共用。

### 1.2 目标

- 建立统一的 SQLite 数据库访问接口（Python SDK）
- 支持多数据库实例（各子模块独立 `.db` 文件）
- 提供简洁的 CRUD 封装，减少样板代码
- 支持 schema 迁移（DDL 版本管理）
- 遵循项目现有的 YAML 配置 + logging 模式

### 1.3 范围

| 包含 | 排除 |
|------|------|
| SQLite 连接管理 | 多线程并发写入（SQLite 单写锁限制） |
| 表创建 / schema 迁移 | 复杂 ORM（如 SQLAlchemy） |
| CRUD 基础操作封装 | 跨网络数据库（MySQL/PostgreSQL 等） |
| 查询结果 dict 化 | 异步 I/O |
| 事务支持 | 内存数据库共享 |

---

## 2. 功能需求

### F01 - 连接管理

| 属性 | 描述 |
|------|------|
| **描述** | 提供上下文管理器自动打开/关闭连接，支持指定数据库文件路径 |
| **输入** | db_path（.db 文件路径，默认 `./data.db`） |
| **输出** | `sqlite3.Connection` 对象 |
| **异常** | 路径不存在时自动创建父目录；连接失败抛出 `DBConnectionError` |

**使用示例**：
```python
with DB.open("data/leetcode.db") as conn:
    rows = conn.fetchall("SELECT * FROM submissions WHERE status = ?", ("Accepted",))
```

### F02 - 数据库实例管理

| 属性 | 描述 |
|------|------|
| **描述** | 通过配置文件集中管理各子模块的数据库路径，一处配置、全局使用 |
| **输入** | YAML 配置文件 `db_config.yaml` |
| **输出** | 按名称获取连接 |

**配置文件示例** (`db_config.yaml`)：
```yaml
databases:
  leetcode:
    path: "data/leetcode.db"
    timeout: 5
  stocks:
    path: "data/stocks.db"
    timeout: 10
  benchmark:
    path: "data/benchmark.db"
  budget:
    path: "../finance/sh/xh/edu/school/data/budget.db"
```

**API**：
```python
db = DB.get("leetcode")
# 等价于 DB.open("data/leetcode.db")
```

### F03 - CRUD 基础操作

提供 `Connection` 子类的便捷方法：

| 方法 | 功能 | 返回值 |
|------|------|--------|
| `fetchone(sql, params)` | 查询单行 | `dict` 或 `None` |
| `fetchall(sql, params)` | 查询多行 | `list[dict]` |
| `execute(sql, params)` | 执行写操作 | `int`（affected rows） |
| `executemany(sql, params_list)` | 批量写入 | `int` |
| `insert(table, data)` | 插入一行 | `int`（lastrowid） |
| `insert_many(table, columns, rows)` | 批量插入 | `int` |
| `update(table, data, where, where_params)` | 更新 | `int` |
| `delete(table, where, where_params)` | 删除 | `int` |

所有查询结果自动转为 `dict`（key 为列名），避免索引依赖。

### F04 - Schema 迁移

| 属性 | 描述 |
|------|------|
| **描述** | 支持版本化的 DDL 迁移，首次运行时自动创建表，升级时按版本号增量执行 |

**迁移文件结构**（每个数据库目录下）：
```
data/
├── leetcode.db
├── leetcode_migrations/
│   ├── 001_init.sql
│   ├── 002_add_difficulty_column.sql
│   └── 003_add_companies_table.sql
```

**API**：
```python
with DB.open("data/leetcode.db", migrations="data/leetcode_migrations") as conn:
    ...
```

**版本管理**：在数据库内维护 `_schema_version` 表，记录当前已执行的迁移版本号。

### F05 - 事务支持

| 属性 | 描述 |
|------|------|
| **描述** | 支持 commit / rollback，错误自动回滚 |

```python
with DB.open("data/stocks.db") as conn:
    with conn.transaction():
        conn.insert("watchlist", {"code": "000001", "date": "2026-01-01"})
        conn.insert("notes", {"stock_id": 1, "note": "关注"})
    # 异常时自动 rollback，成功自动 commit
```

### F06 - 日志集成

遵循项目现有 logging 模式（`CalcTool/sdk/logger.py`），记录以下日志：

| 级别 | 内容 |
|------|------|
| DEBUG | SQL 语句及参数（生产环境可关闭） |
| INFO | 数据库打开/关闭、迁移执行 |
| WARNING | 慢查询（> 1s） |
| ERROR | SQL 执行失败、连接异常 |

### F07 - 导出工具

| 属性 | 描述 |
|------|------|
| **描述** | 提供查询结果导出为 CSV / JSON / DataFrame 的辅助方法 |
| **优先级** | P2（次要） |

```python
with DB.open("data/leetcode.db") as conn:
    rows = conn.fetchall("SELECT * FROM submissions WHERE status = 'Accepted'")
    DB.export_csv(rows, "output/accepted_submissions.csv")
    DB.export_json(rows, "output/accepted_submissions.json")
```

---

## 3. 架构设计

### 3.1 模块结构

```
local/app/db/
├── db_srs.md              # 本文档
├── db_config.yaml          # 数据库配置文件
├── src/
│   └── dbutil/
│       ├── __init__.py     # 公开 API（DB, open, export_*)
│       ├── connection.py   # Connection 类（封装 sqlite3.Connection）
│       ├── manager.py      # DBManager（配置加载、多库管理）
│       ├── migrate.py      # Schema 迁移引擎
│       └── exceptions.py   # 自定义异常类
├── test/
│   ├── test_connection.py
│   ├── test_crud.py
│   ├── test_migrate.py
│   └── test_manager.py
└── examples/
    └── basic_usage.py      # 快速上手指南
```

### 3.2 类图

```
DBManager (单例)
├── _load_config()        # 加载 db_config.yaml
├── get(name)             # 按名称获取 Connection
└── open(path, **kwargs)  # 直接按路径打开

Connection (继承/包装 sqlite3.Connection)
├── fetchone(sql, params) → dict | None
├── fetchall(sql, params) → list[dict]
├── execute(sql, params) → int
├── insert(table, data) → int
├── update(table, data, where, params) → int
├── delete(table, where, params) → int
├── transaction()          # 上下文管理器
└── close()

MigrationEngine
├── _ensure_version_table()
├── apply(conn, migrations_dir)
└── _get_applied_versions() → set[int]
```

### 3.3 数据流

```
配置文件 ──→ DBManager.load() ──→ 缓存连接工厂
                                      │
子模块调用 DB.get("leetcode") ──────→ Connection 对象
                                      │
                 ┌────────────────────┘
                 ▼
        MigrationEngine.apply()  // 首次自动迁移
                 │
                 ▼
        业务代码执行 CRUD ──→ sqlite3 原生调用 ──→ .db 文件
```

---

## 4. 接口定义（API Reference）

### 4.1 `DB` 命名空间（统一入口）

```python
from dbutil import DB

# 按配置名称打开
conn = DB.get("leetcode")

# 直接按路径打开
conn = DB.open("data/mydb.db", timeout=10)

# 带迁移
conn = DB.open("data/mydb.db", migrations="data/mydb_migrations")

# 导出
DB.export_csv(rows, "output.csv")
DB.export_json(rows, "output.json")
```

### 4.2 `Connection` 类

```python
class Connection:
    def __init__(self, db_path: str, timeout: int = 5, 
                 migrations: str | None = None): ...

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None: ...
    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]: ...
    def execute(self, sql: str, params: tuple = ()) -> int: ...
    def executemany(self, sql: str, params_list: list[tuple]) -> int: ...

    def insert(self, table: str, data: dict) -> int: ...
    def insert_many(self, table: str, columns: list[str], rows: list[list]) -> int: ...
    def update(self, table: str, data: dict, where: str, params: tuple = ()) -> int: ...
    def delete(self, table: str, where: str, params: tuple = ()) -> int: ...

    def transaction(self) -> TransactionContext: ...
    def close(self): ...
    def __enter__(self): ...
    def __exit__(self, ...): ...

    # 属性
    @property
    def raw(self) -> sqlite3.Connection: ...   # 获取原生连接（高级用法）
    @property
    def path(self) -> str: ...
```

### 4.3 异常类

```python
class DBError(Exception): ...
class DBConnectionError(DBError): ...
class DBQueryError(DBError): ...
class DBMigrationError(DBError): ...
```

---

## 5. 非功能需求

| 类别 | 要求 |
|------|------|
| **性能** | 单条查询封装开销 < 1%（相比原生 sqlite3） |
| **可靠性** | 写操作异常自动 rollback，不残留脏数据 |
| **可维护性** | 100% type hints，pytest 覆盖率 ≥ 80% |
| **兼容性** | Python 3.10+，仅依赖标准库 `sqlite3` |
| **零依赖** | 不引入第三方 ORM/数据库驱动 |
| **日志** | 遵循项目 `CalcTool.sdk.logger` 规范 |

---

## 6. 与子项目的集成场景

| 子项目 | 数据库 | 典型表 |
|--------|--------|--------|
| `leetcode/` | `leetcode.db` | submissions, problems, companies |
| `filter/` | `stocks.db` | watchlist, observations, kline_cache |
| `finance/.../school/` | `budget.db` | budgets, institutions, categories |
| `benchmark/` | `benchmark.db` | runs, results, versions |
| `dsp_codebuddy/` | `observations.db` | observation_points, screenshots |

---

## 7. 开发计划

| 阶段 | 内容 | 预计产出 |
|------|------|----------|
| Phase 1 | Connection + 基础 CRUD + 异常 + 单元测试 | `connection.py`, `exceptions.py` |
| Phase 2 | DBManager + YAML 配置 + 多实例管理 | `manager.py`, `db_config.yaml` |
| Phase 3 | Migration Engine + 版本管理 | `migrate.py` |
| Phase 4 | 事务支持 + 导出工具 | `transaction()`, `export_*` |
| Phase 5 | 日志集成 + 性能优化 | logging hook |

---

## 8. 验收标准

- [ ] `DB.open(path)` 可以打开/创建数据库，自动创建目录
- [ ] `conn.fetchall(sql, params)` 返回 `list[dict]`，列名作为 key
- [ ] `conn.insert(table, data)` 返回 lastrowid
- [ ] `conn.transaction()` 异常时自动回滚
- [ ] `DB.get("leetcode")` 按配置名称获取连接
- [ ] migration 目录下的 SQL 文件按版本号依次执行
- [ ] 所有公共方法有 type hints 和 docstring
- [ ] pytest 覆盖率 ≥ 80%
