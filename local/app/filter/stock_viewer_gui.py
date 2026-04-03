#!/usr/bin/python
#-*-coding:UTF-8-*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
import sys
from kline_viewer_optimized import KLineViewerOptimized
from tdx_tools import TdxTools
from ths_tools import ThsTools


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
        self.left_panel_visible = True  # 左侧面板是否可见
        
        # 创建通达信和同花顺工具实例
        self.tdx_tools = TdxTools()
        self.ths_tools = ThsTools()
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("股票关注日期查看器")
        
        # 设置初始尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = int(screen_width * 0.85)
        height = int(screen_height * 0.85)
        self.root.geometry(f"{width}x{height}+{int(screen_width*0.08)}+{int(screen_height*0.08)}")
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 允许窗口调整大小和最大化
        self.root.resizable(True, True)
        
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
                       rowheight=22,
                       fieldbackground="#f0f0f0")
        
        style.configure("Treeview.Heading",
                       background="#4a6fa5",
                       foreground="white",
                       font=('Arial', 8, 'bold'))
        
        style.map("Treeview",
                 background=[('selected', '#3465a4')],
                 foreground=[('selected', 'white')])
        
        # 小字体样式
        style.configure("Tiny.TButton", font=('Arial', 8))
        style.configure("Tiny.TLabel", font=('Arial', 8))
        style.configure("Tiny.TEntry", font=('Arial', 8))
    
    def init_ui(self):
        """初始化用户界面"""
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # 标题和文件选择区域
        header_frame = ttk.Frame(main_container)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        title_label = ttk.Label(header_frame, 
                               text="股票关注日期查看器", 
                               font=('Arial', 12, 'bold'),
                               foreground="#2c3e50")
        title_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 左侧面板切换按钮
        self.toggle_button = ttk.Button(header_frame, 
                                       text="◀",  # 左箭头
                                       width=2,
                                       command=self.toggle_left_panel)
        self.toggle_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 文件选择按钮
        self.file_path_var = tk.StringVar()
        self.file_path_var.set("未选择文件")
        
        file_button_frame = ttk.Frame(header_frame)
        file_button_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        select_file_btn = ttk.Button(file_button_frame, 
                                    text="选择文件", 
                                    command=self.select_file,
                                    style="Tiny.TButton")
        select_file_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.file_label = ttk.Label(file_button_frame, 
                                   textvariable=self.file_path_var,
                                   foreground="#666666",
                                   font=('Arial', 8))
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 中间内容区域
        self.content_container = ttk.Frame(main_container)
        self.content_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 左侧控制面板 - 初始可见
        self.left_frame = self.create_left_panel(self.content_container)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 右侧K线图区域
        self.right_frame = self.create_right_panel(self.content_container)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))
        
        # 状态栏
        status_frame = ttk.Frame(main_container)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        self.status_label = ttk.Label(status_frame, 
                                     text="请选择数据文件", 
                                     relief=tk.SUNKEN, anchor=tk.W,
                                     font=('Arial', 8))
        self.status_label.pack(fill=tk.X)
        
        # 初始化统计文本
        self.update_stats_text("等待加载数据...")
        
        # 初始调整
        self.root.after(100, self._initial_adjustment)
    
    def _initial_adjustment(self):
        """初始调整"""
        # 确保左侧面板宽度合适
        if hasattr(self, 'tree'):
            # 动态调整列宽
            self.tree.column('#1', width=25)  # 序号
            self.tree.column('#2', width=60)  # 时间
            self.tree.column('#3', width=40)  # 代码
            self.tree.column('#4', width=60)  # 日期
    
    def create_left_panel(self, parent):
        """创建左侧面板 - 进一步缩小，添加隐藏功能"""
        left_frame = ttk.LabelFrame(parent, text="数据面板", 
                                   padding="3")
        
        # 使用网格布局
        left_frame.columnconfigure(0, weight=1)
        for i in range(7):
            left_frame.rowconfigure(i, weight=0)
        left_frame.rowconfigure(6, weight=1)
        
        # 文件信息
        info_frame = ttk.Frame(left_frame)
        info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        
        ttk.Label(info_frame, text="文件:", 
                 font=('Arial', 8, 'bold')).pack(side=tk.LEFT)
        self.file_info_label = ttk.Label(info_frame, 
                                        text="无", 
                                        foreground="#4a6fa5",
                                        font=('Arial', 8))
        self.file_info_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # 数据统计
        stats_label = ttk.Label(left_frame, text="统计:", 
                               font=('Arial', 8, 'bold'))
        stats_label.grid(row=1, column=0, sticky="w", pady=(0, 2))
        
        # 统计文本
        self.stats_text = tk.Text(left_frame, height=3,
                                 font=('Courier', 7), bg='#f8f9fa',
                                 wrap=tk.WORD)
        self.stats_text.grid(row=2, column=0, sticky="nsew", pady=(0, 3))
        
        # 过滤选项
        filter_label = ttk.Label(left_frame, text="过滤:", 
                                font=('Arial', 8, 'bold'))
        filter_label.grid(row=3, column=0, sticky="w", pady=(0, 2))
        
        # 过滤输入框
        filter_frame = ttk.Frame(left_frame)
        filter_frame.grid(row=4, column=0, sticky="ew", pady=(0, 3))
        
        # 股票代码过滤
        ttk.Label(filter_frame, text="代码:", 
                 font=('Arial', 7)).pack(side=tk.LEFT, padx=(0, 2))
        self.stock_filter_var = tk.StringVar()
        stock_filter_entry = ttk.Entry(filter_frame, 
                                      textvariable=self.stock_filter_var, 
                                      width=6,
                                      font=('Arial', 7))
        stock_filter_entry.pack(side=tk.LEFT, padx=(0, 6))
        
        # 日期过滤
        ttk.Label(filter_frame, text="日期:", 
                 font=('Arial', 7)).pack(side=tk.LEFT, padx=(0, 2))
        self.date_filter_var = tk.StringVar()
        date_filter_entry = ttk.Entry(filter_frame, 
                                     textvariable=self.date_filter_var, 
                                     width=6,
                                     font=('Arial', 7))
        date_filter_entry.pack(side=tk.LEFT)
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=5, column=0, sticky="ew", pady=(0, 5))
        
        filter_button = ttk.Button(button_frame, text="过滤", 
                                  command=self.apply_filter,
                                  style="Tiny.TButton",
                                  width=4)
        filter_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        clear_filter_button = ttk.Button(button_frame, text="清除", 
                                        command=self.clear_filter,
                                        style="Tiny.TButton",
                                        width=4)
        clear_filter_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        refresh_button = ttk.Button(button_frame, text="刷新", 
                                   command=self.load_file,
                                   style="Tiny.TButton",
                                   width=4)
        refresh_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 数据表格框架
        table_frame = ttk.LabelFrame(left_frame, text="数据列表", 
                                    padding="2")
        table_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview - 进一步压缩
        columns = ('#', '时间', '代码', '日期')
        self.tree = ttk.Treeview(table_frame, columns=columns, 
                                show='headings', height=10)
        
        # 定义列 - 进一步减小宽度
        col_widths = [25, 60, 40, 60]  # 总宽度185像素
        for idx, col in enumerate(columns):
            self.tree.heading(col, text=col, anchor='center')
            self.tree.column(col, width=col_widths[idx], anchor='center', 
                           minwidth=col_widths[idx]//2)
        
        # 添加垂直滚动条
        tree_scrollbar = ttk.Scrollbar(table_frame, 
                                      orient=tk.VERTICAL, 
                                      command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 网格布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 绑定双击事件
        self.tree.bind('<Double-Button-1>', self.on_row_double_click)
        
        # 绑定Enter键到过滤
        stock_filter_entry.bind('<Return>', lambda e: self.apply_filter())
        date_filter_entry.bind('<Return>', lambda e: self.apply_filter())
        
        return left_frame
    
    def toggle_left_panel(self):
        """切换左侧面板显示/隐藏"""
        if self.left_panel_visible:
            # 隐藏左侧面板
            self.left_frame.pack_forget()
            self.toggle_button.config(text="▶")  # 右箭头
            self.left_panel_visible = False
            
            # 扩展右侧面板
            self.right_frame.pack_forget()
            self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))
        else:
            # 显示左侧面板
            self.right_frame.pack_forget()
            
            # 重新显示左侧面板
            self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.toggle_button.config(text="◀")  # 左箭头
            
            # 重新显示右侧面板
            self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(3, 0))
            self.left_panel_visible = True
        
        # 更新布局
        self.content_container.update_idletasks()
    
    def create_right_panel(self, parent):
        """创建右侧面板"""
        right_frame = ttk.Frame(parent)
        
        # 工具按钮区域
        tool_frame = ttk.Frame(right_frame, height=35)
        tool_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 3))
        
        # 通达信按钮
        self.tdx_button = ttk.Button(tool_frame, text="通达信", 
                                   state='disabled',
                                   command=self.open_tdx,
                                   style="Tiny.TButton")
        self.tdx_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 同花顺按钮
        self.ths_button = ttk.Button(tool_frame, text="同花顺", 
                                   state='disabled',
                                   command=self.open_ths,
                                   style="Tiny.TButton")
        self.ths_button.pack(side=tk.LEFT)
        
        # K线图容器框架
        self.kline_frame = ttk.LabelFrame(right_frame, text="K线图", padding="3")
        self.kline_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # K线图容器
        self.kline_container = ttk.Frame(self.kline_frame)
        self.kline_container.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # 初始提示
        tip_label = ttk.Label(self.kline_container, 
                             text="双击左侧表格查看K线图", 
                             font=('Arial', 10),
                             foreground="#666666")
        tip_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        return right_frame
    
    def show_kline(self, stock_code, focus_date_str):
        """显示K线图 - 稳定版本，无背景色错误"""
        try:
            # 计算日期范围
            focus_date_obj = datetime.strptime(focus_date_str, "%Y%m%d")
            start_date = (focus_date_obj - timedelta(days=15)).strftime("%Y%m%d")
            end_date = (focus_date_obj + timedelta(days=15)).strftime("%Y%m%d")
            
            self.status_label.config(
                text=f"正在加载 {stock_code} 的K线图，关注日期: {focus_date_str}")
            
            # 清除现有的K线图
            for widget in self.kline_container.winfo_children():
                widget.destroy()
            
            # 简单加载提示
            loading_label = tk.Label(self.kline_container, 
                                   text=f"正在加载 {stock_code}...", 
                                   font=('Arial', 10),
                                   foreground="#666666")
            loading_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # 立即更新界面
            self.kline_container.update()
            
            # 使用延迟创建K线图
            self.root.after(50, lambda: self._create_kline_after_delay(
                stock_code, start_date, end_date, focus_date_str, loading_label))
            
        except Exception as e:
            messagebox.showerror("错误", f"无法显示K线图: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_kline_after_delay(self, stock_code, start_date, end_date, focus_date_str, loading_label):
        """延迟创建K线图"""
        try:
            # 创建K线图查看器
            self.current_kline_viewer = KLineViewerOptimized(
                parent=self.kline_container,
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date,
                target_date=focus_date_str,
                is_embedded=True
            )
            
            # 显示嵌入的K线图
            success = self.current_kline_viewer.show_embedded(self.kline_container)
            
            if success:
                loading_label.destroy()
                self.status_label.config(
                    text=f"已显示 {stock_code} 的K线图，关注日期: {focus_date_str}")
                
                # 稳定布局调整
                self._stable_final_adjustment()
                
            else:
                loading_label.config(text="K线图加载失败", foreground="#ff0000")
                self.status_label.config(text=f"无法加载 {stock_code} 的K线图")
                
        except Exception as e:
            loading_label.config(text=f"加载失败: {str(e)[:30]}", foreground="#ff0000")
    
    def _stable_final_adjustment(self):
        """稳定的最终布局调整"""
        # 确保K线图尺寸合适
        if hasattr(self, 'current_kline_viewer') and self.current_kline_viewer:
            canvas = self.current_kline_viewer.canvas
            if canvas:
                canvas_widget = canvas.get_tk_widget()
                # 设置固定尺寸
                canvas_widget.config(width=600, height=500)
        
        # 延迟重新布局
        self.root.after(100, self.root.update_idletasks)
    
    def open_tdx(self):
        """打开通达信并自动定位到当前股票"""
        if not self.current_stock_code:
            messagebox.showinfo("提示", "请先选择股票")
            return
        
        stock_code = self.current_stock_code
        self.tdx_tools.status_label = self.status_label
        success, message = self.tdx_tools.open_tdx(stock_code, self.status_label)
        if not success:
            messagebox.showerror("错误", message)
    
    def open_ths(self):
        """打开同花顺并自动定位到当前股票"""
        if not self.current_stock_code:
            messagebox.showinfo("提示", "请先选择股票")
            return
        
        stock_code = self.current_stock_code
        self.ths_tools.status_label = self.status_label
        success, message = self.ths_tools.open_ths(stock_code, self.status_label)
        if not success:
            messagebox.showerror("错误", message)
    
    def select_file(self):
        """选择数据文件"""
        file_path = filedialog.askopenfilename(
            title="选择数据文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            filename = os.path.basename(file_path)
            if len(filename) > 20:
                filename = filename[:17] + "..."
            self.file_path_var.set(filename)
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
            filename = os.path.basename(self.current_file)
            if len(filename) > 12:
                filename = filename[:9] + "..."
            self.file_info_label.config(text=filename)
            self.status_label.config(
                text=f"加载完成: {len(self.data_records)} 条")
        else:
            self.status_label.config(text="数据加载失败")
            messagebox.showerror("错误", message)
    
    def update_stats_text(self, text):
        """更新统计文本显示"""
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, text)
        self.stats_text.configure(state='disabled')
    
    def display_data(self, data=None):
        """在表格中显示数据 - 紧凑格式"""
        if data is None:
            data = self.data_records
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for idx, record in enumerate(data, 1):
            # 紧凑格式化
            timestamp = str(record['timestamp'])
            if len(timestamp) > 12:  # 更严格的限制
                timestamp = timestamp[:9] + "..."
            
            stock_code = str(record['stock_code'])
            if len(stock_code) > 6:
                stock_code = stock_code[:6]
            
            focus_date = str(record['focus_date'])
            if len(focus_date) > 8:
                focus_date = focus_date[:8]
            
            # 确保总字符数在40左右
            total_chars = len(str(idx)) + len(timestamp) + len(stock_code) + len(focus_date)
            
            if total_chars > 40:
                timestamp = timestamp[:8] + "..."
            
            self.tree.insert('', 'end', values=(
                idx,
                timestamp,
                stock_code,
                focus_date
            ))
    
    def update_stats(self):
        """更新统计数据"""
        if not self.data_records:
            self.update_stats_text("无数据")
            return
        
        total_records = len(self.data_records)
        unique_stocks = len(set(record['stock_code'] for record in self.data_records))
        
        stats_text = f"总数: {total_records}\n"
        stats_text += f"股票: {unique_stocks}\n"
        stats_text += f"文件: {os.path.basename(self.current_file)[:10]}..."
        
        self.update_stats_text(stats_text)
    
    def apply_filter(self):
        """应用过滤条件"""
        if not self.data_records:
            return
        
        stock_filter = self.stock_filter_var.get().strip()
        date_filter = self.date_filter_var.get().strip()
        filtered_data = self.data_records
        
        if stock_filter:
            filtered_data = [r for r in filtered_data if stock_filter in r['stock_code']]
        if date_filter:
            filtered_data = [r for r in filtered_data if date_filter in r['focus_date']]
        
        self.display_data(filtered_data)
        self.status_label.config(text=f"显示 {len(filtered_data)} 条")
    
    def clear_filter(self):
        """清除过滤条件"""
        self.stock_filter_var.set("")
        self.date_filter_var.set("")
        self.display_data()
        self.status_label.config(text=f"显示所有 {len(self.data_records)} 条")
    
    def on_row_double_click(self, event):
        """双击行事件"""
        if not self.data_records:
            messagebox.showinfo("提示", "请先加载数据文件")
            return
        
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        if len(values) >= 4:
            stock_code = str(values[2])
            focus_date_str = str(values[3])
            
            self.current_stock_code = stock_code
            self.current_focus_date = focus_date_str
            
            self.tdx_button.config(state='normal')
            self.ths_button.config(state='normal')
            
            if not (len(focus_date_str) == 8 and focus_date_str.isdigit()):
                messagebox.showwarning("警告", f"日期格式错误: {focus_date_str}")
                return
            
            self.show_kline(stock_code, focus_date_str)
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()


def main():
    """主函数"""
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
    
    app = StockKLineViewerGUI()
    app.run()


if __name__ == '__main__':
    main()