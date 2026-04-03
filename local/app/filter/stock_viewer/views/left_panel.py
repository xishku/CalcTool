#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
左侧面板
创建和管理左侧面板，包括数据表格显示、统计信息和过滤功能
"""

import tkinter as tk
from tkinter import ttk
import os


class LeftPanel:
    """左侧面板 - 管理数据表格显示、统计信息和过滤功能"""
    
    def __init__(self, parent, controller):
        """
        初始化左侧面板
        
        参数:
            parent: 父容器
            controller: 主控制器实例
        """
        self.parent = parent
        self.controller = controller
        self.frame = None
        self.tree = None
        self.stats_text = None
        self.file_info_label = None
        self.stock_filter_var = None
        self.date_filter_var = None
        
        # 创建左侧面板
        self.create()
    
    def create(self):
        """创建左侧面板"""
        try:
            # 创建主框架
            self.frame = ttk.LabelFrame(
                self.parent, 
                text="数据面板", 
                padding="8"
            )
            
            # 使用网格布局
            self._setup_grid_layout()
            
            # 创建各个部分
            self._create_file_info()
            self._create_stats_section()
            self._create_filter_section()
            self._create_buttons()
            self._create_data_table()
            
            print("[INFO] 左侧面板创建完成")
            return self.frame
            
        except Exception as e:
            print(f"[ERROR] 创建左侧面板时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _setup_grid_layout(self):
        """设置网格布局"""
        # 配置列权重
        self.frame.columnconfigure(0, weight=1)
        
        # 配置行权重
        for i in range(7):
            self.frame.rowconfigure(i, weight=0)
        
        # 表格行可扩展
        self.frame.rowconfigure(6, weight=1)
    
    def _create_file_info(self):
        """创建文件信息区域"""
        try:
            # 文件信息框架
            info_frame = ttk.Frame(self.frame)
            info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
            
            # 文件标签
            file_label = ttk.Label(
                info_frame, 
                text="当前文件:", 
                font=('Arial', 9, 'bold')
            )
            file_label.pack(side=tk.LEFT)
            
            # 文件信息标签
            self.file_info_label = ttk.Label(
                info_frame, 
                text="无", 
                foreground="#4a6fa5",
                font=('Arial', 9)
            )
            self.file_info_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # 空白填充
            filler = ttk.Frame(info_frame)
            filler.pack(side=tk.RIGHT, expand=True, fill=tk.X)
            
        except Exception as e:
            print(f"[ERROR] 创建文件信息区域时出错: {str(e)}")
    
    def _create_stats_section(self):
        """创建统计区域"""
        try:
            # 统计标签
            stats_label = ttk.Label(
                self.frame, 
                text="数据统计:", 
                font=('Arial', 10, 'bold')
            )
            stats_label.grid(row=1, column=0, sticky="w", pady=(0, 5))
            
            # 统计文本区域
            self.stats_text = tk.Text(
                self.frame, 
                height=6,
                font=('Courier', 9), 
                bg='#f8f9fa',
                wrap=tk.WORD
            )
            self.stats_text.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
            
            # 初始文本
            self._update_stats_initial_text()
            
        except Exception as e:
            print(f"[ERROR] 创建统计区域时出错: {str(e)}")
    
    def _update_stats_initial_text(self):
        """更新统计初始文本"""
        try:
            if self.stats_text:
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.insert(1.0, "等待加载数据...\n\n")
                self.stats_text.insert(tk.END, "请点击'选择文件'按钮加载数据")
                self.stats_text.configure(state='disabled')
                
        except Exception as e:
            print(f"[ERROR] 更新统计初始文本时出错: {str(e)}")
    
    def _create_filter_section(self):
        """创建过滤区域"""
        try:
            # 过滤标签
            filter_label = ttk.Label(
                self.frame, 
                text="数据过滤:", 
                font=('Arial', 10, 'bold')
            )
            filter_label.grid(row=3, column=0, sticky="w", pady=(0, 5))
            
            # 过滤框架
            filter_frame = ttk.Frame(self.frame)
            filter_frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))
            
            # 创建过滤输入框
            self._create_filter_inputs(filter_frame)
            
        except Exception as e:
            print(f"[ERROR] 创建过滤区域时出错: {str(e)}")
    
    def _create_filter_inputs(self, parent_frame):
        """创建过滤输入框"""
        try:
            # 股票代码过滤
            stock_frame = ttk.Frame(parent_frame)
            stock_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            stock_label = ttk.Label(
                stock_frame, 
                text="股票代码:", 
                font=('Arial', 9)
            )
            stock_label.pack(side=tk.LEFT, padx=(0, 5))
            
            self.stock_filter_var = tk.StringVar()
            self.stock_filter_entry = ttk.Entry(
                stock_frame, 
                textvariable=self.stock_filter_var, 
                width=10,
                font=('Arial', 9)
            )
            self.stock_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 日期过滤
            date_frame = ttk.Frame(parent_frame)
            date_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            
            date_label = ttk.Label(
                date_frame, 
                text="关注日期:", 
                font=('Arial', 9)
            )
            date_label.pack(side=tk.LEFT, padx=(0, 5))
            
            self.date_filter_var = tk.StringVar()
            self.date_filter_entry = ttk.Entry(
                date_frame, 
                textvariable=self.date_filter_var, 
                width=10,
                font=('Arial', 9)
            )
            self.date_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 绑定Enter键
            self._bind_filter_events()
            
        except Exception as e:
            print(f"[ERROR] 创建过滤输入框时出错: {str(e)}")
    
    def _bind_filter_events(self):
        """绑定过滤事件"""
        try:
            # 绑定Enter键到过滤
            self.stock_filter_entry.bind(
                '<Return>', 
                lambda e: self._apply_filter_from_ui()
            )
            self.date_filter_entry.bind(
                '<Return>', 
                lambda e: self._apply_filter_from_ui()
            )
            
            # 绑定Ctrl+F聚焦到过滤框
            if hasattr(self.controller, 'root'):
                self.controller.root.bind(
                    '<Control-f>', 
                    lambda e: self._focus_filter_input()
                )
            
        except Exception as e:
            print(f"[ERROR] 绑定过滤事件时出错: {str(e)}")
    
    def _apply_filter_from_ui(self):
        """从UI应用过滤"""
        try:
            if hasattr(self.controller, 'filter_controller'):
                self.controller.filter_controller.apply_filter()
        except Exception as e:
            print(f"[ERROR] 应用过滤时出错: {str(e)}")
    
    def _focus_filter_input(self):
        """聚焦到过滤输入框"""
        try:
            if self.stock_filter_entry and self.stock_filter_entry.winfo_exists():
                self.stock_filter_entry.focus_set()
                self.stock_filter_entry.select_range(0, tk.END)
        except Exception as e:
            print(f"[ERROR] 聚焦过滤输入框时出错: {str(e)}")
    
    def _create_buttons(self):
        """创建按钮区域"""
        try:
            # 按钮框架
            button_frame = ttk.Frame(self.frame)
            button_frame.grid(row=5, column=0, sticky="ew", pady=(0, 10))
            
            # 创建按钮
            self._create_action_buttons(button_frame)
            
        except Exception as e:
            print(f"[ERROR] 创建按钮区域时出错: {str(e)}")
    
    def _create_action_buttons(self, parent_frame):
        """创建操作按钮"""
        try:
            # 应用过滤按钮
            filter_button = ttk.Button(
                parent_frame, 
                text="应用过滤", 
                command=self._apply_filter_from_ui,
                width=10
            )
            filter_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
            
            # 清除过滤按钮
            clear_filter_button = ttk.Button(
                parent_frame, 
                text="清除过滤", 
                command=self._clear_filter,
                width=10
            )
            clear_filter_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
            
            # 刷新数据按钮
            refresh_button = ttk.Button(
                parent_frame, 
                text="刷新数据", 
                command=self._refresh_data,
                width=10
            )
            refresh_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
            
        except Exception as e:
            print(f"[ERROR] 创建操作按钮时出错: {str(e)}")
    
    def _clear_filter(self):
        """清除过滤"""
        try:
            if hasattr(self.controller, 'filter_controller'):
                self.controller.filter_controller.clear_filter()
        except Exception as e:
            print(f"[ERROR] 清除过滤时出错: {str(e)}")
    
    def _refresh_data(self):
        """刷新数据"""
        try:
            if hasattr(self.controller, 'file_controller'):
                if hasattr(self.controller.file_controller, 'reload_last_file'):
                    self.controller.file_controller.reload_last_file()
                elif hasattr(self.controller.file_controller, 'load_file'):
                    self.controller.file_controller.load_file()
        except Exception as e:
            print(f"[ERROR] 刷新数据时出错: {str(e)}")
    
    def _create_data_table(self):
        """创建数据表格"""
        try:
            # 表格框架
            table_frame = ttk.LabelFrame(
                self.frame, 
                text="股票数据列表", 
                padding="5"
            )
            table_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 0))
            table_frame.columnconfigure(0, weight=1)
            table_frame.rowconfigure(0, weight=1)
            
            # 创建Treeview
            self._create_treeview(table_frame)
            
        except Exception as e:
            print(f"[ERROR] 创建数据表格时出错: {str(e)}")
    
    def _create_treeview(self, parent_frame):
        """创建Treeview表格"""
        try:
            # 定义列
            columns = ('序号', '时间', '代码', '日期')
            
            # 创建Treeview
            self.tree = ttk.Treeview(
                parent_frame, 
                columns=columns, 
                show='headings', 
                height=15
            )
            
            # 配置列
            self._configure_treeview_columns(columns)
            
            # 添加垂直滚动条
            self._add_treeview_scrollbar(parent_frame)
            
            # 绑定事件
            self._bind_treeview_events()
            
        except Exception as e:
            print(f"[ERROR] 创建Treeview时出错: {str(e)}")
    
    def _configure_treeview_columns(self, columns):
        """配置Treeview列"""
        try:
            # 列定义
            column_configs = [
                {'text': '序号', 'width': 40, 'anchor': 'center', 'minwidth': 30},
                {'text': '时间', 'width': 120, 'anchor': 'center', 'minwidth': 80},
                {'text': '代码', 'width': 60, 'anchor': 'center', 'minwidth': 40},
                {'text': '日期', 'width': 80, 'anchor': 'center', 'minwidth': 60}
            ]
            
            # 配置每一列
            for idx, config in enumerate(column_configs):
                self.tree.heading(f'#{idx+1}', text=config['text'], anchor=config['anchor'])
                self.tree.column(f'#{idx+1}', width=config['width'], 
                               minwidth=config['minwidth'], anchor=config['anchor'])
                
        except Exception as e:
            print(f"[ERROR] 配置Treeview列时出错: {str(e)}")
    
    def _add_treeview_scrollbar(self, parent_frame):
        """添加Treeview滚动条"""
        try:
            # 垂直滚动条
            tree_scrollbar_y = ttk.Scrollbar(
                parent_frame, 
                orient=tk.VERTICAL, 
                command=self.tree.yview
            )
            self.tree.configure(yscrollcommand=tree_scrollbar_y.set)
            
            # 网格布局
            self.tree.grid(row=0, column=0, sticky="nsew")
            tree_scrollbar_y.grid(row=0, column=1, sticky="ns")
            
        except Exception as e:
            print(f"[ERROR] 添加Treeview滚动条时出错: {str(e)}")
    
    def _bind_treeview_events(self):
        """绑定Treeview事件"""
        try:
            # 绑定双击事件
            self.tree.bind('<Double-Button-1>', self._on_row_double_click)
            
            # 绑定右键菜单
            self.tree.bind('<Button-3>', self._on_right_click)
            
            # 绑定选择事件
            self.tree.bind('<<TreeviewSelect>>', self._on_row_select)
            
        except Exception as e:
            print(f"[ERROR] 绑定Treeview事件时出错: {str(e)}")
    
    def _on_row_double_click(self, event):
        """行双击事件"""
        try:
            # 获取选中行
            selection = self.tree.selection()
            if not selection:
                return
            
            item = self.tree.item(selection[0])
            values = item['values']
            
            if len(values) >= 4:
                stock_code = str(values[2])
                focus_date_str = str(values[3])
                
                print(f"[INFO] 双击选择股票: {stock_code}, 日期: {focus_date_str}")
                
                # 调用控制器的处理函数
                if hasattr(self.controller, 'stock_controller'):
                    self.controller.stock_controller.on_stock_selected(
                        stock_code, focus_date_str
                    )
                    
        except Exception as e:
            print(f"[ERROR] 处理行双击事件时出错: {str(e)}")
    
    def _on_right_click(self, event):
        """右键点击事件"""
        try:
            # 获取点击位置
            item_id = self.tree.identify_row(event.y)
            
            if item_id:
                # 选中该行
                self.tree.selection_set(item_id)
                
                # 创建右键菜单
                menu = tk.Menu(self.tree, tearoff=0)
                
                # 添加菜单项
                menu.add_command(
                    label="查看K线图", 
                    command=lambda: self._show_kline_from_menu(item_id)
                )
                
                menu.add_separator()
                
                menu.add_command(
                    label="复制股票代码", 
                    command=lambda: self._copy_stock_code(item_id)
                )
                
                menu.add_command(
                    label="复制日期", 
                    command=lambda: self._copy_date(item_id)
                )
                
                menu.add_separator()
                
                menu.add_command(
                    label="过滤此股票", 
                    command=lambda: self._filter_by_stock(item_id)
                )
                
                menu.add_command(
                    label="过滤此日期", 
                    command=lambda: self._filter_by_date(item_id)
                )
                
                # 显示菜单
                menu.tk_popup(event.x_root, event.y_root)
                
        except Exception as e:
            print(f"[ERROR] 处理右键点击事件时出错: {str(e)}")
    
    def _on_row_select(self, event):
        """行选择事件"""
        try:
            # 可以在这里添加行选择时的处理逻辑
            pass
            
        except Exception as e:
            print(f"[ERROR] 处理行选择事件时出错: {str(e)}")
    
    def _show_kline_from_menu(self, item_id):
        """从菜单查看K线图"""
        try:
            item = self.tree.item(item_id)
            values = item['values']
            
            if len(values) >= 4:
                stock_code = str(values[2])
                focus_date_str = str(values[3])
                
                if hasattr(self.controller, 'stock_controller'):
                    self.controller.stock_controller.on_stock_selected(
                        stock_code, focus_date_str
                    )
                    
        except Exception as e:
            print(f"[ERROR] 从菜单查看K线图时出错: {str(e)}")
    
    def _copy_stock_code(self, item_id):
        """复制股票代码"""
        try:
            item = self.tree.item(item_id)
            values = item['values']
            
            if len(values) >= 3:
                stock_code = str(values[2])
                
                # 复制到剪贴板
                self.tree.clipboard_clear()
                self.tree.clipboard_append(stock_code)
                
                # 更新状态
                if hasattr(self.controller, 'get_status_label'):
                    status_label = self.controller.get_status_label()
                    if status_label:
                        status_label.config(text=f"已复制股票代码: {stock_code}")
                
                print(f"[INFO] 已复制股票代码: {stock_code}")
                
        except Exception as e:
            print(f"[ERROR] 复制股票代码时出错: {str(e)}")
    
    def _copy_date(self, item_id):
        """复制日期"""
        try:
            item = self.tree.item(item_id)
            values = item['values']
            
            if len(values) >= 4:
                date_str = str(values[3])
                
                # 复制到剪贴板
                self.tree.clipboard_clear()
                self.tree.clipboard_append(date_str)
                
                # 更新状态
                if hasattr(self.controller, 'get_status_label'):
                    status_label = self.controller.get_status_label()
                    if status_label:
                        status_label.config(text=f"已复制日期: {date_str}")
                
                print(f"[INFO] 已复制日期: {date_str}")
                
        except Exception as e:
            print(f"[ERROR] 复制日期时出错: {str(e)}")
    
    def _filter_by_stock(self, item_id):
        """按股票过滤"""
        try:
            item = self.tree.item(item_id)
            values = item['values']
            
            if len(values) >= 3:
                stock_code = str(values[2])
                
                # 设置过滤条件
                if self.stock_filter_var:
                    self.stock_filter_var.set(stock_code)
                
                # 应用过滤
                self._apply_filter_from_ui()
                
        except Exception as e:
            print(f"[ERROR] 按股票过滤时出错: {str(e)}")
    
    def _filter_by_date(self, item_id):
        """按日期过滤"""
        try:
            item = self.tree.item(item_id)
            values = item['values']
            
            if len(values) >= 4:
                date_str = str(values[3])
                
                # 设置过滤条件
                if self.date_filter_var:
                    self.date_filter_var.set(date_str)
                
                # 应用过滤
                self._apply_filter_from_ui()
                
        except Exception as e:
            print(f"[ERROR] 按日期过滤时出错: {str(e)}")
    
    def update_data_display(self, data_records):
        """
        更新数据显示
        
        参数:
            data_records: 数据记录列表
        """
        try:
            if not self.tree:
                return
            
            # 清空现有数据
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 添加新数据
            for idx, record in enumerate(data_records, 1):
                self._add_record_to_tree(idx, record)
            
            print(f"[INFO] 更新数据显示，共 {len(data_records)} 条记录")
            
        except Exception as e:
            print(f"[ERROR] 更新数据显示时出错: {str(e)}")
    
    def _add_record_to_tree(self, index, record):
        """添加记录到Treeview"""
        try:
            # 紧凑格式化
            timestamp = self._format_timestamp(getattr(record, 'timestamp', ''))
            stock_code = self._format_stock_code(getattr(record, 'stock_code', ''))
            focus_date = self._format_date(getattr(record, 'focus_date', ''))
            
            # 插入到Treeview
            self.tree.insert('', 'end', values=(
                index,
                timestamp,
                stock_code,
                focus_date
            ))
            
        except Exception as e:
            print(f"[ERROR] 添加记录到Treeview时出错: {str(e)}")
    
    def _format_timestamp(self, timestamp):
        """格式化时间戳"""
        try:
            if not timestamp:
                return ""
            
            timestamp_str = str(timestamp)
            if len(timestamp_str) > 20:
                return timestamp_str[:17] + "..."
            return timestamp_str
            
        except Exception as e:
            return str(timestamp)
    
    def _format_stock_code(self, stock_code):
        """格式化股票代码"""
        try:
            if not stock_code:
                return ""
            
            code_str = str(stock_code)
            if len(code_str) > 8:
                return code_str[:8]
            return code_str
            
        except Exception as e:
            return str(stock_code)
    
    def _format_date(self, date_str):
        """格式化日期"""
        try:
            if not date_str:
                return ""
            
            date = str(date_str)
            if len(date) > 10:
                return date[:10]
            return date
            
        except Exception as e:
            return str(date_str)
    
    def update_stats_display(self, stats_text):
        """
        更新统计显示
        
        参数:
            stats_text: 统计文本
        """
        try:
            if self.stats_text:
                self.stats_text.delete(1.0, tk.END)
                self.stats_text.insert(1.0, stats_text)
                self.stats_text.configure(state='disabled')
                
        except Exception as e:
            print(f"[ERROR] 更新统计显示时出错: {str(e)}")
    
    def clear_filter_inputs(self):
        """清除过滤输入框"""
        try:
            if self.stock_filter_var:
                self.stock_filter_var.set("")
            
            if self.date_filter_var:
                self.date_filter_var.set("")
                
        except Exception as e:
            print(f"[ERROR] 清除过滤输入框时出错: {str(e)}")
    
    def get_selected_stock_info(self):
        """
        获取选中的股票信息
        
        返回:
            dict: 选中的股票信息，如果没有选中则返回None
        """
        try:
            selection = self.tree.selection()
            if not selection:
                return None
            
            item = self.tree.item(selection[0])
            values = item['values']
            
            if len(values) >= 4:
                return {
                    'index': values[0],
                    'timestamp': values[1],
                    'stock_code': values[2],
                    'focus_date': values[3]
                }
            
            return None
            
        except Exception as e:
            print(f"[ERROR] 获取选中的股票信息时出错: {str(e)}")
            return None
    
    def resize_columns(self, widths=None):
        """
        调整列宽
        
        参数:
            widths: 列宽列表，格式为[序号宽度, 时间宽度, 代码宽度, 日期宽度]
        """
        try:
            if not self.tree:
                return
            
            # 默认宽度
            if widths is None:
                widths = [40, 120, 60, 80]
            
            # 调整列宽
            for i, width in enumerate(widths, 1):
                self.tree.column(f'#{i}', width=width)
                
        except Exception as e:
            print(f"[ERROR] 调整列宽时出错: {str(e)}")