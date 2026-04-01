import time
import pyautogui
import pygetwindow as gw
import subprocess
import os
from typing import Optional

class TDXController:
    def __init__(self):
        # 安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        self.tdx_title_keywords = ["通达信金融终端"]
        
    def find_tdx_window(self) -> Optional[gw.Window]:
        """查找通达信窗口"""
        try:
            for window in gw.getAllWindows():
                if window.title:
                    for keyword in self.tdx_title_keywords:
                        if keyword in window.title:
                            print(f"找到通达信窗口: {window.title}")
                            return window
            print("未找到通达信窗口")
            return None
        except Exception as e:
            print(f"查找窗口出错: {e}")
            return None
    
    def launch_tdx(self, tdx_path: str = None):
        """启动通达信"""
        if tdx_path is None:
            # 通达信常见安装路径
            default_paths = [
                r"d:\new_tdx\TdxW.exe",  # 独立行情版
                r"C:\通达信\TdxW.exe"
            ]
            
            for path in default_paths:
                if os.path.exists(path):
                    tdx_path = path
                    break
        
        if tdx_path and os.path.exists(tdx_path):
            print(f"启动通达信: {tdx_path}")
            subprocess.Popen(tdx_path)
            time.sleep(10)  # 通达信启动较慢
            return True
        else:
            print("未找到通达信程序，请手动启动")
            return False
    
    def activate_window(self, window: gw.Window):
        """激活并前置窗口"""
        try:
            if window.isMinimized:
                window.restore()
            window.activate()
            time.sleep(1)
            
            # 点击窗口中心位置确保焦点
            center_x = window.left + window.width // 2
            center_y = window.top + window.height // 2
            pyautogui.click(center_x, center_y)
            time.sleep(0.5)
            
            # 通达信中按Esc清除可能的状态
            pyautogui.press('esc')
            time.sleep(0.2)
            
            return True
        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False
    
    def input_stock_code(self, code: str):
        """通达信输入股票代码"""
        print(f"输入股票代码: {code}")
        
        # 方法1：直接键盘输入（通达信支持直接输入）
        pyautogui.typewrite(code)
        time.sleep(0.5)
        
        # 按回车确认
        pyautogui.press('enter')
        time.sleep(2)  # 等待K线图加载
        
        # 如果没反应，尝试用快捷键
        pyautogui.press('esc')  # 先取消
        time.sleep(0.2)
        
        # 方法2：使用数字键盘输入
        pyautogui.press('num0')  # 确保在数字状态
        time.sleep(0.1)
        pyautogui.typewrite(code)
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(2)
        
        # 确保在K线图模式
        pyautogui.press('f5')
        time.sleep(1)
    
    def ensure_kline_focus(self, window: gw.Window):
        """确保焦点在K线图区域"""
        # 通达信的K线图通常在主窗口中间偏右
        kline_x = window.left + window.width * 2 // 3
        kline_y = window.top + window.height // 2
        
        # 点击K线图区域
        pyautogui.click(kline_x, kline_y)
        time.sleep(0.3)
        
        # 按空格键激活十字光标
        pyautogui.press('space')
        time.sleep(0.2)
        
        # 再按一次关闭十字光标
        pyautogui.press('space')
        time.sleep(0.2)
        
        print("焦点已设置到K线图区域")
    
    def switch_to_daily_kline(self):
        """切换到日K线图"""
        print("切换到日K线图...")
        
        # 通达信周期切换快捷键
        shortcuts = ['f8', 'f5', '5']
        
        for key in shortcuts:
            try:
                pyautogui.press(key)
                time.sleep(0.5)
                print(f"已按 {key.upper()} 切换周期")
                break
            except:
                continue
        
        # 额外按数字5确保是日K线
        pyautogui.typewrite('5')
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(1)
        
        # 按Esc确保退出菜单
        pyautogui.press('esc')
        time.sleep(0.5)
        
        print("日K线图已就绪")
    
    def navigate_to_specific_date_tdx(self, target_date: str = "2026-03-12"):
        """通达信精确定位到具体日期"""
        print(f"导航到日期: {target_date}")
        
        # 方法1：使用通达信的日期定位功能
        print("方法1: 使用通达信日期定位快捷键")
        
        # 通达信日期定位快捷键通常是 Ctrl+G
        pyautogui.hotkey('ctrl', 'g')
        time.sleep(1)
        
        # 输入日期（通达信格式通常是 2026.03.12 或 20260312）
        date_formats = [
            "20260312",  # 无分隔符
            "2026.03.12",  # 点分隔
            "2026-03-12",  # 横线分隔
            "2026/03/12"   # 斜线分隔
        ]
        
        for date_str in date_formats:
            try:
                pyautogui.typewrite(date_str)
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(2)
                print(f"已输入日期: {date_str}")
                break
            except:
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.press('delete')
                time.sleep(0.2)
                continue
        
        # 方法2：如果Ctrl+G无效，尝试其他方法
        time.sleep(1)
        print("方法2: 尝试其他导航方式")
        
        # 按Home到起始位置
        pyautogui.press('home')
        time.sleep(1)
        
        # 按End到结束位置
        pyautogui.press('end')
        time.sleep(1)
        
        # 通达信使用PageUp/PageDown翻页
        # 2026-03-12是过去日期，用PageUp向上翻
        for _ in range(5):
            pyautogui.press('pageup')
            time.sleep(0.3)
        
        # 方法3：使用方向键
        print("方法3: 使用方向键微调")
        
        # 先按↓缩小显示范围
        for _ in range(3):
            pyautogui.press('down')
            time.sleep(0.1)
        
        time.sleep(0.5)
        
        # 向左移动到目标日期（今天2026-03-31，目标2026-03-12，大约15个交易日）
        for i in range(20):
            pyautogui.press('left')
            if i % 5 == 0:
                time.sleep(0.1)
        
        time.sleep(1)
        
        # 方法4：通达信特殊功能键
        print("方法4: 尝试通达信特殊功能键")
        
        # 按Ctrl+方向键快速移动
        pyautogui.keyDown('ctrl')
        for _ in range(5):
            pyautogui.press('left')
            time.sleep(0.1)
        pyautogui.keyUp('ctrl')
        
        time.sleep(1)
    
    def take_screenshot(self, filename: str = "tdx_kline.png"):
        """截图确认结果"""
        time.sleep(2)
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        print(f"已保存截图: {filename}")
        return filename
    
    def debug_tdx_hotkeys(self):
        """调试通达信快捷键"""
        print("调试通达信快捷键...")
        print("请手动记录哪些快捷键有效")
        
        hotkeys = [
            ('F5', 'K线/分时切换'),
            ('F8', '周期切换'),
            ('Ctrl+G', '日期定位'),
            ('Home', '到起始位置'),
            ('End', '到结束位置'),
            ('PageUp', '上一页'),
            ('PageDown', '下一页'),
            ('Ctrl+左', '向左快速移动'),
            ('Ctrl+右', '向右快速移动'),
            ('空格', '十字光标'),
            ('.', '可能日期输入'),
            ('/', '可能日期输入')
        ]
        
        for key, desc in hotkeys:
            print(f"\n准备测试: {key} - {desc}")
            input("按Enter测试此快捷键...")
            
            if '+' in key:
                keys = key.lower().split('+')
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(key.lower())
            
            time.sleep(1)
    
    def run(self, stock_code: str = "601398", target_date: str = "2026-03-12"):
        """主执行函数"""
        print("=" * 60)
        print("通达信自动化控制脚本")
        print(f"目标: {stock_code} 在 {target_date} 的日K线")
        print("=" * 60)
        
        # 步骤1：查找或启动通达信
        window = self.find_tdx_window()
        if not window:
            print("未找到已打开的窗口，尝试启动...")
            if not self.launch_tdx():
                print("请手动打开通达信后重新运行")
                return False
        
        # 重新查找窗口
        window = self.find_tdx_window()
        if not window:
            print("窗口查找失败")
            return False
        
        # 步骤2：激活窗口
        print("激活通达信窗口...")
        if not self.activate_window(window):
            return False
        
        time.sleep(2)  # 等待通达信完全加载
        
        # 步骤3：输入股票代码
        self.input_stock_code(stock_code)
        time.sleep(2)
        
        # 步骤4：确保焦点在K线图
        self.ensure_kline_focus(window)
        time.sleep(1)
        
        # 步骤5：切换到日K线
        self.switch_to_daily_kline()
        time.sleep(1)
        
        # 步骤6：导航到目标日期
        self.navigate_to_specific_date_tdx(target_date)
        
        # 步骤7：最终确认
        screenshot_file = self.take_screenshot(f"tdx_{stock_code}_{target_date}_kline.png")
        
        print("=" * 60)
        print("自动化操作完成!")
        print(f"截图已保存: {screenshot_file}")
        print("=" * 60)
        
        return True

