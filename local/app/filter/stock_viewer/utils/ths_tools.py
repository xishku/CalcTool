#!/usr/bin/python
#-*-coding:UTF-8-*-

import pyautogui
import pygetwindow as gw
import subprocess
import time
from tkinter import messagebox


class ThsTools:
    """同花顺工具类"""
    
    def __init__(self, status_label=None):
        self.status_label = status_label
    
    def find_ths_window(self):
        """查找同花顺窗口"""
        try:
            for window in gw.getAllWindows():
                if window.title:
                    for keyword in ["同花顺", "THS", "hexin"]:
                        if keyword in window.title:
                            return window
        except Exception as e:
            print(f"查找同花顺窗口出错: {e}")
        
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
    
    def auto_input_ths_stock(self, stock_code, window):
        """在同花顺中自动输入股票代码并定位 - 简化版本"""
        try:
            # 等待窗口完全激活
            time.sleep(1)
            
            # 补齐股票代码前面的零，确保是6位
            padded_code = stock_code.zfill(6)
            
            # 方法1：直接键盘输入（同花顺支持直接输入）
            pyautogui.typewrite(padded_code)
            time.sleep(0.5)
            
            # 按回车确认
            pyautogui.press('enter')
            time.sleep(2)  # 等待K线图加载
            
            # 确保在K线图模式
            pyautogui.press('f5')
            time.sleep(1)
            
            # # 切换到日K线
            # pyautogui.press('f8')
            # time.sleep(0.5)
            # pyautogui.press('5')  # 数字5通常对应日K线
            # time.sleep(1)
            # pyautogui.press('enter')
            # time.sleep(1)
            
            # # 确保焦点在K线图区域
            # center_x = window.left + window.width * 2 // 3
            # center_y = window.top + window.height // 2
            # pyautogui.click(center_x, center_y)
            # time.sleep(0.3)
            
            # # 同花顺有时需要按空格激活十字光标
            # pyautogui.press('space')
            # time.sleep(0.2)
            # pyautogui.press('space')
            # time.sleep(0.2)
            
            if self.status_label:
                self.status_label.config(
                    text=f"已在同花顺中定位到 {padded_code} 的日K线")
            return True
            
        except Exception as e:
            if self.status_label:
                padded_code = stock_code.zfill(6)
                self.status_label.config(
                    text=f"同花顺自动化失败，请手动输入 {padded_code}")
            raise Exception(f"同花顺自动化失败: {e}")
    
    def launch_ths_directly(self, stock_code):
        """直接启动同花顺程序"""
        try:
            # 同花顺常见安装路径
            ths_paths = [
                r"C:\同花顺软件\同花顺\hexinlauncher.exe",  # 标准安装
                r"D:\同花顺\hexin.exe",  # D盘
                r"C:\Program Files\同花顺\hexin.exe",  # 默认安装
                r"C:\ths\hexin.exe",     # 简化路径
            ]
            
            for path in ths_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    time.sleep(5)  # 等待同花顺启动
                    return True
            
            return False
            
        except Exception as e:
            raise Exception(f"启动同花顺失败: {e}")
    
    def open_ths(self, stock_code, status_label=None):
        """打开同花顺并自动定位到当前股票"""
        if status_label:
            self.status_label = status_label
        
        if not stock_code:
            return False, "请先选择股票"
        
        # 1. 首先尝试查找已打开的窗口
        ths_window = self.find_ths_window()
        
        if ths_window:
            # 同花顺已打开，激活窗口
            if self.activate_window(ths_window):
                padded_code = stock_code.zfill(6)  # 补齐到6位
                if self.status_label:
                    self.status_label.config(
                        text=f"正在同花顺中定位 {padded_code} 的日K线...")
                # 在同花顺中自动输入股票代码
                try:
                    self.auto_input_ths_stock(stock_code, ths_window)
                    return True, f"已在同花顺中定位到 {stock_code.zfill(6)} 的日K线"
                except Exception as e:
                    return False, str(e)
            else:
                if self.status_label:
                    self.status_label.config(
                        text="同花顺已打开，但无法激活窗口")
                return False, "同花顺已打开，但无法激活窗口"
        else:
            # 同花顺未打开，启动程序
            try:
                if self.launch_ths_directly(stock_code):
                    # 尝试查找窗口
                    time.sleep(3)
                    ths_window = self.find_ths_window()
                    if ths_window and self.activate_window(ths_window):
                        time.sleep(2)
                        self.auto_input_ths_stock(stock_code, ths_window)
                        return True, f"已启动并定位到 {stock_code.zfill(6)} 的日K线"
                    else:
                        padded_code = stock_code.zfill(6)
                        if self.status_label:
                            self.status_label.config(
                                text=f"已启动同花顺，请手动输入 {padded_code}")
                        return False, f"已启动同花顺，请手动输入 {padded_code}"
                else:
                    padded_code = stock_code.zfill(6)
                    return False, f"未找到同花顺程序，请手动打开后输入 {padded_code}"
            except Exception as e:
                return False, str(e)