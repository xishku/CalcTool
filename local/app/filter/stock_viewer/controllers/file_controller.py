#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
文件控制器
处理与文件相关的所有操作，包括文件选择、加载、解析和UI更新
"""

import os
import sys
from tkinter import filedialog, messagebox
from datetime import datetime


class FileController:
    """文件控制器 - 处理文件相关操作"""
    
    def __init__(self, app):
        """
        初始化文件控制器
        
        参数:
            app: 主应用程序实例
        """
        self.app = app
        self.current_file = None
        self.last_loaded_file = None
        
    def select_file(self, file_path=None):
        """
        选择数据文件
        
        参数:
            file_path: 可选的文件路径，如果提供则直接使用
            
        返回:
            bool: 文件选择是否成功
        """
        try:
            if not file_path:
                # 弹出文件选择对话框
                file_path = filedialog.askopenfilename(
                    title="选择股票数据文件",
                    filetypes=[
                        ("文本文件", "*.txt"),
                        ("数据文件", "*.csv"),
                        ("所有文件", "*.*")
                    ],
                    initialdir=os.path.expanduser("~")
                )
            
            if file_path:
                # 验证文件是否存在
                if not os.path.exists(file_path):
                    messagebox.showerror("错误", f"文件不存在:\n{file_path}")
                    return False
                
                # 验证文件扩展名
                if not self._validate_file_extension(file_path):
                    messagebox.showerror("错误", 
                        "不支持的文件格式。请选择.txt或.csv文件")
                    return False
                
                # 保存当前文件路径
                self.current_file = file_path
                
                # 更新UI显示文件名
                self._update_file_display(file_path)
                
                # 加载文件数据
                return self.load_file(file_path)
            else:
                # 用户取消了文件选择
                return False
                
        except Exception as e:
            error_msg = f"选择文件时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def load_file(self, file_path=None):
        """
        加载并解析数据文件
        
        参数:
            file_path: 可选的文件路径，如果未提供则使用当前文件
            
        返回:
            bool: 文件加载是否成功
        """
        try:
            # 确定要加载的文件
            target_file = file_path or self.current_file
            
            if not target_file or not os.path.exists(target_file):
                messagebox.showwarning("警告", "请先选择有效的文件")
                return False
            
            # 更新状态显示
            self._update_status(f"正在解析文件: {os.path.basename(target_file)}")
            
            # 强制UI更新
            if hasattr(self.app, 'root'):
                self.app.root.update()
            
            # 解析文件
            success, message = self._parse_file(target_file)
            
            if success:
                # 保存最后加载的文件
                self.last_loaded_file = target_file
                self.current_file = target_file
                
                # 获取解析后的数据
                data_records = self.app.parser.get_data()
                record_count = len(data_records)
                
                # 更新状态
                self._update_status(f"加载完成: {record_count} 条记录")
                
                # 更新UI显示
                self._update_ui_after_load(data_records, target_file)
                
                # 记录加载时间
                self.last_load_time = datetime.now()
                
                # 输出成功信息到控制台
                print(f"[INFO] 文件加载成功: {target_file}")
                print(f"[INFO] 解析记录数: {record_count}")
                print(f"[INFO] 解析消息: {message}")
                
                return True
            else:
                # 解析失败
                self._update_status("数据加载失败")
                messagebox.showerror("错误", f"解析文件失败:\n{message}")
                
                # 输出错误信息到控制台
                print(f"[ERROR] 文件解析失败: {target_file}")
                print(f"[ERROR] 错误信息: {message}")
                
                return False
                
        except Exception as e:
            error_msg = f"加载文件时出错:\n{str(e)}"
            self._update_status("加载出错")
            messagebox.showerror("错误", error_msg)
            
            # 输出异常信息到控制台
            print(f"[EXCEPTION] 文件加载异常: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return False
    
    def reload_last_file(self):
        """
        重新加载最后一次成功的文件
        
        返回:
            bool: 重新加载是否成功
        """
        if self.last_loaded_file and os.path.exists(self.last_loaded_file):
            self._update_status(f"重新加载文件: {os.path.basename(self.last_loaded_file)}")
            return self.load_file(self.last_loaded_file)
        else:
            messagebox.showinfo("提示", "没有可重新加载的文件")
            return False
    
    def clear_data(self):
        """
        清除当前加载的数据
        
        返回:
            bool: 数据清除是否成功
        """
        try:
            # 清除解析器数据
            if hasattr(self.app, 'parser'):
                self.app.parser.data = []
                self.app.data_records = []
            
            # 清除UI显示
            self._clear_ui_display()
            
            # 更新状态
            self._update_status("数据已清除")
            
            # 清除当前文件
            self.current_file = None
            
            # 清除统计信息
            if hasattr(self.app, 'stats'):
                self.app.stats = None
            
            # 清除K线图
            if hasattr(self.app, 'stock_controller'):
                self.app.stock_controller.close_kline_viewer()
            
            # 禁用外部软件按钮
            if hasattr(self.app, 'right_panel'):
                if hasattr(self.app.right_panel, 'tdx_button'):
                    self.app.right_panel.tdx_button.config(state='disabled')
                if hasattr(self.app.right_panel, 'ths_button'):
                    self.app.right_panel.ths_button.config(state='disabled')
            
            print(f"[INFO] 数据已清除")
            return True
            
        except Exception as e:
            error_msg = f"清除数据时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def _parse_file(self, file_path):
        """
        解析文件内容
        
        参数:
            file_path: 文件路径
            
        返回:
            tuple: (是否成功, 消息)
        """
        try:
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, "文件为空"
            
            if file_size > 10 * 1024 * 1024:  # 10MB限制
                return False, "文件过大，最大支持10MB"
            
            # 调用解析器解析文件
            if hasattr(self.app, 'parser'):
                return self.app.parser.parse(file_path)
            else:
                return False, "解析器未初始化"
                
        except Exception as e:
            return False, f"解析文件时出错: {str(e)}"
    
    def _update_file_display(self, file_path):
        """
        更新文件显示
        
        参数:
            file_path: 文件路径
        """
        try:
            if not file_path:
                return
            
            # 获取文件名
            filename = os.path.basename(file_path)
            
            # 截断过长的文件名
            if len(filename) > 30:
                display_name = filename[:15] + "..." + filename[-12:]
            else:
                display_name = filename
            
            # 更新主窗口的文件名显示
            if hasattr(self.app, 'file_path_var'):
                self.app.file_path_var.set(display_name)
            
            # 更新左侧面板的文件信息
            if hasattr(self.app, 'left_panel') and hasattr(self.app.left_panel, 'file_info_label'):
                short_name = display_name
                if len(short_name) > 15:
                    short_name = short_name[:12] + "..."
                self.app.left_panel.file_info_label.config(
                    text=short_name,
                    foreground="#4a6fa5"
                )
            
            # 输出到控制台
            print(f"[INFO] 当前文件: {filename}")
            
        except Exception as e:
            print(f"[ERROR] 更新文件显示时出错: {str(e)}")
    
    def _update_ui_after_load(self, data_records, file_path):
        """
        加载文件后更新UI
        
        参数:
            data_records: 数据记录列表
            file_path: 文件路径
        """
        try:
            if not data_records:
                self._update_status("无有效数据")
                return
            
            record_count = len(data_records)
            
            # 计算统计信息
            if hasattr(self.app, 'stats'):
                from models.stock_model import StockStats
                self.app.stats = StockStats().calculate(
                    data_records, 
                    os.path.basename(file_path)
                )
            
            # 更新数据模型
            self.app.data_records = data_records
            
            # 更新左侧面板的数据显示
            if hasattr(self.app, 'left_panel'):
                # 更新数据显示
                self.app.left_panel.update_data_display(data_records)
                
                # 更新统计显示
                stats_text = self._generate_stats_text(data_records, file_path)
                self.app.left_panel.update_stats_display(stats_text)
            
            # 清除过滤条件
            self._clear_filter_conditions()
            
            # 强制UI更新
            if hasattr(self.app, 'root'):
                self.app.root.update_idletasks()
            
            # 输出成功信息
            print(f"[INFO] UI更新完成，显示 {record_count} 条记录")
            
        except Exception as e:
            print(f"[ERROR] 更新UI时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _generate_stats_text(self, data_records, file_path):
        """
        生成统计文本
        
        参数:
            data_records: 数据记录列表
            file_path: 文件路径
            
        返回:
            str: 统计文本
        """
        if not data_records:
            return "无数据"
        
        # 基本统计
        total_records = len(data_records)
        unique_stocks = len(set(record.stock_code for record in data_records))
        
        # 获取日期范围
        focus_dates = [record.focus_date for record in data_records if record.focus_date]
        if focus_dates:
            min_date = min(focus_dates)
            max_date = max(focus_dates)
            date_range = f"{min_date} 到 {max_date}"
        else:
            date_range = "N/A"
        
        # 生成统计文本
        stats_text = f"=== 数据统计 ===\n"
        stats_text += f"总记录数: {total_records}\n"
        stats_text += f"唯一股票数: {unique_stocks}\n"
        stats_text += f"日期范围: {date_range}\n"
        stats_text += f"数据文件: {os.path.basename(file_path)[:20]}\n"
        
        # 日期分布统计（前5个）
        date_counts = {}
        for record in data_records:
            date = record.focus_date
            date_counts[date] = date_counts.get(date, 0) + 1
        
        sorted_dates = sorted(date_counts.items(), key=lambda x: x[0])[:5]
        if sorted_dates:
            stats_text += "\n=== 日期分布 ===\n"
            for date, count in sorted_dates:
                stats_text += f"{date}: {count} 条\n"
            
            if len(date_counts) > 5:
                stats_text += f"... 还有 {len(date_counts) - 5} 个日期\n"
        
        return stats_text
    
    def _clear_ui_display(self):
        """清除UI显示"""
        try:
            # 清除左侧面板的数据显示
            if hasattr(self.app, 'left_panel'):
                # 清除表格数据
                if hasattr(self.app.left_panel, 'tree'):
                    for item in self.app.left_panel.tree.get_children():
                        self.app.left_panel.tree.delete(item)
                
                # 清除统计显示
                if hasattr(self.app.left_panel, 'stats_text'):
                    self.app.left_panel.stats_text.delete(1.0, tk.END)
                    self.app.left_panel.stats_text.insert(1.0, "等待加载数据...")
                    self.app.left_panel.stats_text.configure(state='disabled')
                
                # 清除文件信息
                if hasattr(self.app.left_panel, 'file_info_label'):
                    self.app.left_panel.file_info_label.config(text="无")
            
            # 清除K线图容器
            if hasattr(self.app, 'right_panel'):
                if hasattr(self.app.right_panel, 'kline_container'):
                    for widget in self.app.right_panel.kline_container.winfo_children():
                        widget.destroy()
                    
                    # 显示初始提示
                    tip_label = tk.Label(self.app.right_panel.kline_container, 
                                       text="双击左侧表格查看K线图", 
                                       font=('Arial', 10),
                                       foreground="#666666")
                    tip_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            
            # 清除文件名显示
            if hasattr(self.app, 'file_path_var'):
                self.app.file_path_var.set("未选择文件")
            
        except Exception as e:
            print(f"[ERROR] 清除UI显示时出错: {str(e)}")
    
    def _clear_filter_conditions(self):
        """清除过滤条件"""
        try:
            if hasattr(self.app, 'get_filter_vars'):
                filter_vars = self.app.get_filter_vars()
                if filter_vars[0] and filter_vars[1]:
                    filter_vars[0].set("")
                    filter_vars[1].set("")
        except Exception as e:
            print(f"[ERROR] 清除过滤条件时出错: {str(e)}")
    
    def _update_status(self, message):
        """
        更新状态显示
        
        参数:
            message: 状态消息
        """
        try:
            if hasattr(self.app, 'get_status_label'):
                status_label = self.app.get_status_label()
                if status_label:
                    status_label.config(text=message)
        except Exception as e:
            print(f"[ERROR] 更新状态时出错: {str(e)}")
    
    def _validate_file_extension(self, file_path):
        """
        验证文件扩展名
        
        参数:
            file_path: 文件路径
            
        返回:
            bool: 是否支持的文件格式
        """
        supported_extensions = ['.txt', '.csv', '.dat']
        _, ext = os.path.splitext(file_path)
        return ext.lower() in supported_extensions
    
    def get_file_info(self):
        """
        获取当前文件信息
        
        返回:
            dict: 文件信息字典
        """
        info = {
            'current_file': self.current_file,
            'last_loaded_file': self.last_loaded_file,
            'has_data': len(self.app.data_records) > 0 if hasattr(self.app, 'data_records') else False,
            'record_count': len(self.app.data_records) if hasattr(self.app, 'data_records') else 0
        }
        
        if hasattr(self, 'last_load_time'):
            info['last_load_time'] = self.last_load_time.strftime("%Y-%m-%d %H:%M:%S")
        
        return info
    
    def export_data(self, export_format='txt', file_path=None):
        """
        导出数据
        
        参数:
            export_format: 导出格式 ('txt', 'csv')
            file_path: 导出文件路径，如果未提供则弹出保存对话框
            
        返回:
            bool: 导出是否成功
        """
        try:
            if not hasattr(self.app, 'data_records') or not self.app.data_records:
                messagebox.showinfo("提示", "没有数据可导出")
                return False
            
            if not file_path:
                # 弹出保存对话框
                default_name = f"stock_data_export.{export_format}"
                file_path = filedialog.asksaveasfilename(
                    title="导出数据",
                    defaultextension=f".{export_format}",
                    filetypes=[(f"{export_format.upper()}文件", f"*.{export_format}")],
                    initialfile=default_name
                )
            
            if not file_path:
                return False  # 用户取消了保存
            
            # 导出数据
            with open(file_path, 'w', encoding='utf-8') as f:
                if export_format.lower() == 'csv':
                    # CSV格式
                    f.write("timestamp,stock_code,focus_date\n")
                    for record in self.app.data_records:
                        f.write(f"{record.timestamp},{record.stock_code},{record.focus_date}\n")
                else:
                    # TXT格式（制表符分隔）
                    for record in self.app.data_records:
                        f.write(f"{record.timestamp}\t{record.stock_code}\t{record.focus_date}\n")
            
            # 更新状态
            self._update_status(f"数据已导出到: {os.path.basename(file_path)}")
            
            # 输出成功信息
            print(f"[INFO] 数据已导出: {file_path}")
            
            return True
            
        except Exception as e:
            error_msg = f"导出数据时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False