def debug_all_windows():
    """查看所有窗口信息"""
    print("\n当前所有窗口信息:")
    print("-" * 50)
    for i, window in enumerate(gw.getAllWindows()):
        if window.title and len(window.title) > 3:
            print(f"{i:3}. '{window.title[:60]}'")
    print("-" * 50)

def manual_tdx_test():
    """手动测试通达信"""
    print("\n通达信手动测试模式")
    print("请先手动打开通达信，并确保它在前台")
    input("按Enter键开始测试...")
    
    # 获取活动窗口
    active = gw.getActiveWindow()
    if active:
        print(f"当前活动窗口: {active.title}")
    
    # 测试通达信功能
    print("\n1. 将测试通达信快捷键")
    print("2. 请观察通达信的反应")
    print("3. 记录有效的快捷键")
    
    tests = [
        ("直接输入601398+回车", lambda: (pyautogui.typewrite("601398"), time.sleep(1), pyautogui.press('enter'))),
        ("F5切换K线", lambda: pyautogui.press('f5')),
        ("F8周期切换", lambda: pyautogui.press('f8')),
        ("Ctrl+G日期定位", lambda: pyautogui.hotkey('ctrl', 'g')),
        ("空格十字光标", lambda: pyautogui.press('space')),
        ("Home/End导航", lambda: (pyautogui.press('home'), time.sleep(0.5), pyautogui.press('end'))),
    ]
    
    for desc, test_func in tests:
        print(f"\n测试: {desc}")
        input("按Enter执行...")
        test_func()
        time.sleep(2)
    
    print("\n测试完成!")

