import time
import pyautogui
import win32gui
import win32con

def activate_window(window_title):
    """激活指定标题的窗口"""
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE) # 恢复窗口
        win32gui.SetForegroundWindow(hwnd) # 置顶
        time.sleep(1)
        return True
    else:
        print(f"未找到窗口: {window_title}")
        return False

def open_stock_kline(stock_code, target_date):
    """核心操作函数"""
    # 1. 激活同花顺窗口 (请将“同花顺”改为您窗口的实际标题)
    if not activate_window("同花顺(9.50.31) - 个股资金流向"):
        print("请先打开同花顺软件。")
        return

    time.sleep(0.5)
    # 2. 输入股票代码
    pyautogui.typewrite(stock_code) # 如 "601398"
    pyautogui.press('enter')
    time.sleep(2) # 等待K线图加载

    # 3. 切换到指定日期 (此部分高度依赖软件界面，可能需要OCR或坐标定位，极不稳定)
    # 假设先缩小视图以便更快定位到过去日期
    for _ in range(5): # 按5次下箭头缩小时间范围
        pyautogui.press('down')
        time.sleep(0.1)

    # 然后按左箭头向过去移动 (次数需估算，这里仅为示例)
    for _ in range(50):
        pyautogui.press('left')
        time.sleep(0.05)

    # 注意：自动化点击特定日期的K线极其困难，通常需要图像识别。
    print("自动化操作完成，但精准定位到指定日期可能需要手动微调。")

import win32gui

def get_all_windows():
    """列出所有可见窗口的标题和句柄"""
    windows = []
    
    def enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):  # 只显示可见窗口
            window_title = win32gui.GetWindowText(hwnd)
            if window_title:  # 过滤无标题窗口
                windows.append((hwnd, window_title))
        return True
    
    win32gui.EnumWindows(enum_callback, None)
    return windows



# 使用示例
if __name__ == "__main__":
    # 目标：工商银行(601398) 在 2026-03-12 的K线
    open_stock_kline("601398", "2026-03-12")

    # # 获取并打印所有窗口
    # all_windows = get_all_windows()
    # for hwnd, title in all_windows:
    #     print(f"句柄: {hwnd:10} | 标题: {title}")

    # # 筛选包含特定关键词的窗口
    # print("\n=== 包含'同花顺'的窗口 ===")
    # for hwnd, title in all_windows:
    #     if "同花顺" in title:
    #         print(f"句柄: {hwnd} | 标题: {title}")