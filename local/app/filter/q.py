# ==================== Imports & Constants ====================
import sys
import os
import datetime
import time
from collections import OrderedDict
from typing import List, Dict, Optional
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QSplitter,
                                QTableWidget, QTableWidgetItem, QHeaderView,
                                QVBoxLayout, QWidget, QMenu, QMessageBox, QLabel, QToolTip)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QAction, QCursor
# SDK Imports - MUST be exactly like this, no try-except ImportError
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../src"))
from CalcTool.sdk.tool_main import CalcLast1YearCount
from CalcTool.sdk.logger import Logger
from CalcTool.sdk.tdx_data_agent import TdxDataAgent
MIN_WINDOW_SIZE = (800, 600)
DEFAULT_WINDOW_SIZE = (1200, 700)
LEFT_PANEL_WIDTH = 150
KLINE_HEIGHT = 500
DEFAULT_VISIBLE_BARS = 50
PRELOAD_BARS = 100
CACHE_MAX_SIZE = 5
CACHE_TTL_MINUTES = 5
# ==================== DataParser ====================
class DataParser:
    """Parses input tab-separated file and expands focus dates."""
    @staticmethod
    def parse_file(filepath: str) -> List[Dict]:
        items = []
        line_no = 0
        lines = DataParser._read_file(filepath)
        if not lines:
            return items
        for line in lines:
            line_no += 1
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                Logger.log().warn(f"Line {line_no}: Column count < 2, skipped.")
                continue
            parsed_item = DataParser._parse_line(parts, line_no)
            if parsed_item:
                items.extend(parsed_item)
        Logger.log().info(f"File parsed: {filepath}, total valid items: {len(items)}")
        return items
    @staticmethod
    def _read_file(filepath: str) -> List[str]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.readlines()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='gb18030') as f:
                    return f.readlines()
            except Exception as e:
                Logger.log().error(f"Failed to read file {filepath}: {str(e)}")
                return []
    @staticmethod
    def _parse_line(parts: List[str], line_no: int) -> List[Dict]:
        dt_str = parts[0].strip()
        sym_str = parts[1].strip()
        if not sym_str:
            Logger.log().warn(f"Line {line_no}: Empty symbol, skipped.")
            return []
        # Symbol must be string, left pad with 0 if missing (assume 6 digits)
        sym_str = sym_str.zfill(6)
        focus_dates = []
        for fd_str in parts[2:]:
            fd_str = fd_str.strip()
            if not fd_str:
                continue
            try:
                fd_int = int(fd_str)
                focus_dates.append(fd_int)
            except ValueError:
                Logger.log().warn(f"Line {line_no}: Invalid focus date '{fd_str}', skipped.")
        if not focus_dates:
            return [{'datetime': dt_str, 'symbol': sym_str, 'focus_date': 0}]
        return [{'datetime': dt_str, 'symbol': sym_str, 'focus_date': fd} for fd in focus_dates]
# ==================== DataCache ====================
class DataCache:
    """LRU Cache for stock data with TTL support."""
    def __init__(self):
        self._cache = OrderedDict()
    def get(self, symbol: str) -> Optional[pd.DataFrame]:
        if symbol in self._cache:
            item = self._cache.pop(symbol)
            if time.time() - item['ts'] <= CACHE_TTL_MINUTES * 60:
                self._cache[symbol] = item
                return item['df'].copy()  # Return copy to avoid mutation
            else:
                del self._cache[symbol]
                Logger.log().info(f"Cache expired for {symbol}")
        return None
    def put(self, symbol: str, df: pd.DataFrame):
        if symbol in self._cache:
            del self._cache[symbol]
        elif len(self._cache) >= CACHE_MAX_SIZE:
            evicted = self._cache.popitem(last=False)
            Logger.log().info(f"Cache LRU evicted: {evicted[0]}")
        self._cache[symbol] = {'df': df.copy(), 'ts': time.time()}