if __name__ == "__main__":
    # 调试：查看所有窗口
    debug_all_windows()
    
    # 运行通达信自动化
    controller = TDXController()
    
    # 首先尝试查找窗口
    window = controller.find_tdx_window()
    if not window:
        print("未找到通达信窗口，请手动打开或检查窗口标题")
        print("常见通达信窗口标题包含: 通达信, TDX, 金融终端")
        
        # 显示可能的窗口
        for win in gw.getAllWindows():
            if win.title and len(win.title) > 5:
                print(f"  - {win.title}")
        
        # 尝试修改关键词
        new_keyword = input("\n请输入通达信窗口标题中的关键词: ").strip()
        if new_keyword:
            controller.tdx_title_keywords = [new_keyword]
    
    # 运行自动化
    success = controller.run(stock_code="601398", target_date="2026-03-12")
    
    if not success:
        print("\n自动化可能失败，请尝试以下方法:")
        print("1. 手动打开通达信")
        print("2. 在通达信中直接输入: 601398 回车")
        print("3. 按F5切换到K线图")
        print("4. 按Ctrl+G，输入: 20260312 回车")
        print("5. 或按F8选择'日线'")
        
        choice = input("\n是否进入手动测试模式? (y/n): ")
        if choice.lower() == 'y':
            manual_tdx_test()