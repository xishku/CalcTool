import time
import pyautogui
import pygetwindow as gw
import subprocess
import os
from typing import Optional

class THSController:
    def __init__(self):
        # 安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        self.ths_title_keywords = ["同花顺"]
        
    def find_ths_window(self) -> Optional[gw.Window]:
        """查找同花顺窗口"""
        try:
            for window in gw.getAllWindows():
                if window.title:
                    for keyword in self.ths_title_keywords:
                        if keyword in window.title:
                            print(f"找到窗口: {window.title}")
                            return window
            print("未找到同花顺窗口")
            return None
        except Exception as e:
            print(f"查找窗口出错: {e}")
            return None
    
    def launch_ths(self, ths_path: str = None):
        """启动同花顺"""
        if ths_path is None:
            default_paths = [
                r"C:\同花顺\xiadan.exe",
                r"C:\同花顺软件\hexin.exe",
                r"C:\Program Files\同花顺\hexin.exe",
                r"C:\ths\hexin.exe"
            ]
            
            for path in default_paths:
                if os.path.exists(path):
                    ths_path = path
                    break
        
        if ths_path and os.path.exists(ths_path):
            print(f"启动同花顺: {ths_path}")
            subprocess.Popen(ths_path)
            time.sleep(8)
            return True
        else:
            print("未找到同花顺程序，请手动启动")
            return False
    
    def activate_window(self, window: gw.Window):
        """激活并前置窗口"""
        try:
            if window.isMinimized:
                window.restore()
            window.activate()
            time.sleep(1)
            
            # 点击窗口中心位置，确保焦点在K线图区域
            center_x = window.left + window.width // 2
            center_y = window.top + window.height // 2
            pyautogui.click(center_x, center_y)
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False
    
    def ensure_kline_focus(self, window: gw.Window):
        """确保焦点在K线图区域"""
        # 点击K线图区域（通常位于窗口中间偏右下方）
        kline_x = window.left + window.width * 3 // 4
        kline_y = window.top + window.height * 2 // 3
        pyautogui.click(kline_x, kline_y)
        time.sleep(0.3)
        
        # 按Esc确保退出任何输入状态
        pyautogui.press('esc')
        time.sleep(0.2)
        
        # 按空格键（同花顺中空格键可以切换光标状态）
        pyautogui.press('space')
        time.sleep(0.2)
        
        # 再按一次空格键切换回来
        pyautogui.press('space')
        time.sleep(0.2)
        
        print("已确保焦点在K线图区域")
    
    def input_stock_code(self, code: str):
        """输入股票代码"""
        print(f"输入股票代码: {code}")
        
        # 按F6切换到代码输入（同花顺标准快捷键）
        pyautogui.press('f6')
        time.sleep(0.5)
        
        # 清空输入框
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        pyautogui.press('delete')
        time.sleep(0.1)
        
        # 输入代码
        pyautogui.typewrite(code)
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(2)  # 等待K线图加载
        
        # 再次按回车确认
        pyautogui.press('enter')
        time.sleep(1)
    
    def switch_to_daily_kline(self):
        """切换到日K线图"""
        print("切换到日K线图...")
        
        # 先按Esc取消任何可能的光标
        pyautogui.press('esc')
        time.sleep(0.2)
        
        # 按F5切换K线周期
        pyautogui.press('f5')
        time.sleep(0.5)
        
        # 如果不在日K线，按F5或数字键5
        pyautogui.typewrite('5')  # 5通常是日K线
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(1)
        
        # 再按一次F5确保
        pyautogui.press('f5')
        time.sleep(1)
        
        print("日K线图已就绪")
    
    def navigate_to_specific_date(self, target_date: str = "2026-03-12"):
        """精确定位到具体日期"""
        print(f"导航到日期: {target_date}")
        
        # 方法1：使用日期输入功能
        print("方法1: 使用日期输入功能")
        
        # 先按Esc确保在K线模式
        pyautogui.press('esc')
        time.sleep(0.2)
        
        # 尝试不同的日期输入快捷键
        date_shortcuts = ['.', '/', '\\']
        for shortcut in date_shortcuts:
            try:
                pyautogui.press(shortcut)
                time.sleep(0.5)
                
                # 检查是否弹出日期输入框
                # 输入日期 (同花顺格式可能是: 20260312 或 2026-03-12)
                pyautogui.typewrite("20260312")
                time.sleep(0.3)
                pyautogui.press('enter')
                time.sleep(1)
                
                # 再按一次回车确认
                pyautogui.press('enter')
                time.sleep(1)
                
                print(f"使用快捷键 '{shortcut}' 输入日期")
                break
                
            except Exception as e:
                print(f"快捷键 '{shortcut}' 失败: {e}")
                pyautogui.press('esc')
                time.sleep(0.2)
        
        # 方法2：如果日期输入失败，使用方向键导航
        time.sleep(2)
        print("方法2: 使用方向键导航")
        
        # 先按Esc确保焦点
        pyautogui.press('esc')
        time.sleep(0.2)
        
        # 按↓键缩小时间范围（更容易导航到特定日期）
        print("缩小时间范围...")
        for i in range(6):
            pyautogui.press('down')
            time.sleep(0.1)
        
        time.sleep(0.5)
        
        # 向左移动到3月12日（今天3月31日，向左大约15-20个交易日）
        print("向左移动到目标日期...")
        for i in range(20):  # 增加尝试次数
            pyautogui.press('left')
            time.sleep(0.1)
            
            # 每移动几次，按一次空格查看日期
            if i % 5 == 0:
                pyautogui.press('space')
                time.sleep(0.3)
                pyautogui.press('space')
                time.sleep(0.3)
        
        # 方法3：使用Home键回到最早，再按→键导航
        time.sleep(1)
        print("方法3: 从最早日期开始导航")
        pyautogui.press('home')  # 回到K线图最早日期
        time.sleep(1)
        
        # 按→键向右移动到3月12日附近
        for i in range(150):  # 大量按→键
            pyautogui.press('right')
            if i % 20 == 0:
                time.sleep(0.1)
        
        time.sleep(1)
    
    def take_screenshot(self, filename: str = "kline_screenshot.png"):
        """截图确认结果"""
        time.sleep(2)
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        print(f"已保存截图: {filename}")
        return filename
    
    def run(self, stock_code: str = "601398", target_date: str = "2026-03-12"):
        """主执行函数"""
        print("=" * 60)
        print("同花顺自动化控制脚本 - 增强版")
        print(f"目标: {stock_code} 在 {target_date} 的日K线")
        print("今天是2026年3月31日，目标日期是过去日期")
        print("=" * 60)
        
        # 步骤1：查找或启动同花顺
        window = self.find_ths_window()
        if not window:
            print("未找到已打开的窗口，请手动打开同花顺")
            return False
        
        # 步骤2：激活窗口
        print("激活同花顺窗口...")
        if not self.activate_window(window):
            return False
        
        # 步骤3：确保焦点在K线图区域
        self.ensure_kline_focus(window)
        time.sleep(1)
        
        # 步骤4：输入股票代码
        self.input_stock_code(stock_code)
        time.sleep(2)
        
        # 步骤5：切换到日K线
        self.switch_to_daily_kline()
        time.sleep(1)
        
        # 步骤6：确保焦点再次在K线图
        self.ensure_kline_focus(window)
        time.sleep(0.5)
        
        # 步骤7：导航到目标日期
        self.navigate_to_specific_date(target_date)
        
        # 步骤8：最终确认和截图
        screenshot_file = self.take_screenshot(f"{stock_code}_{target_date}_kline.png")
        
        print("=" * 60)
        print("自动化操作完成!")
        print(f"截图已保存: {screenshot_file}")
        print("提示: 如果日期不准确，可以:")
        print("1. 手动按左右方向键微调")
        print("2. 按 '.' 或 '/' 键输入精确日期")
        print("3. 按空格键查看光标所在位置的日期")
        print("=" * 60)
        
        return True

