#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
主窗口
股票K线图查看器的主窗口，负责整合所有组件和协调控制器
"""

import tkinter as tk
from tkinter import ttk
import os
import sys


class StockKLineViewerGUI:
    """股票K线图查看器GUI - 主窗口类"""
    
    def __init__(self):
        # 初始化数据模型
        self._init_data_models()
        
        # 初始化控制器
        self._init_controllers()
        
        # 初始化工具实例
        self._init_tools()
        
        # 初始化状态变量
        self._init_state_variables()
        
        # 创建主窗口
        self._create_main_window()
        
        # 设置样式
        self._setup_styles()
        
        # 初始化UI
        self._init_ui()
        
        # 绑定窗口事件
        self._bind_window_events()
    
    def _init_data_models(self):
        """初始化数据模型"""
        try:
            # 导入数据模型
            from models.stock_data_parser import StockDataParser
            from models.stock_model import StockStats
            
            self.parser = StockDataParser()
            self.stats = StockStats()
            self.data_records = []
            
            print("[INFO] 数据模型初始化完成")
            
        except ImportError as e:
            print(f"[ERROR] 导入数据模型失败: {str(e)}")
            # 创建简化版本的数据模型
            class SimpleDataParser:
                def __init__(self): self.data = []
                def parse(self, file_path): return False, "数据模型加载失败"
                def get_data(self): return []
                def filter_data(self, *args): return []
            
            self.parser = SimpleDataParser()
            self.stats = None
            self.data_records = []
    
    def _init_controllers(self):
        """初始化控制器"""
        try:
            # 导入控制器
            from controllers.file_controller import FileController
            from controllers.filter_controller import FilterController
            from controllers.stock_controller import StockController
            
            self.file_controller = FileController(self)
            self.filter_controller = FilterController(self)
            self.stock_controller = StockController(self)
            
            print("[INFO] 控制器初始化完成")
            
        except ImportError as e:
            print(f"[ERROR] 导入控制器失败: {str(e)}")
            # 创建简化版本的控制器
            class SimpleController:
                def __init__(self, app): self.app = app
                def select_file(self): pass
                def load_file(self): pass
            
            self.file_controller = SimpleController(self)
            self.filter_controller = SimpleController(self)
            self.stock_controller = SimpleController(self)
    
    def _init_tools(self):
        """初始化工具实例"""
        try:
            # 导入工具
            from utils.tdx_tools import TdxTools
            from utils.ths_tools import ThsTools
            
            self.tdx_tools = TdxTools()
            self.ths_tools = ThsTools()
            
            print("[INFO] 工具实例初始化完成")
            
        except ImportError as e:
            print(f"[ERROR] 导入工具实例失败: {str(e)}")
            # 创建简化版本的工具
            class SimpleTools:
                def __init__(self): pass
                def open_tdx(self, *args): return False, "工具加载失败"
                def open_ths(self, *args): return False, "工具加载失败"
            
            self.tdx_tools = SimpleTools()
            self.ths_tools = SimpleTools()
    
    def _init_state_variables(self):
        """初始化状态变量"""
        self.current_file = None
        self.current_stock_code = None
        self.current_focus_date = None
        self.left_panel_visible = True
        self._window_geometry = None
        self._is_maximized = False
        self._resize_timer = None
    
    def _create_main_window(self):
        """创建主窗口"""
        self.root = tk.Tk()
        self.root.title("股票关注日期查看器")
        
        # 设置窗口图标（如果存在）
        self._set_window_icon()
        
        # 设置初始尺寸和位置
        self._set_window_geometry()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 允许窗口调整大小和最大化
        self.root.resizable(True, True)
    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            # 尝试加载图标文件
            icon_paths = [
                "icon.ico",
                "icon.png",
                os.path.join("assets", "icon.ico"),
                os.path.join("assets", "icon.png")
            ]
            
            for path in icon_paths:
                if os.path.exists(path):
                    if path.endswith('.ico'):
                        self.root.iconbitmap(path)
                    elif path.endswith('.png'):
                        icon = tk.PhotoImage(file=path)
                        self.root.iconphoto(True, icon)
                    print(f"[INFO] 已设置窗口图标: {path}")
                    break
                    
        except Exception as e:
            print(f"[WARNING] 设置窗口图标失败: {str(e)}")
    
    def _set_window_geometry(self):
        """设置窗口几何尺寸"""
        try:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 计算窗口尺寸（屏幕的85%）
            width = int(screen_width * 0.85)
            height = int(screen_height * 0.85)
            
            # 计算窗口位置（居中）
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            
            # 设置几何尺寸
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            
            # 保存初始几何信息
            self._window_geometry = f"{width}x{height}+{x}+{y}"
            
            print(f"[INFO] 窗口尺寸设置为: {width}x{height}")
            
        except Exception as e:
            print(f"[WARNING] 设置窗口几何尺寸失败: {str(e)}")
            # 使用默认尺寸
            self.root.geometry("1200x800")
    
    def _setup_styles(self):
        """设置UI样式"""
        try:
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
                           font=('Arial', 9, 'bold'))
            
            style.map("Treeview",
                     background=[('selected', '#3465a4')],
                     foreground=[('selected', 'white')])
            
            # 小字体样式
            style.configure("Tiny.TButton", font=('Arial', 9))
            style.configure("Tiny.TLabel", font=('Arial', 9))
            style.configure("Tiny.TEntry", font=('Arial', 9))
            
            # K线图容器样式
            style.configure("KlineContainer.TFrame", background="#ffffff")
            
            # 状态栏样式
            style.configure("Status.TLabel", 
                          background="#e0e0e0", 
                          foreground="#333333",
                          relief=tk.SUNKEN,
                          font=('Arial', 9))
            
            print("[INFO] UI样式设置完成")
            
        except Exception as e:
            print(f"[ERROR] 设置UI样式时出错: {str(e)}")
    
    def _init_ui(self):
        """初始化用户界面"""
        try:
            # 主容器
            self.main_container = ttk.Frame(self.root)
            self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 创建标题栏
            self._create_header()
            
            # 创建内容区域
            self._create_content_area()
            
            # 创建状态栏
            self._create_status_bar()
            
            # 初始调整
            self.root.after(100, self._initial_adjustment)
            
            print("[INFO] 用户界面初始化完成")
            
        except Exception as e:
            print(f"[ERROR] 初始化用户界面时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _create_header(self):
        """创建标题栏"""
        try:
            # 标题栏框架
            self.header_frame = ttk.Frame(self.main_container)
            self.header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
            
            # 应用标题
            self._create_app_title()
            
            # 左侧面板切换按钮
            self._create_toggle_button()
            
            # 文件选择按钮
            self._create_file_selection()
            
        except Exception as e:
            print(f"[ERROR] 创建标题栏时出错: {str(e)}")
    
    def _create_app_title(self):
        """创建应用标题"""
        self.title_label = ttk.Label(
            self.header_frame,
            text="📈 股票关注日期查看器",
            font=('Arial', 14, 'bold'),
            foreground="#2c3e50"
        )
        self.title_label.pack(side=tk.LEFT, padx=(0, 15))
    
    def _create_toggle_button(self):
        """创建左侧面板切换按钮"""
        self.toggle_button = ttk.Button(
            self.header_frame,
            text="◀",
            width=2,
            command=self._toggle_left_panel
        )
        self.toggle_button.pack(side=tk.LEFT, padx=(0, 10))
    
    def _create_file_selection(self):
        """创建文件选择区域"""
        # 文件路径变量
        self.file_path_var = tk.StringVar()
        self.file_path_var.set("未选择文件")
        
        # 文件选择框架
        file_button_frame = ttk.Frame(self.header_frame)
        file_button_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 选择文件按钮
        select_file_btn = ttk.Button(
            file_button_frame,
            text="选择数据文件",
            command=self._on_select_file,
            style="Tiny.TButton"
        )
        select_file_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 重新加载按钮
        reload_btn = ttk.Button(
            file_button_frame,
            text="重新加载",
            command=self._on_reload_file,
            style="Tiny.TButton"
        )
        reload_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 文件标签
        self.file_label = ttk.Label(
            file_button_frame,
            textvariable=self.file_path_var,
            foreground="#666666",
            font=('Arial', 9)
        )
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _create_content_area(self):
        """创建内容区域"""
        try:
            # 内容容器
            self.content_container = ttk.Frame(self.main_container)
            self.content_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            # 导入视图组件
            from views.left_panel import LeftPanel
            from views.right_panel import RightPanel
            
            # 创建左侧面板
            self.left_panel = LeftPanel(self.content_container, self)
            self.left_frame = self.left_panel.create()
            self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 创建右侧面板
            self.right_panel = RightPanel(self.content_container, self)
            self.right_frame = self.right_panel.create()
            self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
            
        except ImportError as e:
            print(f"[ERROR] 导入视图组件失败: {str(e)}")
            # 创建简单的替代面板
            error_label = tk.Label(
                self.content_container,
                text="界面组件加载失败，请检查views目录",
                font=('Arial', 12),
                foreground="#ff0000"
            )
            error_label.pack(expand=True)
    
    def _create_status_bar(self):
        """创建状态栏"""
        try:
            # 状态栏框架
            self.status_frame = ttk.Frame(self.main_container)
            self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
            
            # 状态标签
            self.status_label = ttk.Label(
                self.status_frame,
                text="就绪 - 请选择数据文件开始使用",
                relief=tk.SUNKEN,
                anchor=tk.W,
                style="Status.TLabel"
            )
            self.status_label.pack(fill=tk.X)
            
            # 版本信息
            version_label = ttk.Label(
                self.status_frame,
                text="v1.0.0",
                relief=tk.SUNKEN,
                anchor=tk.E,
                style="Status.TLabel"
            )
            version_label.pack(side=tk.RIGHT, fill=tk.Y)
            
        except Exception as e:
            print(f"[ERROR] 创建状态栏时出错: {str(e)}")
    
    def _bind_window_events(self):
        """绑定窗口事件"""
        try:
            # 绑定窗口大小变化事件
            self.root.bind('<Configure>', self._on_window_resize)
            
            # 绑定键盘快捷键
            self.root.bind('<Control-o>', lambda e: self._on_select_file())
            self.root.bind('<Control-r>', lambda e: self._on_reload_file())
            self.root.bind('<Control-q>', lambda e: self._on_closing())
            self.root.bind('<F5>', lambda e: self._on_reload_file())
            
            # 绑定ESC键
            self.root.bind('<Escape>', lambda e: self._on_escape_pressed())
            
            print("[INFO] 窗口事件绑定完成")
            
        except Exception as e:
            print(f"[ERROR] 绑定窗口事件时出错: {str(e)}")
    
    def _on_window_resize(self, event):
        """窗口大小变化事件处理"""
        if event.widget == self.root:
            # 检查窗口是否最大化
            current_state = (self.root.state() == 'zoomed')
            if current_state != self._is_maximized:
                self._is_maximized = current_state
                
            # 防抖处理：延迟调整布局
            if self._resize_timer:
                self.root.after_cancel(self._resize_timer)
            self._resize_timer = self.root.after(100, self._adjust_resize_layout)
    
    def _adjust_resize_layout(self):
        """调整窗口大小后的布局"""
        try:
            # 确保左侧面板宽度合适
            if hasattr(self, 'left_panel') and hasattr(self.left_panel, 'tree'):
                # 动态调整列宽
                self.left_panel.tree.column('#1', width=25)  # 序号
                self.left_panel.tree.column('#2', width=60)  # 时间
                self.left_panel.tree.column('#3', width=40)  # 代码
                self.left_panel.tree.column('#4', width=60)  # 日期
                
        except Exception as e:
            print(f"[ERROR] 调整布局时出错: {str(e)}")
    
    def _initial_adjustment(self):
        """初始布局调整"""
        try:
            if hasattr(self, 'left_panel') and hasattr(self.left_panel, 'tree'):
                # 动态调整列宽
                self.left_panel.tree.column('#1', width=25)
                self.left_panel.tree.column('#2', width=60)
                self.left_panel.tree.column('#3', width=40)
                self.left_panel.tree.column('#4', width=60)
                
            print("[INFO] 初始布局调整完成")
            
        except Exception as e:
            print(f"[ERROR] 初始布局调整时出错: {str(e)}")
    
    def _toggle_left_panel(self):
        """切换左侧面板显示/隐藏"""
        try:
            if self.left_panel_visible:
                # 隐藏左侧面板
                self.left_frame.pack_forget()
                self.toggle_button.config(text="▶")
                self.left_panel_visible = False
                
                # 扩展右侧面板
                self.right_frame.pack_forget()
                self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))
            else:
                # 显示左侧面板
                self.right_frame.pack_forget()
                
                # 重新显示左侧面板
                self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                self.toggle_button.config(text="◀")
                
                # 重新显示右侧面板
                self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
                self.left_panel_visible = True
            
            # 更新布局
            self.content_container.update_idletasks()
            
            # 更新状态
            panel_state = "隐藏" if not self.left_panel_visible else "显示"
            self._update_status(f"左侧面板{panel_state}")
            
        except Exception as e:
            print(f"[ERROR] 切换左侧面板时出错: {str(e)}")
            self._update_status("切换面板失败")
    
    def _on_select_file(self):
        """选择文件按钮点击事件"""
        try:
            if hasattr(self, 'file_controller'):
                self.file_controller.select_file()
        except Exception as e:
            print(f"[ERROR] 选择文件时出错: {str(e)}")
            self._update_status("选择文件失败")
    
    def _on_reload_file(self):
        """重新加载文件按钮点击事件"""
        try:
            if hasattr(self, 'file_controller'):
                if hasattr(self.file_controller, 'reload_last_file'):
                    self.file_controller.reload_last_file()
                elif hasattr(self.file_controller, 'load_file'):
                    self.file_controller.load_file()
        except Exception as e:
            print(f"[ERROR] 重新加载文件时出错: {str(e)}")
            self._update_status("重新加载失败")
    
    def _on_escape_pressed(self):
        """ESC键按下事件"""
        try:
            # 如果右侧面板在全屏模式，退出全屏
            if hasattr(self, 'right_panel') and hasattr(self.right_panel, 'is_fullscreen'):
                if self.right_panel.is_fullscreen:
                    self.right_panel._exit_fullscreen()
                    
        except Exception as e:
            print(f"[ERROR] 处理ESC键时出错: {str(e)}")
    
    def _on_closing(self):
        """关闭窗口事件"""
        try:
            # 清理资源
            if hasattr(self, 'stock_controller'):
                self.stock_controller.close_kline_viewer()
            
            # 关闭窗口
            self.root.destroy()
            
            # 退出程序
            sys.exit(0)
            
        except Exception as e:
            print(f"[ERROR] 关闭窗口时出错: {str(e)}")
            self.root.destroy()
            sys.exit(1)
    
    def _update_status(self, message):
        """更新状态显示"""
        try:
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text=message)
        except Exception as e:
            print(f"[ERROR] 更新状态时出错: {str(e)}")
    
    def run(self):
        """运行应用程序"""
        try:
            print("[INFO] 启动股票K线图查看器")
            print("[INFO] 版本: 1.0.0")
            print("[INFO] 作者: 股票分析工具")
            print("[INFO] 快捷键:")
            print("  Ctrl+O: 打开文件")
            print("  Ctrl+R: 重新加载")
            print("  F5: 刷新")
            print("  Ctrl+Q: 退出")
            print("  ESC: 退出全屏")
            print("-" * 50)
            
            self.root.mainloop()
            
        except Exception as e:
            print(f"[FATAL] 应用程序运行错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 以下是一些便捷方法，供控制器调用
    
    def get_root(self):
        """获取根窗口"""
        return self.root
    
    def get_status_label(self):
        """获取状态标签"""
        return self.status_label if hasattr(self, 'status_label') else None
    
    def get_file_info_label(self):
        """获取文件信息标签"""
        if hasattr(self, 'left_panel') and hasattr(self.left_panel, 'file_info_label'):
            return self.left_panel.file_info_label
        return None
    
    def get_stats_text_widget(self):
        """获取统计文本部件"""
        if hasattr(self, 'left_panel') and hasattr(self.left_panel, 'stats_text'):
            return self.left_panel.stats_text
        return None
    
    def get_tree_widget(self):
        """获取树形部件"""
        if hasattr(self, 'left_panel') and hasattr(self.left_panel, 'tree'):
            return self.left_panel.tree
        return None
    
    def get_filter_vars(self):
        """获取过滤变量"""
        if hasattr(self, 'left_panel'):
            if hasattr(self.left_panel, 'stock_filter_var') and hasattr(self.left_panel, 'date_filter_var'):
                return (self.left_panel.stock_filter_var, self.left_panel.date_filter_var)
        return (None, None)
    
    def get_kline_container(self):
        """获取K线图容器"""
        if hasattr(self, 'right_panel') and hasattr(self.right_panel, 'kline_container'):
            return self.right_panel.kline_container
        return None
    
    def get_tdx_button(self):
        """获取通达信按钮"""
        if hasattr(self, 'right_panel') and hasattr(self.right_panel, 'tdx_button'):
            return self.right_panel.tdx_button
        return None
    
    def get_ths_button(self):
        """获取同花顺按钮"""
        if hasattr(self, 'right_panel') and hasattr(self.right_panel, 'ths_button'):
            return self.right_panel.ths_button
        return None
    
    def update_file_display(self, filename, records_count=None):
        """更新文件显示"""
        try:
            if not filename:
                return
            
            # 截断过长的文件名
            display_name = filename
            if len(filename) > 30:
                display_name = filename[:15] + "..." + filename[-12:]
            
            # 更新文件路径变量
            if hasattr(self, 'file_path_var'):
                self.file_path_var.set(display_name)
            
            # 更新左侧面板的文件信息
            if hasattr(self, 'left_panel') and hasattr(self.left_panel, 'file_info_label'):
                short_name = os.path.basename(filename) if filename else "无"
                if len(short_name) > 12:
                    short_name = short_name[:9] + "..."
                self.left_panel.file_info_label.config(text=short_name)
            
            # 更新状态
            if records_count is not None:
                self._update_status(f"文件加载完成: {records_count} 条记录")
            
        except Exception as e:
            print(f"[ERROR] 更新文件显示时出错: {str(e)}")
    
    def get_app_info(self):
        """获取应用程序信息"""
        info = {
            'version': '1.0.0',
            'python_version': sys.version,
            'platform': sys.platform,
            'current_file': self.current_file,
            'current_stock': self.current_stock_code,
            'data_records': len(self.data_records) if hasattr(self, 'data_records') else 0,
            'left_panel_visible': self.left_panel_visible,
            'window_maximized': self._is_maximized
        }
        return info


def main():
    """主函数（用于独立测试）"""
    try:
        app = StockKLineViewerGUI()
        app.run()
    except Exception as e:
        print(f"[FATAL] 应用程序启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...")


if __name__ == '__main__':
    main()