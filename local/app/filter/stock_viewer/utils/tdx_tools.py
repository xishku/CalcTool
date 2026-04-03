#!/usr/bin/python
#-*-coding:UTF-8-*-

import pyautogui
import pygetwindow as gw
import subprocess
import time
from tkinter import messagebox


class TdxTools:
    """通达信工具类"""
    
    def __init__(self, status_label=None):
        self.status_label = status_label
    
    def find_tdx_window(self):
        """查找通达信窗口"""
        try:
            for window in gw.getAllWindows():
                if window.title:
                    for keyword in ["通达信", "TDX"]:
                        if keyword in window.title:
                            return window
        except Exception as e:
            print(f"查找通达信窗口出错: {e}")
        
        return None
    
    def activate_window(self, window):
        """激活窗口"""
        try:
            window.activate()
            if window.isMinimized:
                window.restore()
            time.sleep(0.5)  # 等待窗口激活
            return True
        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False
    
    def auto_input_tdx_stock(self, stock_code, window):
        """在通达信中自动输入股票代码并定位"""
        try:
            # 等待窗口完全激活
            time.sleep(1)
            
            # 补齐股票代码前面的零，确保是6位
            padded_code = stock_code.zfill(6)
            
            # 方法1：直接键盘输入（通达信支持直接输入）
            pyautogui.typewrite(padded_code)
            time.sleep(0.5)
            
            # 按回车确认
            pyautogui.press('enter')
            time.sleep(2)  # 等待K线图加载
            
            # 确保在K线图模式
            pyautogui.press('f5')
            time.sleep(1)
            
            # 如果没反应，尝试用快捷键
            # pyautogui.press('esc')  # 先取消
            # time.sleep(0.2)
            
            # # 方法2：使用数字键盘输入
            # pyautogui.press('num0')  # 确保在数字状态
            # time.sleep(0.1)
            # pyautogui.typewrite(stock_code)
            # time.sleep(0.5)
            # pyautogui.press('enter')
            # time.sleep(2)
            
            # # 切换到日K线
            # pyautogui.press('f8')
            # time.sleep(0.5)
            # pyautogui.press('5')  # 数字5通常对应日K线
            # time.sleep(1)
            
            # # 确保焦点在K线图区域
            # center_x = window.left + window.width * 2 // 3
            # center_y = window.top + window.height // 2
            # pyautogui.click(center_x, center_y)
            # time.sleep(0.3)
            
            if self.status_label:
                self.status_label.config(
                    text=f"已在通达信中定位到 {padded_code} 的日K线")
            return True
            
        except Exception as e:
            if self.status_label:
                padded_code = stock_code.zfill(6)
                self.status_label.config(
                    text=f"通达信自动化失败，请手动输入 {padded_code}")
            raise Exception(f"通达信自动化失败: {e}")
    
    def launch_tdx_directly(self, stock_code):
        """直接启动通达信程序"""
        try:
            # 通达信常见安装路径
            tdx_paths = [
                r"C:\new_tdx\TdxW.exe",  # 独立行情版
                r"D:\new_tdx\TdxW.exe",  # D盘
                r"E:\new_tdx\TdxW.exe",  # E盘
                r"C:\tdx\TdxW.exe",      # 传统安装
                r"D:\tdx\TdxW.exe",      # D盘传统
                r"C:\通达信\TdxW.exe",    # 标准安装
            ]
            
            for path in tdx_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    time.sleep(5)  # 等待通达信启动
                    return True
            
            return False
            
        except Exception as e:
            raise Exception(f"启动通达信失败: {e}")
    
    def open_tdx(self, stock_code, status_label=None):
        """打开通达信并自动定位到当前股票"""
        if status_label:
            self.status_label = status_label
        
        if not stock_code:
            return False, "请先选择股票"
        
        # 1. 首先尝试查找已打开的窗口
        tdx_window = self.find_tdx_window()
        
        if tdx_window:
            # 通达信已打开，激活窗口
            if self.activate_window(tdx_window):
                if self.status_label:
                    self.status_label.config(
                        text=f"正在通达信中定位 {stock_code} 的日K线...")
                # 在通达信中自动输入股票代码
                try:
                    self.auto_input_tdx_stock(stock_code, tdx_window)
                    return True, f"已在通达信中定位到 {stock_code.zfill(6)} 的日K线"
                except Exception as e:
                    return False, str(e)
            else:
                if self.status_label:
                    self.status_label.config(
                        text="通达信已打开，但无法激活窗口")
                return False, "通达信已打开，但无法激活窗口"
        else:
            # 通达信未打开，启动程序
            try:
                if self.launch_tdx_directly(stock_code):
                    # 尝试查找窗口
                    time.sleep(3)
                    tdx_window = self.find_tdx_window()
                    if tdx_window and self.activate_window(tdx_window):
                        time.sleep(2)
                        self.auto_input_tdx_stock(stock_code, tdx_window)
                        return True, f"已启动并定位到 {stock_code.zfill(6)} 的日K线"
                    else:
                        if self.status_label:
                            self.status_label.config(
                                text=f"已启动通达信，请手动输入 {stock_code}")
                        return False, f"已启动通达信，请手动输入 {stock_code}"
                else:
                    return False, f"未找到通达信程序，请手动打开后输入 {stock_code}"
            except Exception as e:
                return False, str(e)