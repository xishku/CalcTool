#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
股票控制器
处理股票相关的所有操作，包括K线图显示、外部软件集成和股票数据处理
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import threading
import time


class StockController:
    """股票控制器 - 处理股票相关操作"""
    
    def __init__(self, app):
        """
        初始化股票控制器
        
        参数:
            app: 主应用程序实例
        """
        self.app = app
        self.current_kline_viewer = None
        self.current_stock_code = None
        self.current_focus_date = None
        self.kline_history = []
        self.max_kline_history = 5
        
    def on_stock_selected(self, stock_code, focus_date_str, timestamp=None):
        """
        股票被选中时的处理（从表格双击触发）
        
        参数:
            stock_code: 股票代码
            focus_date_str: 关注日期字符串 (YYYYMMDD格式)
            timestamp: 可选的时间戳
            
        返回:
            bool: 处理是否成功
        """
        try:
            # 验证输入参数
            if not stock_code or not focus_date_str:
                messagebox.showwarning("警告", "股票代码和关注日期不能为空")
                return False
            
            # 验证股票代码格式
            if not self._validate_stock_code(stock_code):
                messagebox.showerror("错误", f"无效的股票代码格式: {stock_code}")
                return False
            
            # 验证日期格式
            if not self._validate_date_format(focus_date_str):
                messagebox.showerror("错误", f"无效的日期格式: {focus_date_str}\n应为YYYYMMDD格式")
                return False
            
            # 保存当前选择
            self.current_stock_code = stock_code
            self.current_focus_date = focus_date_str
            
            # 添加到历史记录
            self._add_to_history(stock_code, focus_date_str, timestamp)
            
            # 启用外部软件按钮
            self._enable_external_buttons()
            
            # 显示K线图
            success = self.show_kline(stock_code, focus_date_str)
            
            if success:
                # 更新状态
                self._update_status(f"已选中 {stock_code}，关注日期: {focus_date_str}")
                
                # 记录操作
                self._log_stock_selection(stock_code, focus_date_str, "成功")
                
                return True
            else:
                self._log_stock_selection(stock_code, focus_date_str, "失败")
                return False
                
        except Exception as e:
            error_msg = f"选择股票时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            self._log_stock_selection(stock_code, focus_date_str, f"异常: {str(e)}")
            return False
    
    def show_kline(self, stock_code, focus_date_str):
        """
        显示K线图
        
        参数:
            stock_code: 股票代码
            focus_date_str: 关注日期字符串
            
        返回:
            bool: K线图显示是否成功
        """
        try:
            # 更新状态
            self._update_status(f"正在加载 {stock_code} 的K线图，关注日期: {focus_date_str}")
            
            # 获取K线图容器
            kline_container = self.app.get_kline_container()
            if not kline_container:
                messagebox.showerror("错误", "K线图容器未找到")
                return False
            
            # 清除现有的K线图
            self._clear_kline_container(kline_container)
            
            # 显示加载提示
            loading_label = self._show_loading_indicator(kline_container, stock_code)
            
            # 在后台线程中创建K线图
            def create_kline_in_background():
                try:
                    # 计算日期范围
                    start_date, end_date = self._calculate_date_range(focus_date_str)
                    
                    # 导入K线图模块
                    kline_viewer = self._import_kline_viewer()
                    
                    if kline_viewer is None:
                        # 如果导入失败，在主线程中显示错误
                        self.app.root.after(0, lambda: self._show_kline_error(
                            kline_container, loading_label, "K线图模块加载失败"))
                        return
                    
                    # 创建K线图查看器
                    kline_instance = kline_viewer(
                        parent=kline_container,
                        stock_code=stock_code,
                        start_date=start_date,
                        end_date=end_date,
                        target_date=focus_date_str,
                        is_embedded=True
                    )
                    
                    # 显示嵌入的K线图
                    success = kline_instance.show_embedded(kline_container)
                    
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self._update_kline_ui(
                        success, stock_code, focus_date_str, kline_instance, 
                        kline_container, loading_label))
                    
                except Exception as e:
                    # 在主线程中显示错误
                    self.app.root.after(0, lambda: self._show_kline_error(
                        kline_container, loading_label, f"创建K线图时出错: {str(e)[:50]}"))
            
            # 启动后台线程
            thread = threading.Thread(target=create_kline_in_background, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            error_msg = f"显示K线图时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            self._update_status(f"K线图加载失败: {stock_code}")
            return False
    
    def open_tdx(self):
        """
        打开通达信并自动定位到当前股票
        
        返回:
            bool: 操作是否成功
        """
        try:
            if not self.current_stock_code:
                messagebox.showinfo("提示", "请先选择股票")
                return False
            
            stock_code = self.current_stock_code
            
            # 设置状态标签
            if hasattr(self.app, 'tdx_tools'):
                self.app.tdx_tools.status_label = self.app.get_status_label()
            
            # 调用通达信工具
            success, message = self.app.tdx_tools.open_tdx(stock_code, self.app.get_status_label())
            
            if success:
                self._log_external_app_action("通达信", stock_code, "成功")
                return True
            else:
                self._log_external_app_action("通达信", stock_code, f"失败: {message}")
                
                # 即使失败也尝试显示友好提示
                padded_code = stock_code.zfill(6)
                self._update_status(f"请手动在通达信中输入 {padded_code}")
                
                messagebox.showinfo("提示", 
                    f"无法自动打开通达信\n"
                    f"请手动打开通达信，然后输入股票代码: {padded_code}")
                return False
                
        except Exception as e:
            error_msg = f"打开通达信时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            self._log_external_app_action("通达信", self.current_stock_code or "未知", f"异常: {str(e)}")
            return False
    
    def open_ths(self):
        """
        打开同花顺并自动定位到当前股票
        
        返回:
            bool: 操作是否成功
        """
        try:
            if not self.current_stock_code:
                messagebox.showinfo("提示", "请先选择股票")
                return False
            
            stock_code = self.current_stock_code
            
            # 设置状态标签
            if hasattr(self.app, 'ths_tools'):
                self.app.ths_tools.status_label = self.app.get_status_label()
            
            # 调用同花顺工具
            success, message = self.app.ths_tools.open_ths(stock_code, self.app.get_status_label())
            
            if success:
                self._log_external_app_action("同花顺", stock_code, "成功")
                return True
            else:
                self._log_external_app_action("同花顺", stock_code, f"失败: {message}")
                
                # 即使失败也尝试显示友好提示
                padded_code = stock_code.zfill(6)
                self._update_status(f"请手动在同花顺中输入 {padded_code}")
                
                messagebox.showinfo("提示", 
                    f"无法自动打开同花顺\n"
                    f"请手动打开同花顺，然后输入股票代码: {padded_code}")
                return False
                
        except Exception as e:
            error_msg = f"打开同花顺时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            self._log_external_app_action("同花顺", self.current_stock_code or "未知", f"异常: {str(e)}")
            return False
    
    def close_kline_viewer(self):
        """关闭当前的K线图查看器"""
        try:
            if self.current_kline_viewer:
                self.current_kline_viewer.close()
                self.current_kline_viewer = None
                print("[INFO] K线图查看器已关闭")
        except Exception as e:
            print(f"[ERROR] 关闭K线图查看器时出错: {str(e)}")
    
    def get_current_stock_info(self):
        """
        获取当前股票信息
        
        返回:
            dict: 当前股票信息字典
        """
        info = {
            'stock_code': self.current_stock_code,
            'focus_date': self.current_focus_date,
            'has_kline': self.current_kline_viewer is not None,
            'history_count': len(self.kline_history)
        }
        
        if self.current_stock_code:
            info['stock_code_padded'] = self.current_stock_code.zfill(6)
        
        return info
    
    def get_kline_history(self, limit=5):
        """
        获取K线图历史记录
        
        参数:
            limit: 限制返回的记录数
            
        返回:
            list: K线图历史记录列表
        """
        return self.kline_history[-limit:] if self.kline_history else []
    
    def navigate_kline_history(self, direction='prev'):
        """
        导航K线图历史记录
        
        参数:
            direction: 导航方向 ('prev' 或 'next')
            
        返回:
            bool: 导航是否成功
        """
        try:
            if not self.kline_history:
                messagebox.showinfo("提示", "没有历史记录")
                return False
            
            # 这里可以实现历史记录导航逻辑
            # 由于时间关系，这里只提供基本框架
            messagebox.showinfo("提示", f"导航功能开发中，方向: {direction}")
            return False
            
        except Exception as e:
            error_msg = f"导航历史记录时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def export_kline_chart(self, export_format='png', file_path=None):
        """
        导出K线图
        
        参数:
            export_format: 导出格式 ('png', 'jpg', 'pdf')
            file_path: 导出文件路径
            
        返回:
            bool: 导出是否成功
        """
        try:
            if not self.current_kline_viewer:
                messagebox.showinfo("提示", "没有可导出的K线图")
                return False
            
            if not hasattr(self.current_kline_viewer, 'fig'):
                messagebox.showinfo("提示", "K线图没有图形对象")
                return False
            
            if not file_path:
                # 弹出保存对话框
                default_name = f"kline_{self.current_stock_code}_{self.current_focus_date}.{export_format}"
                file_path = filedialog.asksaveasfilename(
                    title="导出K线图",
                    defaultextension=f".{export_format}",
                    filetypes=[
                        ("PNG图片", "*.png"),
                        ("JPEG图片", "*.jpg"),
                        ("PDF文档", "*.pdf")
                    ],
                    initialfile=default_name
                )
            
            if not file_path:
                return False  # 用户取消了保存
            
            # 导出图形
            self.current_kline_viewer.fig.savefig(
                file_path,
                dpi=300,
                bbox_inches='tight',
                format=export_format
            )
            
            # 更新状态
            self._update_status(f"K线图已导出: {os.path.basename(file_path)}")
            
            # 记录操作
            print(f"[INFO] K线图已导出: {file_path}")
            
            return True
            
        except Exception as e:
            error_msg = f"导出K线图时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def _validate_stock_code(self, stock_code):
        """验证股票代码格式"""
        if not stock_code or not isinstance(stock_code, str):
            return False
        
        # 清理空格
        code = stock_code.strip()
        
        # 检查是否为数字
        if not code.isdigit():
            return False
        
        # 检查长度（A股通常为6位，但允许1-8位）
        if len(code) < 1 or len(code) > 8:
            return False
        
        return True
    
    def _validate_date_format(self, date_str):
        """验证日期格式是否为YYYYMMDD"""
        if not date_str or not isinstance(date_str, str):
            return False
        
        if len(date_str) != 8 or not date_str.isdigit():
            return False
        
        try:
            datetime.strptime(date_str, "%Y%m%d")
            return True
        except ValueError:
            return False
    
    def _calculate_date_range(self, focus_date_str, days_before=15, days_after=15):
        """计算日期范围"""
        try:
            focus_date = datetime.strptime(focus_date_str, "%Y%m%d")
            
            start_date = (focus_date - timedelta(days=days_before)).strftime("%Y%m%d")
            end_date = (focus_date + timedelta(days=days_after)).strftime("%Y%m%d")
            
            return start_date, end_date
            
        except Exception as e:
            # 如果计算失败，返回默认范围
            print(f"[WARNING] 计算日期范围失败，使用默认值: {str(e)}")
            default_start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            default_end = datetime.now().strftime("%Y%m%d")
            return default_start, default_end
    
    def _import_kline_viewer(self):
        """导入K线图查看器模块"""
        try:
            # 尝试从项目根目录导入
            import sys
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, project_root)
            
            from kline_viewer_optimized import KLineViewerOptimized
            return KLineViewerOptimized
            
        except ImportError as e:
            print(f"[ERROR] 导入K线图模块失败: {str(e)}")
            
            # 尝试创建简化的替代类
            try:
                class SimpleKLineViewer:
                    def __init__(self, parent=None, stock_code='000001', 
                               start_date='20230101', end_date='20231231', 
                               target_date=None, is_embedded=False):
                        self.parent = parent
                        self.stock_code = stock_code
                        self.start_date = start_date
                        self.end_date = end_date
                        self.target_date = target_date
                        self.is_embedded = is_embedded
                        self.canvas = None
                        self.fig = None
                    
                    def show_embedded(self, container):
                        import tkinter as tk
                        label = tk.Label(container, 
                                       text=f"{self.stock_code} K线图\n(演示模式)",
                                       font=('Arial', 12),
                                       foreground="#666666")
                        label.pack(expand=True)
                        
                        # 添加详细信息
                        info_label = tk.Label(container,
                                            text=f"关注日期: {self.target_date}\n"
                                                 f"日期范围: {self.start_date} 到 {self.end_date}",
                                            font=('Arial', 10))
                        info_label.pack(pady=10)
                        
                        return True
                    
                    def close(self):
                        pass
                
                return SimpleKLineViewer
                
            except Exception as inner_e:
                print(f"[ERROR] 创建简化K线图类失败: {str(inner_e)}")
                return None
    
    def _clear_kline_container(self, container):
        """清空K线图容器"""
        try:
            if container:
                for widget in container.winfo_children():
                    widget.destroy()
        except Exception as e:
            print(f"[ERROR] 清空K线图容器时出错: {str(e)}")
    
    def _show_loading_indicator(self, container, stock_code):
        """显示加载指示器"""
        try:
            loading_frame = tk.Frame(container)
            loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            loading_label = tk.Label(loading_frame,
                                   text=f"正在加载 {stock_code} 的K线图...",
                                   font=('Arial', 12),
                                   foreground="#666666")
            loading_label.pack()
            
            return loading_frame
            
        except Exception as e:
            print(f"[ERROR] 显示加载指示器时出错: {str(e)}")
            return None
    
    def _show_kline_error(self, container, loading_label, error_message):
        """显示K线图错误"""
        try:
            # 移除加载指示器
            if loading_label and loading_label.winfo_exists():
                loading_label.destroy()
            
            # 显示错误信息
            error_frame = tk.Frame(container)
            error_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            error_label = tk.Label(error_frame,
                                 text=f"K线图加载失败\n{error_message}",
                                 font=('Arial', 10),
                                 foreground="#ff0000")
            error_label.pack()
            
            # 添加重试按钮
            retry_button = tk.Button(error_frame,
                                   text="重试",
                                   command=lambda: self._retry_kline_load(container, error_frame))
            retry_button.pack(pady=10)
            
        except Exception as e:
            print(f"[ERROR] 显示K线图错误时出错: {str(e)}")
    
    def _retry_kline_load(self, container, error_frame):
        """重试K线图加载"""
        try:
            # 移除错误信息
            if error_frame and error_frame.winfo_exists():
                error_frame.destroy()
            
            # 重新加载K线图
            if self.current_stock_code and self.current_focus_date:
                self.show_kline(self.current_stock_code, self.current_focus_date)
                
        except Exception as e:
            print(f"[ERROR] 重试K线图加载时出错: {str(e)}")
    
    def _update_kline_ui(self, success, stock_code, focus_date_str, kline_instance, 
                        container, loading_label):
        """更新K线图UI"""
        try:
            # 移除加载指示器
            if loading_label and loading_label.winfo_exists():
                loading_label.destroy()
            
            if success:
                # 保存K线图实例
                self.current_kline_viewer = kline_instance
                
                # 更新状态
                self._update_status(f"已显示 {stock_code} 的K线图，关注日期: {focus_date_str}")
                
                # 延迟调整布局
                self.app.root.after(200, self._stable_final_adjustment)
                
                # 记录成功
                print(f"[INFO] K线图显示成功: {stock_code}")
                
            else:
                # 显示错误
                self._show_kline_error(container, None, "K线图加载失败")
                self._update_status(f"无法加载 {stock_code} 的K线图")
                
                # 记录失败
                print(f"[ERROR] K线图显示失败: {stock_code}")
                
        except Exception as e:
            error_msg = f"更新K线图UI时出错:\n{str(e)}"
            self._show_kline_error(container, loading_label, error_msg)
            print(f"[ERROR] 更新K线图UI时出错: {str(e)}")
    
    def _stable_final_adjustment(self):
        """稳定的最终布局调整"""
        try:
            # 确保K线图尺寸合适
            if self.current_kline_viewer and hasattr(self.current_kline_viewer, 'canvas'):
                canvas = self.current_kline_viewer.canvas
                if canvas:
                    canvas_widget = canvas.get_tk_widget()
                    container = self.app.get_kline_container()
                    
                    if container:
                        container_width = container.winfo_width()
                        container_height = container.winfo_height()
                        
                        if container_width > 100 and container_height > 100:
                            canvas_widget.config(
                                width=max(400, container_width - 20),
                                height=max(300, container_height - 20)
                            )
            
            # 延迟重新布局
            self.app.root.after(100, self.app.root.update_idletasks)
            
        except Exception as e:
            print(f"[ERROR] 布局调整时出错: {str(e)}")
    
    def _enable_external_buttons(self):
        """启用外部软件按钮"""
        try:
            tdx_button = self.app.get_tdx_button()
            ths_button = self.app.get_ths_button()
            
            if tdx_button:
                tdx_button.config(state='normal')
            if ths_button:
                ths_button.config(state='normal')
                
        except Exception as e:
            print(f"[ERROR] 启用外部按钮时出错: {str(e)}")
    
    def _add_to_history(self, stock_code, focus_date_str, timestamp=None):
        """添加到历史记录"""
        history_entry = {
            'stock_code': stock_code,
            'focus_date': focus_date_str,
            'timestamp': timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.kline_history.append(history_entry)
        
        # 限制历史记录大小
        if len(self.kline_history) > self.max_kline_history:
            self.kline_history = self.kline_history[-self.max_kline_history:]
    
    def _update_status(self, message):
        """更新状态显示"""
        try:
            if hasattr(self.app, 'get_status_label'):
                status_label = self.app.get_status_label()
                if status_label:
                    status_label.config(text=message)
        except Exception as e:
            print(f"[ERROR] 更新状态时出错: {str(e)}")
    
    def _log_stock_selection(self, stock_code, focus_date, result):
        """记录股票选择操作"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[INFO] {timestamp} 股票选择: {stock_code} | {focus_date} | 结果: {result}")
    
    def _log_external_app_action(self, app_name, stock_code, result):
        """记录外部应用操作"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[INFO] {timestamp} {app_name}操作: {stock_code} | 结果: {result}")
    
    def analyze_stock_data(self, stock_code=None, date_range=None):
        """
        分析股票数据（扩展功能占位）
        
        参数:
            stock_code: 股票代码
            date_range: 日期范围
            
        返回:
            dict: 分析结果
        """
        # 这是一个扩展功能的占位方法
        # 可以实现技术指标计算、统计分析等功能
        
        stock = stock_code or self.current_stock_code
        
        if not stock:
            return {"error": "未选择股票"}
        
        return {
            "stock_code": stock,
            "analysis": "股票分析功能开发中",
            "suggestions": ["功能扩展: 技术指标", "功能扩展: 统计分析", "功能扩展: 回测功能"]
        }