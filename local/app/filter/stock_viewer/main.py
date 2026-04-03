#!/usr/bin/python
#-*-coding:UTF-8-*-

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from views.main_window import StockKLineViewerGUI
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保项目结构完整，并安装了所有依赖库")
    print("运行: pip install matplotlib pandas numpy mplfinance pyautogui pygetwindow")
    sys.exit(1)


def main():
    """主函数"""
    # 检查是否安装了必要的库
    try:
        import pygetwindow
        print("已安装窗口管理模块: pygetwindow")
    except ImportError:
        print("未安装pygetwindow，将无法检测已打开的窗口")
        print("请运行: pip install pygetwindow")
        return
    
    try:
        import pyautogui
        print("已安装自动化模块: pyautogui")
    except ImportError:
        print("未安装pyautogui，将无法模拟鼠标键盘操作")
        print("请运行: pip install pyautogui")
        return
    
    try:
        import matplotlib
        print("已安装图表库: matplotlib")
    except ImportError:
        print("未安装matplotlib，将无法显示K线图")
        print("请运行: pip install matplotlib")
        return
    
    # 创建并运行GUI应用程序
    app = StockKLineViewerGUI()
    app.run()


if __name__ == '__main__':
    main()