# ==================== DataFetcher ====================
class DataFetcher(QThread):
    """Asynchronous worker to fetch stock data without blocking GUI."""
    data_ready = Signal(str, pd.DataFrame, bool)
    def __init__(self, symbol: str, focus_date: int):
        super().__init__()
        self.symbol = symbol
        self.focus_date = focus_date
    def run(self):
        try:
            agent = TdxDataAgent()
            fd_str = str(self.focus_date)
            fd_dt = datetime.datetime.strptime(fd_str, "%Y%m%d")
            start_dt = fd_dt - datetime.timedelta(days=365)
            end_dt = fd_dt + datetime.timedelta(days=365)
            start_date = int(start_dt.strftime("%Y%m%d"))
            end_date = int(end_dt.strftime("%Y%m%d"))
            Logger.log().info(f"Requesting data for {self.symbol} from {start_date} to {end_date}")
            df = agent.read_kdata_cache(self.symbol, start_date, end_date)
            if df is None or df.empty:
                self.data_ready.emit(self.symbol, pd.DataFrame(), False)
                Logger.log().error(f"No data returned for {self.symbol}")
                return
            # Normalize columns to mplfinance expected format
            df = self._normalize_columns(df)
            self.data_ready.emit(self.symbol, df, True)
        except Exception as e:
            Logger.log().error(f"DataFetcher error: {str(e)}")
            self.data_ready.emit(self.symbol, pd.DataFrame(), False)
    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume', 'amount': 'Amount'
        }
        df = df.rename(columns=rename_map)
        if 'Amount' not in df.columns:
            df['Amount'] = 0.0
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        return df
# ==================== KLineCanvas ====================
class KLineCanvas(FigureCanvas):
    """Matplotlib Canvas embedding mplfinance chart with interaction."""
    focus_updated = Signal(int)  # Emits new focus date (int) on double click
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(12, 7))
        super().__init__(self.fig)
        self.setParent(parent)
        self.df = pd.DataFrame()
        self.visible_bars = DEFAULT_VISIBLE_BARS
        self.view_start = 0
        self.view_end = 0
        self.focus_idx = -1
        self.cross_vline = None
        self.cross_hline = None
        self.ax = None
        self.ax_macd = None
        self.mpl_connect('button_press_event', self.on_click)
        self.setFixedHeight(KLINE_HEIGHT)
    def update_chart(self, df: pd.DataFrame, focus_date: int):
        self.df = df.copy()
        self._calc_indicators()
        self.focus_idx = self._find_focus_index(focus_date)
        self._adjust_view_around_focus()
        self._render()
    def _calc_indicators(self):
        if self.df.empty: return
        self.df['MA5'] = self.df['Close'].rolling(5).mean()
        self.df['MA10'] = self.df['Close'].rolling(10).mean()
        self.df['MA20'] = self.df['Close'].rolling(20).mean()
        self.df['MA60'] = self.df['Close'].rolling(60).mean()
        exp1 = self.df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = self.df['Close'].ewm(span=26, adjust=False).mean()
        self.df['DIF'] = exp1 - exp2
        self.df['DEA'] = self.df['DIF'].ewm(span=9, adjust=False).mean()
        self.df['MACD_Hist'] = (self.df['DIF'] - self.df['DEA']) * 2
    def _find_focus_index(self, focus_date: int) -> int:
        if self.df.empty or focus_date == 0:
            return len(self.df) // 2
        try:
            fd_str = str(focus_date)
            focus_dt = pd.to_datetime(fd_str)
            return self.df.index.get_indexer([focus_dt], method='nearest')[0]
        except Exception:
            return len(self.df) // 2
    def _adjust_view_around_focus(self):
        half = self.visible_bars // 2
        self.view_start = max(0, self.focus_idx - half)
        self.view_end = min(len(self.df), self.view_start + self.visible_bars)
    def _render(self):
        if self.df.empty: return
        df_view = self.df.iloc[self.view_start:self.view_end]
        apds = self._create_addplots(df_view)
        # Fix: Use valid mplfinance kwarg 'panel_ratios' instead of 'panel_sizes'
        fig, axlist = mpf.plot(df_view, type='candle', addplot=apds, returnfig=True,
                                style='charles', panel_ratios=(3, 1), figratio=(12, 7))
        fig.set_canvas(self)
        self.fig = fig
        self.ax = axlist[0]
        # Fix: MACD is on panel 1 (index 1 in axlist when volume=False)
        self.ax_macd = axlist[1] if len(axlist) > 1 else None
        self.draw()
        self._draw_focus_marker()
    def _create_addplots(self, df_view: pd.DataFrame) -> list:
        # Fix: MACD indicators must be attached to panel=1, not panel=2
        apds = [
            mpf.make_addplot(df_view['MA5'], color='r', width=1),
            mpf.make_addplot(df_view['MA10'], color='g', width=1),
            mpf.make_addplot(df_view['MA20'], color='b', width=1),
            mpf.make_addplot(df_view['MA60'], color='y', width=1),
            mpf.make_addplot(df_view['MACD_Hist'], type='bar', panel=1, color='dimgray'),
            mpf.make_addplot(df_view['DIF'], panel=1, color='r'),
            mpf.make_addplot(df_view['DEA'], panel=1, color='g')
        ]
        return apds
    def _draw_focus_marker(self):
        if not self.ax or self.focus_idx < self.view_start or self.focus_idx >= self.view_end:
            return
        idx_in_view = self.focus_idx - self.view_start
        self.ax.axvline(x=idx_in_view, color='b', linestyle='--', linewidth=0.5, alpha=0.5)
        self.draw()
    def on_click(self, event):
        if event.inaxes != self.ax or self.df.empty: return
        idx = int(round(event.xdata))
        actual_idx = self.view_start + idx
        if 0 <= actual_idx < len(self.df):
            row = self.df.iloc[actual_idx]
            msg = self._format_popup_msg(row)
            QToolTip.showText(QCursor.pos(), msg)
            if event.dblclick:
                new_fd = int(row.name.strftime('%Y%m%d'))
                self.focus_updated.emit(new_fd)
    @staticmethod
    def _format_popup_msg(row) -> str:
        date_str = row.name.strftime('%Y%m%d')
        return (f"Date: {date_str}\n"
                f"O: {row['Open']:.2f}  H: {row['High']:.2f}\n"
                f"L: {row['Low']:.2f}  C: {row['Close']:.2f}\n"
                f"V: {row['Volume']}\nAmount: {row['Amount']}")
    def step_kline(self, direction: int):
        if self.df.empty: return
        new_idx = self.focus_idx + direction
        if 0 <= new_idx < len(self.df):
            self.focus_idx = new_idx
            row = self.df.iloc[new_idx]
            msg = self._format_popup_msg(row)
            QToolTip.showText(QCursor.pos(), msg)
            if new_idx < self.view_start or new_idx >= self.view_end:
                self.view_start = max(0, new_idx - self.visible_bars // 2)
                self.view_end = min(len(self.df), self.view_start + self.visible_bars)
            self._render()
    def zoom_in(self):
        self.visible_bars = max(5, self.visible_bars - 10)
        self._adjust_view_around_focus()
        self._render()
    def zoom_out(self):
        self.visible_bars = min(len(self.df), self.visible_bars + 10)
        self._adjust_view_around_focus()
        self._render()
    def reset_view(self):
        self.visible_bars = DEFAULT_VISIBLE_BARS
        self._adjust_view_around_focus()
        self._render()
    def export_png(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Export PNG", "", "PNG Files (*.png)")
        if filepath:
            self.fig.savefig(filepath)
            Logger.log().info(f"Chart exported to {filepath}")
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Zoom In", self.zoom_in)
        menu.addAction("Zoom Out", self.zoom_out)
        menu.addAction("Reset View", self.reset_view)
        menu.addAction("Export PNG", self.export_png)
        menu.exec_(event.globalPos())
# ==================== MainWindow ====================
class MainWindow(QMainWindow):
    """Main Application Window managing layout, list, and canvas interaction."""
    def __init__(self):
        super().__init__()
        self.resize(*DEFAULT_WINDOW_SIZE)
        self.setMinimumSize(*MIN_WINDOW_SIZE)
        self.items = []
        self.cache = DataCache()
        self.current_symbol = ""
        self.is_chart_mode = False
        self.fetcher = None
        self._init_ui()
        self._init_menu()
    def _init_ui(self):
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["DateTime", "Symbol", "FocusDate"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setFixedWidth(LEFT_PANEL_WIDTH)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self.on_row_selected)
        self.canvas = KLineCanvas(self)
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.focus_updated.connect(self.on_focus_updated)
        self.scroll_area = QWidget()
        layout = QVBoxLayout(self.scroll_area)
        layout.addWidget(self.canvas)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.setStretchFactor(1, 1)
    def _init_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        open_act = QAction("Open File", self)
        open_act.triggered.connect(self.open_file)
        file_menu.addAction(open_act)
    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "", "Text Files (*.txt *.csv *.tsv);;All Files (*)")
        if filepath:
            self.items = DataParser.parse_file(filepath)
            self._populate_table()
    def _populate_table(self):
        self.table.setRowCount(0)
        for i, item in enumerate(self.items):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(item['datetime']))
            self.table.setItem(i, 1, QTableWidgetItem(item['symbol']))
            self.table.setItem(i, 2, QTableWidgetItem(str(item['focus_date'])))
    def on_row_selected(self, row: int, _col: int):
        if row < 0 or row >= len(self.items): return
        item = self.items[row]
        symbol = item['symbol']
        focus_date = item['focus_date']
        if symbol == self.current_symbol:
            df = self.cache.get(symbol)
            if df is not None:
                self.canvas.update_chart(df, focus_date)
                self.is_chart_mode = True
                return
        self._fetch_data(symbol, focus_date)
    def _fetch_data(self, symbol: str, focus_date: int):
        df = self.cache.get(symbol)
        if df is not None:
            self.current_symbol = symbol
            self.canvas.update_chart(df, focus_date)
            self.is_chart_mode = True
            return
        if self.fetcher and self.fetcher.isRunning():
            self.fetcher.quit()
        self.fetcher = DataFetcher(symbol, focus_date)
        self.fetcher.data_ready.connect(self._on_data_ready)
        self.fetcher.start()
    def _on_data_ready(self, symbol: str, df: pd.DataFrame, success: bool):
        if success:
            self.cache.put(symbol, df)
            self.current_symbol = symbol
            row = self.table.currentRow()
            focus_date = self.items[row]['focus_date'] if row >= 0 else 0
            self.canvas.update_chart(df, focus_date)
            self.is_chart_mode = True
        else:
            QMessageBox.warning(self, "Error", f"Failed to load data for {symbol}")
    def on_focus_updated(self, new_focus_date: int):
        row = self.table.currentRow()
        if row >= 0:
            self.items[row]['focus_date'] = new_focus_date
            self.table.setItem(row, 2, QTableWidgetItem(str(new_focus_date)))
    def keyPressEvent(self, event):
        if self.is_chart_mode:
            if event.key() == Qt.Key_Left:
                self.canvas.step_kline(-1)
            elif event.key() == Qt.Key_Right:
                self.canvas.step_kline(1)
            elif event.key() in (Qt.Key_Up, Qt.Key_Down):
                self._change_list_row(-1 if event.key() == Qt.Key_Up else 1)
            elif event.key() == Qt.Key_Escape:
                self.is_chart_mode = False
                QToolTip.hideText()
        else:
            if event.key() == Qt.Key_Up:
                self._change_list_row(-1)
            elif event.key() == Qt.Key_Down:
                self._change_list_row(1)
            elif event.key() == Qt.Key_Return:
                row = self.table.currentRow()
                if row >= 0: self.on_row_selected(row, 0)
        super().keyPressEvent(event)
    def _change_list_row(self, offset: int):
        row = self.table.currentRow()
        new_row = row + offset
        if 0 <= new_row < self.table.rowCount():
            self.table.selectRow(new_row)
            self.on_row_selected(new_row, 0)
# ==================== Application Entry ====================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())