#!/usr/bin/env python3
"""
股票K线图查看器启动脚本
"""

import subprocess
import sys
import os

def check_dependencies():
    """检查依赖库是否安装"""
    required_packages = [
        'matplotlib',
        'pandas',
        'numpy',
        'mplfinance',
        'pyautogui',
        'pygetwindow'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """安装缺失的依赖库"""
    if not packages:
        return True
    
    print(f"发现缺失的依赖库: {', '.join(packages)}")
    response = input("是否自动安装？(y/n): ")
    
    if response.lower() in ['y', 'yes']:
        try:
            for package in packages:
                print(f"正在安装 {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            return True
        except Exception as e:
            print(f"安装失败: {e}")
            return False
    else:
        print("请手动安装依赖库:")
        print(f"pip install {' '.join(packages)}")
        return False

def main():
    """主函数"""
    # 检查依赖
    missing_packages = check_dependencies()
    if missing_packages:
        if not install_dependencies(missing_packages):
            print("依赖库安装失败，程序无法启动")
            return
    
    # 运行主程序
    try:
        from main import main as app_main
        app_main()
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()