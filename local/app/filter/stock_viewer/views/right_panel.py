#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
右侧面板
创建和管理右侧面板，包括K线图显示区域和工具按钮
"""

import tkinter as tk
from tkinter import ttk
import os


class RightPanel:
    """右侧面板 - 管理K线图显示区域和工具按钮"""
    
    def __init__(self, parent, controller):
        """
        初始化右侧面板
        
        参数:
            parent: 父容器
            controller: 主控制器实例
        """
        self.parent = parent
        self.controller = controller
        self.frame = None
        self.kline_frame = None
        self.kline_container = None
        self.tdx_button = None
        self.ths_button = None
        self.export_button = None
        self.fullscreen_button = None
        self.is_fullscreen = False
        self.original_geometry = None
        
        # 创建右侧面板
        self.create()
    
    def create(self):
        """创建右侧面板"""
        try:
            # 创建主框架
            self.frame = ttk.Frame(self.parent)
            
            # 创建工具按钮区域
            self._create_tool_buttons()
            
            # 创建K线图容器
            self._create_kline_container()
            
            # 绑定事件
            self._bind_events()
            
            print("[INFO] 右侧面板创建完成")
            return self.frame
            
        except Exception as e:
            print(f"[ERROR] 创建右侧面板时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_tool_buttons(self):
        """创建工具按钮区域"""
        try:
            # 工具按钮容器
            tool_frame = ttk.Frame(self.frame, height=40)
            tool_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
            
            # 按钮容器左侧
            left_button_frame = ttk.Frame(tool_frame)
            left_button_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 通达信按钮
            self.tdx_button = ttk.Button(
                left_button_frame,
                text="通达信",
                state='disabled',
                command=self._on_tdx_click,
                style="Tiny.TButton",
                width=8
            )
            self.tdx_button.pack(side=tk.LEFT, padx=(0, 5))
            
            # 同花顺按钮
            self.ths_button = ttk.Button(
                left_button_frame,
                text="同花顺",
                state='disabled',
                command=self._on_ths_click,
                style="Tiny.TButton",
                width=8
            )
            self.ths_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # 按钮容器右侧
            right_button_frame = ttk.Frame(tool_frame)
            right_button_frame.pack(side=tk.RIGHT, fill=tk.X)
            
            # 导出按钮
            self.export_button = ttk.Button(
                right_button_frame,
                text="导出",
                state='disabled',
                command=self._on_export_click,
                style="Tiny.TButton",
                width=6
            )
            self.export_button.pack(side=tk.LEFT, padx=(0, 5))
            
            # 全屏按钮
            self.fullscreen_button = ttk.Button(
                right_button_frame,
                text="全屏",
                command=self._on_fullscreen_click,
                style="Tiny.TButton",
                width=6
            )
            self.fullscreen_button.pack(side=tk.LEFT)
            
            # 分隔线
            separator = ttk.Separator(tool_frame, orient=tk.HORIZONTAL)
            separator.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
            
        except Exception as e:
            print(f"[ERROR] 创建工具按钮时出错: {str(e)}")
    
    def _create_kline_container(self):
        """创建K线图容器"""
        try:
            # K线图框架
            self.kline_frame = ttk.LabelFrame(
                self.frame,
                text="K线图",
                padding="5"
            )
            self.kline_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # 创建内部容器
            self.kline_container = ttk.Frame(self.kline_frame)
            self.kline_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # 设置容器背景色
            self.kline_container.configure(style="KlineContainer.TFrame")
            
            # 初始提示
            self._show_initial_tip()
            
        except Exception as e:
            print(f"[ERROR] 创建K线图容器时出错: {str(e)}")
    
    def _show_initial_tip(self):
        """显示初始提示"""
        try:
            tip_frame = ttk.Frame(self.kline_container)
            tip_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # 主提示
            main_label = tk.Label(
                tip_frame,
                text="双击左侧表格查看K线图",
                font=('Arial', 12),
                foreground="#666666"
            )
            main_label.pack(pady=(0, 10))
            
            # 次要提示
            sub_label = tk.Label(
                tip_frame,
                text="选择数据文件后，双击任意股票行查看详细K线图",
                font=('Arial', 9),
                foreground="#888888"
            )
            sub_label.pack()
            
            # 图标提示（可选）
            icon_label = tk.Label(
                tip_frame,
                text="📈",
                font=('Arial', 24),
                foreground="#4a6fa5"
            )
            icon_label.pack(pady=(10, 0))
            
        except Exception as e:
            print(f"[ERROR] 显示初始提示时出错: {str(e)}")
    
    def _bind_events(self):
        """绑定事件"""
        try:
            # 绑定K线图容器大小变化事件
            self.kline_container.bind('<Configure>', self._on_container_resize)
            
            # 绑定鼠标滚轮事件
            self.kline_container.bind('<MouseWheel>', self._on_mouse_wheel)
            self.kline_container.bind('<Button-4>', self._on_mouse_wheel)  # Linux
            self.kline_container.bind('<Button-5>', self._on_mouse_wheel)  # Linux
            
        except Exception as e:
            print(f"[ERROR] 绑定事件时出错: {str(e)}")
    
    def _on_tdx_click(self):
        """通达信按钮点击事件"""
        try:
            print("[INFO] 点击通达信按钮")
            
            # 禁用按钮防止重复点击
            self.tdx_button.config(state='disabled')
            self.tdx_button.config(text="打开中...")
            
            # 调用控制器打开通达信
            if hasattr(self.controller, 'stock_controller'):
                self.controller.stock_controller.open_tdx()
            
            # 恢复按钮状态
            self.app.root.after(2000, self._restore_tdx_button)
            
        except Exception as e:
            print(f"[ERROR] 通达信按钮点击时出错: {str(e)}")
            self._restore_tdx_button()
    
    def _restore_tdx_button(self):
        """恢复通达信按钮状态"""
        try:
            if self.tdx_button and self.tdx_button.winfo_exists():
                self.tdx_button.config(text="通达信")
                # 只在有股票选中时才启用
                if hasattr(self.controller, 'stock_controller'):
                    if self.controller.stock_controller.current_stock_code:
                        self.tdx_button.config(state='normal')
        except Exception as e:
            print(f"[ERROR] 恢复通达信按钮时出错: {str(e)}")
    
    def _on_ths_click(self):
        """同花顺按钮点击事件"""
        try:
            print("[INFO] 点击同花顺按钮")
            
            # 禁用按钮防止重复点击
            self.ths_button.config(state='disabled')
            self.ths_button.config(text="打开中...")
            
            # 调用控制器打开同花顺
            if hasattr(self.controller, 'stock_controller'):
                self.controller.stock_controller.open_ths()
            
            # 恢复按钮状态
            self.app.root.after(2000, self._restore_ths_button)
            
        except Exception as e:
            print(f"[ERROR] 同花顺按钮点击时出错: {str(e)}")
            self._restore_ths_button()
    
    def _restore_ths_button(self):
        """恢复同花顺按钮状态"""
        try:
            if self.ths_button and self.ths_button.winfo_exists():
                self.ths_button.config(text="同花顺")
                # 只在有股票选中时才启用
                if hasattr(self.controller, 'stock_controller'):
                    if self.controller.stock_controller.current_stock_code:
                        self.ths_button.config(state='normal')
        except Exception as e:
            print(f"[ERROR] 恢复同花顺按钮时出错: {str(e)}")
    
    def _on_export_click(self):
        """导出按钮点击事件"""
        try:
            print("[INFO] 点击导出按钮")
            
            if hasattr(self.controller, 'stock_controller'):
                # 弹出导出选项菜单
                self._show_export_menu()
            
        except Exception as e:
            print(f"[ERROR] 导出按钮点击时出错: {str(e)}")
            import tkinter as tk
            tk.messagebox.showerror("错误", f"导出时出错:\n{str(e)}")
    
    def _show_export_menu(self):
        """显示导出菜单"""
        try:
            import tkinter as tk
            
            # 创建菜单
            menu = tk.Menu(self.export_button, tearoff=0)
            
            # 添加导出选项
            menu.add_command(
                label="导出K线图 (PNG)",
                command=lambda: self._export_kline_chart('png')
            )
            menu.add_command(
                label="导出K线图 (JPEG)",
                command=lambda: self._export_kline_chart('jpg')
            )
            menu.add_command(
                label="导出K线图 (PDF)",
                command=lambda: self._export_kline_chart('pdf')
            )
            
            menu.add_separator()
            
            menu.add_command(
                label="导出股票数据 (CSV)",
                command=lambda: self._export_stock_data('csv')
            )
            menu.add_command(
                label="导出股票数据 (TXT)",
                command=lambda: self._export_stock_data('txt')
            )
            
            # 显示菜单
            x = self.export_button.winfo_rootx()
            y = self.export_button.winfo_rooty() + self.export_button.winfo_height()
            menu.tk_popup(x, y)
            
        except Exception as e:
            print(f"[ERROR] 显示导出菜单时出错: {str(e)}")
    
    def _export_kline_chart(self, export_format):
        """导出K线图"""
        try:
            if hasattr(self.controller, 'stock_controller'):
                success = self.controller.stock_controller.export_kline_chart(export_format)
                
                if success:
                    # 更新状态
                    if hasattr(self.controller, 'get_status_label'):
                        status_label = self.controller.get_status_label()
                        if status_label:
                            status_label.config(text=f"K线图已导出为 {export_format.upper()} 格式")
                    
                    print(f"[INFO] K线图导出成功: {export_format}")
            
        except Exception as e:
            print(f"[ERROR] 导出K线图时出错: {str(e)}")
            import tkinter as tk
            tk.messagebox.showerror("错误", f"导出K线图时出错:\n{str(e)}")
    
    def _export_stock_data(self, export_format):
        """导出股票数据"""
        try:
            if hasattr(self.controller, 'file_controller'):
                success = self.controller.file_controller.export_data(export_format)
                
                if success:
                    print(f"[INFO] 股票数据导出成功: {export_format}")
            
        except Exception as e:
            print(f"[ERROR] 导出股票数据时出错: {str(e)}")
            import tkinter as tk
            tk.messagebox.showerror("错误", f"导出股票数据时出错:\n{str(e)}")
    
    def _on_fullscreen_click(self):
        """全屏按钮点击事件"""
        try:
            if not self.is_fullscreen:
                # 进入全屏模式
                self._enter_fullscreen()
            else:
                # 退出全屏模式
                self._exit_fullscreen()
            
        except Exception as e:
            print(f"[ERROR] 全屏按钮点击时出错: {str(e)}")
    
    def _enter_fullscreen(self):
        """进入全屏模式"""
        try:
            # 保存原始几何信息
            if hasattr(self.controller, 'root'):
                self.original_geometry = self.controller.root.geometry()
            
            # 隐藏左侧面板
            if hasattr(self.controller, 'left_panel') and hasattr(self.controller.left_panel, 'frame'):
                self.controller.left_panel.frame.pack_forget()
            
            # 隐藏标题栏
            if hasattr(self.controller, 'toggle_button'):
                self.controller.toggle_button.pack_forget()
            
            # 隐藏文件选择区域
            if hasattr(self.controller, 'file_label'):
                self.controller.file_label.pack_forget()
            
            # 最大化窗口
            if hasattr(self.controller, 'root'):
                self.controller.root.state('zoomed')
            
            # 更新按钮文本
            self.fullscreen_button.config(text="退出全屏")
            self.is_fullscreen = True
            
            # 更新状态
            if hasattr(self.controller, 'get_status_label'):
                status_label = self.controller.get_status_label()
                if status_label:
                    status_label.config(text="全屏模式 - 按ESC键或点击'退出全屏'按钮退出")
            
            # 绑定ESC键退出全屏
            if hasattr(self.controller, 'root'):
                self.controller.root.bind('<Escape>', lambda e: self._exit_fullscreen())
            
            print("[INFO] 进入全屏模式")
            
        except Exception as e:
            print(f"[ERROR] 进入全屏模式时出错: {str(e)}")
    
    def _exit_fullscreen(self):
        """退出全屏模式"""
        try:
            # 恢复原始几何信息
            if hasattr(self.controller, 'root') and self.original_geometry:
                self.controller.root.geometry(self.original_geometry)
                self.controller.root.state('normal')
            
            # 显示左侧面板
            if hasattr(self.controller, 'left_panel') and hasattr(self.controller.left_panel, 'frame'):
                self.controller.left_panel.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 显示标题栏
            if hasattr(self.controller, 'toggle_button'):
                self.controller.toggle_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # 显示文件选择区域
            if hasattr(self.controller, 'file_label'):
                self.controller.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 更新按钮文本
            self.fullscreen_button.config(text="全屏")
            self.is_fullscreen = False
            
            # 更新状态
            if hasattr(self.controller, 'get_status_label'):
                status_label = self.controller.get_status_label()
                if status_label:
                    status_label.config(text="已退出全屏模式")
            
            # 解绑ESC键
            if hasattr(self.controller, 'root'):
                self.controller.root.unbind('<Escape>')
            
            print("[INFO] 退出全屏模式")
            
        except Exception as e:
            print(f"[ERROR] 退出全屏模式时出错: {str(e)}")
    
    def _on_container_resize(self, event):
        """容器大小变化事件"""
        try:
            # 当容器大小变化时，可以调整K线图大小
            if hasattr(self, 'current_kline_viewer') and self.current_kline_viewer:
                if hasattr(self.current_kline_viewer, 'canvas'):
                    canvas = self.current_kline_viewer.canvas
                    if canvas:
                        canvas_widget = canvas.get_tk_widget()
                        # 这里可以添加调整K线图大小的逻辑
            
        except Exception as e:
            # 忽略resize事件中的小错误
            pass
    
    def _on_mouse_wheel(self, event):
        """鼠标滚轮事件"""
        try:
            # 这里可以添加鼠标滚轮缩放K线图的逻辑
            # 暂时只记录事件
            pass
            
        except Exception as e:
            print(f"[ERROR] 处理鼠标滚轮事件时出错: {str(e)}")
    
    def clear_kline_container(self):
        """
        清空K线图容器
        
        返回:
            bool: 操作是否成功
        """
        try:
            if self.kline_container:
                # 清除所有子部件
                for widget in self.kline_container.winfo_children():
                    widget.destroy()
                
                print("[INFO] K线图容器已清空")
                return True
            return False
            
        except Exception as e:
            print(f"[ERROR] 清空K线图容器时出错: {str(e)}")
            return False
    
    def show_loading_indicator(self, stock_code):
        """
        显示加载指示器
        
        参数:
            stock_code: 股票代码
            
        返回:
            tk.Widget: 加载指示器部件
        """
        try:
            if not self.kline_container:
                return None
            
            # 清除现有内容
            self.clear_kline_container()
            
            # 创建加载指示器
            loading_frame = ttk.Frame(self.kline_container)
            loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # 加载文本
            loading_label = tk.Label(
                loading_frame,
                text=f"正在加载 {stock_code} 的K线图...",
                font=('Arial', 12),
                foreground="#4a6fa5"
            )
            loading_label.pack(pady=(0, 10))
            
            # 加载动画（简单的点动画）
            dot_frame = ttk.Frame(loading_frame)
            dot_frame.pack()
            
            dots = []
            for i in range(3):
                dot = tk.Label(
                    dot_frame,
                    text=".",
                    font=('Arial', 20),
                    foreground="#4a6fa5"
                )
                dot.pack(side=tk.LEFT, padx=2)
                dots.append(dot)
            
            # 动画效果
            def animate_dots(index=0):
                if loading_frame and loading_frame.winfo_exists():
                    for i, dot in enumerate(dots):
                        if i == index % 3:
                            dot.config(font=('Arial', 24, 'bold'))
                        else:
                            dot.config(font=('Arial', 20, 'normal'))
                    
                    # 下一帧
                    if hasattr(self, 'app') and hasattr(self.app, 'root'):
                        self.app.root.after(300, lambda: animate_dots((index + 1) % 3))
            
            # 开始动画
            if hasattr(self, 'app') and hasattr(self.app, 'root'):
                self.app.root.after(100, lambda: animate_dots())
            
            print(f"[INFO] 显示加载指示器: {stock_code}")
            return loading_frame
            
        except Exception as e:
            print(f"[ERROR] 显示加载指示器时出错: {str(e)}")
            return None
    
    def show_error_message(self, message, retry_callback=None):
        """
        显示错误信息
        
        参数:
            message: 错误信息
            retry_callback: 重试回调函数
            
        返回:
            tk.Widget: 错误信息部件
        """
        try:
            if not self.kline_container:
                return None
            
            # 清除现有内容
            self.clear_kline_container()
            
            # 创建错误信息框架
            error_frame = ttk.Frame(self.kline_container)
            error_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # 错误图标
            icon_label = tk.Label(
                error_frame,
                text="⚠️",
                font=('Arial', 36),
                foreground="#ff9900"
            )
            icon_label.pack(pady=(0, 10))
            
            # 错误信息
            error_label = tk.Label(
                error_frame,
                text=message,
                font=('Arial', 10),
                foreground="#ff0000",
                wraplength=300,
                justify=tk.CENTER
            )
            error_label.pack(pady=(0, 20))
            
            # 重试按钮（如果提供了回调函数）
            if retry_callback:
                retry_button = tk.Button(
                    error_frame,
                    text="重试",
                    command=retry_callback,
                    font=('Arial', 9),
                    width=10
                )
                retry_button.pack()
            
            print(f"[INFO] 显示错误信息: {message}")
            return error_frame
            
        except Exception as e:
            print(f"[ERROR] 显示错误信息时出错: {str(e)}")
            return None
    
    def update_kline_title(self, stock_code, focus_date=None):
        """
        更新K线图标题
        
        参数:
            stock_code: 股票代码
            focus_date: 关注日期
        """
        try:
            if self.kline_frame:
                title = f"K线图 - {stock_code}"
                if focus_date:
                    title += f" (关注日期: {focus_date})"
                self.kline_frame.config(text=title)
                
                print(f"[INFO] 更新K线图标题: {title}")
                
        except Exception as e:
            print(f"[ERROR] 更新K线图标题时出错: {str(e)}")
    
    def enable_external_buttons(self, enable=True):
        """
        启用/禁用外部软件按钮
        
        参数:
            enable: 是否启用
        """
        try:
            state = 'normal' if enable else 'disabled'
            
            if self.tdx_button:
                self.tdx_button.config(state=state)
            
            if self.ths_button:
                self.ths_button.config(state=state)
            
            if self.export_button:
                self.export_button.config(state=state)
            
            print(f"[INFO] 外部按钮状态: {'启用' if enable else '禁用'}")
            
        except Exception as e:
            print(f"[ERROR] 设置外部按钮状态时出错: {str(e)}")