def debug_window_info():
    """调试函数：查看所有窗口信息"""
    print("当前所有窗口:")
    print("-" * 50)
    for i, window in enumerate(gw.getAllWindows()):
        if window.title:
            print(f"{i}: {window.title[:50]}...")
    print("-" * 50)

def manual_test():
    """手动测试模式"""
    print("进入手动测试模式")
    print("请先手动打开同花顺，并确保它在前台")
    input("按Enter键继续...")
    
    # 记录当前鼠标位置
    print("移动鼠标到同花顺窗口，5秒后记录位置...")
    time.sleep(5)
    x, y = pyautogui.position()
    print(f"鼠标位置: ({x}, {y})")
    
    # 获取当前活动窗口
    active_window = gw.getActiveWindow()
    if active_window:
        print(f"活动窗口: {active_window.title}")
    else:
        print("无活动窗口")
    
    # 测试快捷键
    print("测试快捷键...")
    shortcuts = ['F6', 'F5', '.', '/', 'space', 'left', 'right', 'down', 'home']
    
    for key in shortcuts:
        print(f"按 {key} 键，3秒后继续...")
        time.sleep(3)
        pyautogui.press(key.lower())
        time.sleep(1)

if __name__ == "__main__":
    # 调试：查看窗口信息
    debug_window_info()
    
    # 运行自动化脚本
    controller = THSController()
    
    # 尝试自动化
    success = controller.run(stock_code="601398", target_date="2026-03-12")
    
    if not success:
        print("\n自动化可能失败，请尝试:")
        print("1. 手动打开同花顺")
        print("2. 手动输入601398并回车")
        print("3. 按F5确保在日K线")
        print("4. 在K线图区域点击鼠标")
        print("5. 按'.'键输入20260312并回车")
        
        # 或者进入手动测试模式
        choice = input("\n是否进入手动测试模式? (y/n): ")
        if choice.lower() == 'y':
            manual_test()