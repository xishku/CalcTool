#!/usr/bin/python
#-*-coding:UTF-8-*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
import sys
import subprocess
import time
import pyautogui
import pygetwindow as gw
from kline_viewer_optimized import KLineViewerOptimized


class StockDataParser:
    """股票数据解析器"""
    
    def __init__(self, file_path=None):
        self.file_path = file_path
        self.data = []
        
    def parse(self, file_path=None):
        """解析文件数据"""
        if file_path:
            self.file_path = file_path
        
        if not self.file_path or not os.path.exists(self.file_path):
            return False, "请选择有效的文件"
            
        try:
            self.data = []
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) < 3:
                        continue
                    
                    timestamp_str = parts[0]
                    stock_code = parts[1]
                    focus_dates = parts[2:]
                    
                    for focus_date in focus_dates:
                        if focus_date:
                            self.data.append({
                                'timestamp': timestamp_str,
                                'stock_code': stock_code,
                                'focus_date': focus_date,
                                'full_data': line
                            })
            
            return True, f"解析完成，共处理 {len(self.data)} 条记录"
            
        except Exception as e:
            return False, f"解析文件时出错: {e}"


class StockKLineViewerGUI:
    """股票K线图查看器GUI"""
    
    def __init__(self):
        self.parser = StockDataParser()
        self.data_records = []
        self.current_file = None
        self.current_kline_viewer = None
        self.current_stock_code = None
        self.current_focus_date = None
        
        # 设置pyautogui安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("股票关注日期查看器")
        self.root.geometry("1400x800")
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置样式
        self.setup_styles()
        
        # 初始化UI
        self.init_ui()
    
    def on_closing(self):
        """关闭主窗口时清理资源"""
        if self.current_kline_viewer:
            try:
                self.current_kline_viewer.close()
            except:
                pass
        self.root.destroy()
        sys.exit(0)
    
    def setup_styles(self):
        """设置UI样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置Treeview样式
        style.configure("Treeview",
                       background="#f0f0f0",
                       foreground="black",
                       rowheight=25,
                       fieldbackground="#f0f0f0")
        
        style.configure("Treeview.Heading",
                       background="#4a6fa5",
                       foreground="white",
                       font=('Arial', 10, 'bold'))
        
        style.map("Treeview",
                 background=[('selected', '#3465a4')],
                 foreground=[('selected', 'white')])
    
    def init_ui(self):
        """初始化用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题和文件选择区域
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, 
                         sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(header_frame, 
                               text="股票关注日期查看器", 
                               font=('Arial', 16, 'bold'),
                               foreground="#2c3e50")
        title_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # 文件选择按钮
        self.file_path_var = tk.StringVar()
        self.file_path_var.set("未选择文件")
        
        file_button_frame = ttk.Frame(header_frame)
        file_button_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        select_file_btn = ttk.Button(file_button_frame, 
                                    text="选择数据文件", 
                                    command=self.select_file)
        select_file_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_label = ttk.Label(file_button_frame, 
                                   textvariable=self.file_path_var,
                                   foreground="#666666")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 左侧控制面板
        left_frame = self.create_left_panel(main_frame)
        
        # 右侧K线图区域
        right_frame = self.create_right_panel(main_frame)
        
        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=2, 
                         sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, 
                                     text="请选择数据文件", 
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)
        
        # 初始化统计文本
        self.update_stats_text("等待加载数据...")
    
    def create_left_panel(self, parent):
        """创建左侧面板"""
        left_frame = ttk.LabelFrame(parent, text="数据和控制面板", 
                                   padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), 
                       padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)
        
        # 文件信息
        info_frame = ttk.Frame(left_frame)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), 
                       pady=(0, 10))
        
        ttk.Label(info_frame, text="当前文件:", 
                 font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        self.file_info_label = ttk.Label(info_frame, 
                                        text="未加载文件", 
                                        foreground="#4a6fa5")
        self.file_info_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 数据统计
        stats_label = ttk.Label(left_frame, text="数据统计:", 
                               font=('Arial', 10, 'bold'))
        stats_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        self.stats_text = tk.Text(left_frame, height=8, width=40, 
                                 font=('Courier', 9), bg='#f8f9fa')
        self.stats_text.grid(row=2, column=0, 
                            sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 过滤选项
        filter_label = ttk.Label(left_frame, text="数据过滤:", 
                                font=('Arial', 10, 'bold'))
        filter_label.grid(row=3, column=0, sticky=tk.W, pady=(10, 5))
        
        filter_frame = ttk.Frame(left_frame)
        filter_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(filter_frame, text="股票代码:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.stock_filter_var = tk.StringVar()
        stock_filter_entry = ttk.Entry(filter_frame, 
                                      textvariable=self.stock_filter_var, 
                                      width=15)
        stock_filter_entry.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(filter_frame, text="关注日期:").grid(
            row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.date_filter_var = tk.StringVar()
        date_filter_entry = ttk.Entry(filter_frame, 
                                     textvariable=self.date_filter_var, 
                                     width=15)
        date_filter_entry.grid(row=0, column=3, padx=(0, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=10)
        
        filter_button = ttk.Button(button_frame, text="应用过滤", 
                                  command=self.apply_filter)
        filter_button.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_filter_button = ttk.Button(button_frame, text="清除过滤", 
                                        command=self.clear_filter)
        clear_filter_button.pack(side=tk.LEFT, padx=(0, 5))
        
        refresh_button = ttk.Button(button_frame, text="重新加载", 
                                   command=self.load_file)
        refresh_button.pack(side=tk.LEFT)
        
        # 数据表格框架
        table_frame = ttk.LabelFrame(left_frame, text="股票数据", 
                                    padding="5")
        table_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), 
                        pady=(10, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        columns = ('序号', '时间戳', '股票代码', '关注日期')
        self.tree = ttk.Treeview(table_frame, columns=columns, 
                                show='headings', height=15)
        
        # 定义列
        col_widths = [50, 150, 100, 100]
        for idx, col in enumerate(columns):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[idx], anchor='center')
        
        # 添加滚动条
        tree_scrollbar = ttk.Scrollbar(table_frame, 
                                      orient=tk.VERTICAL, 
                                      command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 添加水平滚动条
        tree_hscrollbar = ttk.Scrollbar(table_frame, 
                                       orient=tk.HORIZONTAL, 
                                       command=self.tree.xview)
        self.tree.configure(xscrollcommand=tree_hscrollbar.set)
        
        # 网格布局
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        tree_hscrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 绑定双击事件
        self.tree.bind('<Double-Button-1>', self.on_row_double_click)
        
        # 绑定Enter键到过滤
        stock_filter_entry.bind('<Return>', lambda e: self.apply_filter())
        date_filter_entry.bind('<Return>', lambda e: self.apply_filter())
        
        return left_frame
    
    def create_right_panel(self, parent):
        """创建右侧面板"""
        right_frame = ttk.Frame(parent)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        # 创建工具按钮区域
        tool_frame = ttk.Frame(right_frame, height=40)
        tool_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        tool_frame.grid_propagate(False)  # 固定高度
        
        # 通达信按钮
        self.tdx_button = ttk.Button(tool_frame, text="通达信", 
                                   state='disabled',
                                   command=self.open_tdx)
        self.tdx_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 同花顺按钮
        self.ths_button = ttk.Button(tool_frame, text="同花顺", 
                                   state='disabled',
                                   command=self.open_ths)
        self.ths_button.pack(side=tk.LEFT)
        
        # 创建K线图容器框架
        kline_frame = ttk.LabelFrame(right_frame, text="K线图", padding="5")
        kline_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        kline_frame.columnconfigure(0, weight=1)
        kline_frame.rowconfigure(0, weight=1)
        
        # 创建K线图容器
        self.kline_container = ttk.Frame(kline_frame)
        self.kline_container.grid(row=0, column=0, 
                                 sticky=(tk.W, tk.E, tk.N, tk.S), 
                                 padx=5, pady=5)
        self.kline_container.columnconfigure(0, weight=1)
        self.kline_container.rowconfigure(0, weight=1)
        
        # 初始提示
        tip_label = ttk.Label(self.kline_container, 
                             text="双击左侧表格中的任意行查看K线图", 
                             font=('Arial', 12),
                             foreground="#666666")
        tip_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        return right_frame
    
    def find_window(self, keywords):
        """查找包含关键字的窗口"""
        try:
            for window in gw.getAllWindows():
                if window.title:
                    for keyword in keywords:
                        if keyword in window.title:
                            return window
        except Exception as e:
            print(f"查找窗口出错: {e}")
        
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
    
    def open_tdx(self):
        """打开通达信并自动定位到当前股票"""
        if not self.current_stock_code:
            messagebox.showinfo("提示", "请先选择股票")
            return
        
        stock_code = self.current_stock_code
        
        # 1. 首先尝试查找已打开的窗口
        tdx_window = self.find_window(["通达信", "TDX"])
        
        if tdx_window:
            # 通达信已打开，激活窗口
            if self.activate_window(tdx_window):
                self.status_label.config(
                    text=f"正在通达信中定位 {stock_code} 的日K线...")
                # 在通达信中自动输入股票代码
                self.auto_input_tdx_stock(stock_code, tdx_window)
            else:
                self.status_label.config(
                    text="通达信已打开，但无法激活窗口")
        else:
            # 通达信未打开，启动程序
            self.launch_tdx_directly(stock_code)
    
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
            
            self.status_label.config(
                text=f"已在通达信中定位到 {padded_code} 的日K线")
            
        except Exception as e:
            messagebox.showerror("错误", f"通达信自动化失败: {e}")
            padded_code = stock_code.zfill(6)
            self.status_label.config(
                text=f"通达信自动化失败，请手动输入 {padded_code}")
    
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
                    
                    # 尝试查找窗口
                    tdx_window = self.find_window(["通达信", "TDX"])
                    if tdx_window and self.activate_window(tdx_window):
                        time.sleep(2)
                        self.auto_input_tdx_stock(stock_code, tdx_window)
                    else:
                        self.status_label.config(
                            text=f"已启动通达信，请手动输入 {stock_code}")
                    return
            
            messagebox.showinfo("提示", 
                f"未找到通达信程序，请手动打开后输入 {stock_code}")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动通达信失败: {e}")
    
    def open_ths(self):
        """打开同花顺并自动定位到当前股票"""
        if not self.current_stock_code:
            messagebox.showinfo("提示", "请先选择股票")
            return
        
        stock_code = self.current_stock_code
        
        # 1. 首先尝试查找已打开的窗口
        ths_window = self.find_window(["同花顺", "THS", "hexin"])
        
        if ths_window:
            # 同花顺已打开，激活窗口
            if self.activate_window(ths_window):
                padded_code = stock_code.zfill(6)  # 补齐到6位
                self.status_label.config(
                    text=f"正在同花顺中定位 {padded_code} 的日K线...")
                # 在同花顺中自动输入股票代码
                self.auto_input_ths_stock(stock_code, ths_window)
            else:
                self.status_label.config(
                    text="同花顺已打开，但无法激活窗口")
        else:
            # 同花顺未打开，启动程序
            self.launch_ths_directly(stock_code)
    
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
            
            self.status_label.config(
                text=f"已在同花顺中定位到 {padded_code} 的日K线")
            
        except Exception as e:
            messagebox.showerror("错误", f"同花顺自动化失败: {e}")
            padded_code = stock_code.zfill(6)
            self.status_label.config(
                text=f"同花顺自动化失败，请手动输入 {padded_code}")
    
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
                    
                    # 尝试查找窗口
                    ths_window = self.find_window(["同花顺", "THS", "hexin"])
                    if ths_window and self.activate_window(ths_window):
                        time.sleep(2)
                        self.auto_input_ths_stock(stock_code, ths_window)
                    else:
                        padded_code = stock_code.zfill(6)
                        self.status_label.config(
                            text=f"已启动同花顺，请手动输入 {padded_code}")
                    return
            
            padded_code = stock_code.zfill(6)
            messagebox.showinfo("提示", 
                f"未找到同花顺程序，请手动打开后输入 {padded_code}")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动同花顺失败: {e}")
    
    def select_file(self):
        """选择数据文件"""
        file_path = filedialog.askopenfilename(
            title="选择数据文件",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.current_file = file_path
            self.file_path_var.set(os.path.basename(file_path))
            self.load_file()
    
    def load_file(self):
        """加载并显示数据"""
        if not self.current_file or not os.path.exists(self.current_file):
            messagebox.showwarning("警告", "请先选择有效的文件")
            return
        
        self.status_label.config(text="正在解析数据...")
        self.root.update()
        
        success, message = self.parser.parse(self.current_file)
        
        if success:
            self.data_records = self.parser.data
            self.display_data()
            self.update_stats()
            self.file_info_label.config(
                text=f"{os.path.basename(self.current_file)} "
                    f"({len(self.data_records)} 条记录)")
            self.status_label.config(
                text=f"数据加载完成: {len(self.data_records)} 条记录")
        else:
            self.status_label.config(text="数据加载失败")
            messagebox.showerror("错误", message)
    
    def update_stats_text(self, text):
        """更新统计文本显示"""
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, text)
        self.stats_text.configure(state='disabled')
    
    def display_data(self, data=None):
        """在表格中显示数据"""
        if data is None:
            data = self.data_records
        
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加新数据
        for idx, record in enumerate(data, 1):
            self.tree.insert('', 'end', values=(
                idx,
                record['timestamp'],
                record['stock_code'],
                record['focus_date']
            ))
    
    def update_stats(self):
        """更新统计数据"""
        if not self.data_records:
            self.update_stats_text("无数据")
            return
        
        # 计算统计信息
        total_records = len(self.data_records)
        unique_stocks = len(set(record['stock_code'] 
                               for record in self.data_records))
        date_range = sorted(set(record['focus_date'] 
                               for record in self.data_records))
        
        if date_range:
            min_date = min(date_range)
            max_date = max(date_range)
        else:
            min_date = max_date = "N/A"
        
        # 统计每个日期的记录数
        date_counts = {}
        for record in self.data_records:
            date = record['focus_date']
            date_counts[date] = date_counts.get(date, 0) + 1
        
        # 显示统计信息
        stats_text = f"=== 数据统计 ===\n"
        stats_text += f"总记录数: {total_records}\n"
        stats_text += f"唯一股票数: {unique_stocks}\n"
        stats_text += f"日期范围: {min_date} 到 {max_date}\n"
        stats_text += f"数据文件: {os.path.basename(self.current_file)}\n"
        
        stats_text += "=== 日期分布 ===\n"
        stats_text += "-" * 30 + "\n"
        
        # 只显示前20个日期的统计
        sorted_dates = sorted(date_counts.items(), key=lambda x: x[0])
        for date, count in sorted_dates[:20]:
            stats_text += f"{date}: {count} 条记录\n"
        
        if len(date_counts) > 20:
            stats_text += f"... 还有 {len(date_counts) - 20} 个日期\n"
        
        self.update_stats_text(stats_text)
    
    def apply_filter(self):
        """应用过滤条件"""
        if not self.data_records:
            return
        
        stock_filter = self.stock_filter_var.get().strip()
        date_filter = self.date_filter_var.get().strip()
        
        filtered_data = self.data_records
        
        if stock_filter:
            filtered_data = [r for r in filtered_data 
                            if stock_filter in r['stock_code']]
        
        if date_filter:
            filtered_data = [r for r in filtered_data 
                            if date_filter in r['focus_date']]
        
        self.display_data(filtered_data)
        self.status_label.config(
            text=f"显示 {len(filtered_data)} 条记录 (已过滤)")
    
    def clear_filter(self):
        """清除过滤条件"""
        self.stock_filter_var.set("")
        self.date_filter_var.set("")
        self.display_data()
        self.status_label.config(
            text=f"显示所有 {len(self.data_records)} 条记录")
    
    def on_row_double_click(self, event):
        """双击行事件"""
        if not self.data_records:
            messagebox.showinfo("提示", "请先加载数据文件")
            return
            
        selection = self.tree.selection()
        if not selection:
            return
        
        # 获取选中行的数据
        item = self.tree.item(selection[0])
        values = item['values']
        
        if len(values) >= 4:
            stock_code = str(values[2])
            focus_date_str = str(values[3])
            
            # 保存当前选择的股票代码
            self.current_stock_code = stock_code
            self.current_focus_date = focus_date_str
            
            # 启用外部软件按钮
            self.tdx_button.config(state='normal')
            self.ths_button.config(state='normal')
            
            # 验证日期格式
            if not (len(focus_date_str) == 8 and focus_date_str.isdigit()):
                messagebox.showwarning("警告", 
                    f"日期格式错误: {focus_date_str}，"
                    f"应为8位数字格式(YYYYMMDD)")
                return
            
            # 在主线程中打开K线图
            self.show_kline(stock_code, focus_date_str)
    
    def show_kline(self, stock_code, focus_date_str):
        """显示K线图"""
        try:
            # 计算日期范围（关注日期前后各15天）
            focus_date_obj = datetime.strptime(focus_date_str, "%Y%m%d")
            start_date = (focus_date_obj - timedelta(days=15)).strftime(
                "%Y%m%d")
            end_date = (focus_date_obj + timedelta(days=15)).strftime(
                "%Y%m%d")
            
            # 更新状态
            self.status_label.config(
                text=f"正在加载 {stock_code} 的K线图，"
                f"关注日期: {focus_date_str}")
            self.root.update()
            
            # 清除现有的K线图
            for widget in self.kline_container.winfo_children():
                widget.destroy()
            
            # 创建K线图查看器（嵌入模式）
            self.current_kline_viewer = KLineViewerOptimized(
                parent=self.kline_container,
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                target_date=focus_date_str,
                is_embedded=True
            )
            
            # 显示嵌入的K线图
            success = self.current_kline_viewer.show_embedded(
                self.kline_container)
            
            if success:
                self.status_label.config(
                    text=f"已显示 {stock_code} 的K线图，"
                    f"关注日期: {focus_date_str}")
            else:
                self.status_label.config(
                    text=f"无法加载 {stock_code} 的K线图")
                messagebox.showerror("错误", 
                    f"无法加载 {stock_code} 的K线图数据")
                
        except ValueError as e:
            messagebox.showerror("错误", f"日期格式错误: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"无法显示K线图: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()


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
    
    # 创建并运行GUI应用程序
    app = StockKLineViewerGUI()
    app.run()


if __name__ == '__main__':
    main()