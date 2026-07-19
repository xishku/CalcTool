# Tetris C++ (SDL2)

Python 版本的俄罗斯方块用 C++17 + SDL2 重写。

## 快速构建

### Windows (推荐 vcpkg)

```powershell
# 1. 安装 SDL2
vcpkg install sdl2:x64-windows

# 2. 构建
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release
```

### Windows (手动)

```powershell
# 1. 下载 SDL2-devel-2.x.x-VC.zip 解压到 C:\SDL2
# 2. 设置环境变量
$env:SDL2_DIR = "C:/SDL2"

# 3. 构建
mkdir build && cd build
cmake .. -G "Visual Studio 17 2022"
cmake --build . --config Release
```

## 项目结构

```
tetris_cpp/
├── CMakeLists.txt
├── README.md
└── src/
    ├── main.cpp          # 入口
    ├── constants.h       # 常量 (棋盘/颜色/形状/SRS/计分)
    ├── piece.h/cpp       # 方块 (SRS旋转/墙踢/7-Bag)
    ├── board.h/cpp       # 棋盘 (碰撞/消行)
    ├── scorer.h/cpp      # 计分系统
    ├── renderer.h/cpp    # SDL2 渲染 (含内嵌 5x7 像素字体)
    ├── sound.h/cpp       # 程序化音效 (SDL Audio)
    └── game.h/cpp        # 游戏主循环/状态机/输入
```

## 操作

| 按键 | 动作 |
|------|------|
| ← →  | 左右移动 |
| ↓    | 软降 |
| ↑    | 旋转 |
| 空格 | 硬降 |
| P    | 暂停 |
| R    | 重置 |
| ESC  | 退出 |

## 依赖

仅需 **SDL2** (>= 2.0)，无其他外部依赖：

- 音效：纯代码合成方波/三角波，通过 SDL Audio 播放
- 字体：内嵌 5×7 像素点阵字体（A-Z/0-9/符号）
- 无 SDL2_ttf / libsndfile / 额外库需求
