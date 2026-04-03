#!/usr/bin/python
#-*-coding:UTF-8-*-

"""
过滤器控制器
处理数据过滤相关的所有操作，包括股票代码过滤、日期过滤和结果展示
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import re


class FilterController:
    """过滤器控制器 - 处理数据过滤相关操作"""
    
    def __init__(self, app):
        """
        初始化过滤器控制器
        
        参数:
            app: 主应用程序实例
        """
        self.app = app
        self.current_filter = {
            'stock_code': '',
            'focus_date': '',
            'active': False
        }
        self.filter_history = []
        self.max_history_size = 10
        
    def apply_filter(self, stock_filter=None, date_filter=None):
        """
        应用过滤条件
        
        参数:
            stock_filter: 股票代码过滤条件，如果未提供则从UI获取
            date_filter: 日期过滤条件，如果未提供则从UI获取
            
        返回:
            bool: 过滤是否成功应用
        """
        try:
            # 检查是否有数据可过滤
            if not self._has_data_to_filter():
                messagebox.showinfo("提示", "请先加载数据文件")
                return False
            
            # 获取过滤条件
            stock_code_filter, date_filter = self._get_filter_conditions(stock_filter, date_filter)
            
            # 验证过滤条件
            if not self._validate_filter_conditions(stock_code_filter, date_filter):
                return False
            
            # 保存当前过滤条件
            self.current_filter = {
                'stock_code': stock_code_filter,
                'focus_date': date_filter,
                'active': True
            }
            
            # 添加到历史记录
            self._add_to_history(stock_code_filter, date_filter)
            
            # 执行过滤
            filtered_data = self._filter_data(stock_code_filter, date_filter)
            
            # 更新UI显示过滤结果
            self._update_ui_after_filter(filtered_data, stock_code_filter, date_filter)
            
            # 输出过滤信息到控制台
            self._log_filter_operation(stock_code_filter, date_filter, len(filtered_data))
            
            return True
            
        except Exception as e:
            error_msg = f"应用过滤时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            self._update_status("过滤出错")
            return False
    
    def clear_filter(self):
        """
        清除所有过滤条件，显示原始数据
        
        返回:
            bool: 清除是否成功
        """
        try:
            # 检查是否有数据
            if not self._has_data_to_filter():
                messagebox.showinfo("提示", "没有数据可操作")
                return False
            
            # 重置过滤条件
            self.current_filter = {
                'stock_code': '',
                'focus_date': '',
                'active': False
            }
            
            # 清空过滤输入框
            self._clear_filter_inputs()
            
            # 显示所有数据
            self._show_all_data()
            
            # 更新状态
            self._update_status(f"显示所有 {len(self.app.data_records)} 条记录")
            
            # 输出到控制台
            print(f"[INFO] 过滤条件已清除，显示全部数据")
            
            return True
            
        except Exception as e:
            error_msg = f"清除过滤时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def filter_by_stock_pattern(self, pattern):
        """
        使用正则表达式模式过滤股票代码
        
        参数:
            pattern: 正则表达式模式
            
        返回:
            bool: 过滤是否成功
        """
        try:
            if not pattern:
                return self.clear_filter()
            
            # 验证正则表达式
            try:
                re.compile(pattern)
            except re.error as e:
                messagebox.showerror("错误", f"无效的正则表达式:\n{str(e)}")
                return False
            
            # 应用过滤
            return self.apply_filter(stock_filter=pattern)
            
        except Exception as e:
            error_msg = f"正则表达式过滤时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def filter_by_date_range(self, start_date, end_date):
        """
        按日期范围过滤
        
        参数:
            start_date: 开始日期 (YYYYMMDD格式)
            end_date: 结束日期 (YYYYMMDD格式)
            
        返回:
            bool: 过滤是否成功
        """
        try:
            # 验证日期格式
            if not self._validate_date_format(start_date) or not self._validate_date_format(end_date):
                messagebox.showerror("错误", "日期格式应为YYYYMMDD")
                return False
            
            # 转换为datetime对象进行比较
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            
            if start_dt > end_dt:
                messagebox.showerror("错误", "开始日期不能晚于结束日期")
                return False
            
            # 生成日期范围条件
            date_condition = f"{start_date}-{end_date}"
            
            # 应用过滤
            return self.apply_filter(date_filter=date_condition)
            
        except Exception as e:
            error_msg = f"日期范围过滤时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def quick_filter(self, filter_type, value):
        """
        快速过滤功能
        
        参数:
            filter_type: 过滤类型 ('stock_code', 'date', 'both')
            value: 过滤值
            
        返回:
            bool: 过滤是否成功
        """
        try:
            if filter_type == 'stock_code':
                return self.apply_filter(stock_filter=value)
            elif filter_type == 'date':
                return self.apply_filter(date_filter=value)
            elif filter_type == 'both':
                # 假设value是"代码:日期"格式
                if ':' in value:
                    parts = value.split(':', 1)
                    return self.apply_filter(stock_filter=parts[0].strip(), date_filter=parts[1].strip())
                else:
                    messagebox.showerror("错误", "格式应为: 股票代码:日期")
                    return False
            else:
                messagebox.showerror("错误", f"不支持的过滤类型: {filter_type}")
                return False
                
        except Exception as e:
            error_msg = f"快速过滤时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def get_filter_stats(self):
        """
        获取过滤统计信息
        
        返回:
            dict: 过滤统计信息
        """
        stats = {
            'is_filtered': self.current_filter['active'],
            'current_stock_filter': self.current_filter['stock_code'],
            'current_date_filter': self.current_filter['focus_date'],
            'history_count': len(self.filter_history),
            'total_records': len(self.app.data_records) if hasattr(self.app, 'data_records') else 0
        }
        
        if self.current_filter['active'] and hasattr(self.app, 'data_records'):
            filtered_data = self._filter_data(
                self.current_filter['stock_code'],
                self.current_filter['focus_date']
            )
            stats['filtered_records'] = len(filtered_data)
            stats['filter_percentage'] = (len(filtered_data) / len(self.app.data_records) * 100) if self.app.data_records else 0
        
        return stats
    
    def undo_last_filter(self):
        """
        撤销上一次过滤操作
        
        返回:
            bool: 撤销是否成功
        """
        try:
            if not self.filter_history:
                messagebox.showinfo("提示", "没有可撤销的过滤记录")
                return False
            
            # 获取上一次过滤记录
            last_filter = self.filter_history.pop()
            
            # 获取上上次过滤记录（如果有）
            if self.filter_history:
                prev_filter = self.filter_history[-1]
                stock_filter = prev_filter.get('stock_code', '')
                date_filter = prev_filter.get('date', '')
            else:
                stock_filter = ''
                date_filter = ''
            
            # 应用上一次的过滤条件
            return self.apply_filter(stock_filter, date_filter)
            
        except Exception as e:
            error_msg = f"撤销过滤时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False
    
    def _has_data_to_filter(self):
        """检查是否有数据可过滤"""
        if not hasattr(self.app, 'data_records') or not self.app.data_records:
            return False
        return True
    
    def _get_filter_conditions(self, stock_filter=None, date_filter=None):
        """获取过滤条件"""
        # 如果提供了参数，使用参数
        if stock_filter is not None or date_filter is not None:
            stock_code_filter = stock_filter or ''
            date_filter = date_filter or ''
        else:
            # 从UI获取过滤条件
            if hasattr(self.app, 'get_filter_vars'):
                filter_vars = self.app.get_filter_vars()
                if filter_vars[0] and filter_vars[1]:
                    stock_code_filter = filter_vars[0].get().strip()
                    date_filter = filter_vars[1].get().strip()
                else:
                    stock_code_filter = ''
                    date_filter = ''
            else:
                stock_code_filter = ''
                date_filter = ''
        
        return stock_code_filter, date_filter
    
    def _validate_filter_conditions(self, stock_filter, date_filter):
        """验证过滤条件"""
        # 如果两个条件都为空，相当于清除过滤
        if not stock_filter and not date_filter:
            return self.clear_filter()
        
        # 验证股票代码过滤条件
        if stock_filter:
            # 检查是否为有效的正则表达式
            try:
                re.compile(stock_filter)
            except re.error:
                # 如果不是有效的正则表达式，检查是否为普通文本
                if len(stock_filter) > 20:
                    messagebox.showwarning("警告", "股票代码过滤条件过长")
                    return False
        
        # 验证日期过滤条件
        if date_filter:
            # 检查是否为日期范围格式
            if '-' in date_filter:
                parts = date_filter.split('-')
                if len(parts) != 2:
                    messagebox.showerror("错误", "日期范围格式应为: YYYYMMDD-YYYYMMDD")
                    return False
                
                for part in parts:
                    if not self._validate_date_format(part):
                        messagebox.showerror("错误", f"无效的日期格式: {part}")
                        return False
            else:
                # 检查是否为单个日期
                if not self._validate_date_format(date_filter):
                    messagebox.showerror("错误", f"无效的日期格式: {date_filter}")
                    return False
        
        return True
    
    def _validate_date_format(self, date_str):
        """验证日期格式是否为YYYYMMDD"""
        if not date_str:
            return False
        
        if len(date_str) != 8 or not date_str.isdigit():
            return False
        
        try:
            datetime.strptime(date_str, "%Y%m%d")
            return True
        except ValueError:
            return False
    
    def _filter_data(self, stock_filter, date_filter):
        """执行数据过滤"""
        if not hasattr(self.app, 'parser') or not hasattr(self.app, 'data_records'):
            return []
        
        # 使用解析器的过滤功能
        if hasattr(self.app.parser, 'filter_data'):
            return self.app.parser.filter_data(stock_filter, date_filter)
        
        # 如果没有解析器的过滤功能，手动过滤
        filtered_data = self.app.data_records
        
        # 股票代码过滤
        if stock_filter:
            try:
                # 尝试使用正则表达式匹配
                pattern = re.compile(stock_filter, re.IGNORECASE)
                filtered_data = [
                    record for record in filtered_data
                    if pattern.search(record.stock_code)
                ]
            except re.error:
                # 如果正则表达式无效，使用普通包含匹配
                filtered_data = [
                    record for record in filtered_data
                    if stock_filter in record.stock_code
                ]
        
        # 日期过滤
        if date_filter:
            if '-' in date_filter:
                # 日期范围过滤
                start_date, end_date = date_filter.split('-')
                start_dt = datetime.strptime(start_date, "%Y%m%d")
                end_dt = datetime.strptime(end_date, "%Y%m%d")
                
                filtered_data = [
                    record for record in filtered_data
                    if self._date_in_range(record.focus_date, start_dt, end_dt)
                ]
            else:
                # 单个日期过滤
                filtered_data = [
                    record for record in filtered_data
                    if date_filter in record.focus_date
                ]
        
        return filtered_data
    
    def _date_in_range(self, date_str, start_dt, end_dt):
        """检查日期是否在范围内"""
        try:
            record_dt = datetime.strptime(date_str, "%Y%m%d")
            return start_dt <= record_dt <= end_dt
        except (ValueError, TypeError):
            return False
    
    def _update_ui_after_filter(self, filtered_data, stock_filter, date_filter):
        """过滤后更新UI"""
        try:
            # 更新左侧面板的数据显示
            if hasattr(self.app, 'left_panel'):
                self.app.left_panel.update_data_display(filtered_data)
            
            # 更新过滤条件显示
            self._update_filter_display(stock_filter, date_filter)
            
            # 更新状态显示
            filter_description = self._get_filter_description(stock_filter, date_filter)
            status_text = f"显示 {len(filtered_data)} 条记录"
            if filter_description:
                status_text += f" ({filter_description})"
            
            self._update_status(status_text)
            
            # 强制UI更新
            if hasattr(self.app, 'root'):
                self.app.root.update_idletasks()
            
        except Exception as e:
            print(f"[ERROR] 更新过滤UI时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _update_filter_display(self, stock_filter, date_filter):
        """更新过滤条件显示"""
        try:
            # 更新输入框的值
            if hasattr(self.app, 'get_filter_vars'):
                filter_vars = self.app.get_filter_vars()
                if filter_vars[0] and filter_vars[1]:
                    filter_vars[0].set(stock_filter)
                    filter_vars[1].set(date_filter)
            
            # 在左侧面板显示当前过滤条件
            if hasattr(self.app, 'left_panel') and hasattr(self.app.left_panel, 'stats_text'):
                stats_widget = self.app.left_panel.stats_text
                
                # 获取当前统计文本
                current_text = stats_widget.get(1.0, tk.END).strip()
                
                # 添加过滤信息
                filter_info = "\n\n=== 当前过滤 ==="
                if stock_filter:
                    filter_info += f"\n股票代码: {stock_filter}"
                if date_filter:
                    filter_info += f"\n关注日期: {date_filter}"
                
                # 更新文本
                if "=== 当前过滤 ===" in current_text:
                    # 替换现有的过滤信息
                    lines = current_text.split('\n')
                    filtered_lines = [line for line in lines if "=== 当前过滤 ===" not in line]
                    new_text = '\n'.join(filtered_lines).strip() + filter_info
                else:
                    # 添加新的过滤信息
                    new_text = current_text + filter_info
                
                stats_widget.delete(1.0, tk.END)
                stats_widget.insert(1.0, new_text)
                stats_widget.configure(state='disabled')
                
        except Exception as e:
            print(f"[ERROR] 更新过滤显示时出错: {str(e)}")
    
    def _get_filter_description(self, stock_filter, date_filter):
        """获取过滤条件描述"""
        description_parts = []
        
        if stock_filter:
            description_parts.append(f"代码: {stock_filter}")
        
        if date_filter:
            if '-' in date_filter:
                start_date, end_date = date_filter.split('-')
                description_parts.append(f"日期: {start_date}~{end_date}")
            else:
                description_parts.append(f"日期: {date_filter}")
        
        if not description_parts:
            return ""
        
        return " | ".join(description_parts)
    
    def _clear_filter_inputs(self):
        """清空过滤输入框"""
        try:
            if hasattr(self.app, 'get_filter_vars'):
                filter_vars = self.app.get_filter_vars()
                if filter_vars[0] and filter_vars[1]:
                    filter_vars[0].set("")
                    filter_vars[1].set("")
        except Exception as e:
            print(f"[ERROR] 清空过滤输入框时出错: {str(e)}")
    
    def _show_all_data(self):
        """显示所有数据"""
        try:
            if hasattr(self.app, 'left_panel') and hasattr(self.app, 'data_records'):
                self.app.left_panel.update_data_display(self.app.data_records)
                
                # 清除过滤信息显示
                if hasattr(self.app.left_panel, 'stats_text'):
                    stats_widget = self.app.left_panel.stats_text
                    current_text = stats_widget.get(1.0, tk.END).strip()
                    
                    if "=== 当前过滤 ===" in current_text:
                        # 移除过滤信息
                        lines = current_text.split('\n')
                        filtered_lines = [line for line in lines if "=== 当前过滤 ===" not in line]
                        new_text = '\n'.join(filtered_lines).strip()
                        
                        stats_widget.delete(1.0, tk.END)
                        stats_widget.insert(1.0, new_text)
                        stats_widget.configure(state='disabled')
                
        except Exception as e:
            print(f"[ERROR] 显示所有数据时出错: {str(e)}")
    
    def _update_status(self, message):
        """更新状态显示"""
        try:
            if hasattr(self.app, 'get_status_label'):
                status_label = self.app.get_status_label()
                if status_label:
                    status_label.config(text=message)
        except Exception as e:
            print(f"[ERROR] 更新状态时出错: {str(e)}")
    
    def _add_to_history(self, stock_filter, date_filter):
        """添加到过滤历史"""
        history_entry = {
            'stock_code': stock_filter,
            'date': date_filter,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.filter_history.append(history_entry)
        
        # 限制历史记录大小
        if len(self.filter_history) > self.max_history_size:
            self.filter_history = self.filter_history[-self.max_history_size:]
    
    def _log_filter_operation(self, stock_filter, date_filter, result_count):
        """记录过滤操作到控制台"""
        filter_desc = self._get_filter_description(stock_filter, date_filter)
        
        if filter_desc:
            print(f"[INFO] 应用过滤: {filter_desc}")
        else:
            print(f"[INFO] 清除过滤条件")
        
        print(f"[INFO] 过滤结果: {result_count} 条记录")
        
        if hasattr(self.app, 'data_records'):
            total_records = len(self.app.data_records)
            if total_records > 0:
                percentage = (result_count / total_records) * 100
                print(f"[INFO] 过滤比例: {percentage:.1f}% ({result_count}/{total_records})")
    
    def export_filtered_data(self, export_format='txt', file_path=None):
        """
        导出过滤后的数据
        
        参数:
            export_format: 导出格式 ('txt', 'csv')
            file_path: 导出文件路径，如果未提供则弹出保存对话框
            
        返回:
            bool: 导出是否成功
        """
        try:
            # 获取过滤后的数据
            if not self.current_filter['active']:
                messagebox.showinfo("提示", "当前没有激活的过滤条件")
                return False
            
            filtered_data = self._filter_data(
                self.current_filter['stock_code'],
                self.current_filter['focus_date']
            )
            
            if not filtered_data:
                messagebox.showinfo("提示", "没有可导出的过滤数据")
                return False
            
            if not file_path:
                # 弹出保存对话框
                filter_desc = self._get_filter_description(
                    self.current_filter['stock_code'],
                    self.current_filter['focus_date']
                )
                
                # 创建安全的文件名
                safe_desc = "".join(c for c in filter_desc if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_desc = safe_desc[:50]  # 限制长度
                
                default_name = f"filtered_data_{safe_desc}.{export_format}" if safe_desc else f"filtered_data.{export_format}"
                
                file_path = filedialog.asksaveasfilename(
                    title="导出过滤数据",
                    defaultextension=f".{export_format}",
                    filetypes=[(f"{export_format.upper()}文件", f"*.{export_format}")],
                    initialfile=default_name
                )
            
            if not file_path:
                return False  # 用户取消了保存
            
            # 导出数据
            with open(file_path, 'w', encoding='utf-8') as f:
                # 添加过滤信息注释
                filter_info = self._get_filter_description(
                    self.current_filter['stock_code'],
                    self.current_filter['focus_date']
                )
                
                if export_format.lower() == 'csv':
                    f.write(f"# 过滤条件: {filter_info}\n")
                    f.write("timestamp,stock_code,focus_date\n")
                    for record in filtered_data:
                        f.write(f"{record.timestamp},{record.stock_code},{record.focus_date}\n")
                else:
                    f.write(f"# 过滤条件: {filter_info}\n")
                    for record in filtered_data:
                        f.write(f"{record.timestamp}\t{record.stock_code}\t{record.focus_date}\n")
            
            # 更新状态
            self._update_status(f"过滤数据已导出: {os.path.basename(file_path)}")
            
            # 输出成功信息
            print(f"[INFO] 过滤数据已导出: {file_path}")
            print(f"[INFO] 导出记录数: {len(filtered_data)}")
            
            return True
            
        except Exception as e:
            error_msg = f"导出过滤数据时出错:\n{str(e)}"
            messagebox.showerror("错误", error_msg)
            return False