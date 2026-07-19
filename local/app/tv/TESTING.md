# TV App - 单元测试本地运行说明

## 前置要求
- JDK 17+
- Android SDK (API 34+)
- Gradle 8.5+

## 运行测试

```bash
# 在项目目录下
cd CalcTool/local/app/tv

# 运行所有单元测试 (JVM, 不需要模拟器)
./gradlew test

# 查看测试报告
# app/build/reports/tests/testDebugUnitTest/index.html
```

## CI 自动运行

Push/PR 到仓库后，GitHub Actions 自动运行 `.github/workflows/tv-test.yml`，包含：
- **unit-test**: JVM 单元测试（API 24 + 34）
- **lint**: Android Lint + Detekt 代码检查
