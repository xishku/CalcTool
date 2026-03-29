import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# 1. 数据准备
data = {
    '月份': ['Oct-24', 'Nov-24', 'Dec-24', 'Jan-25', 'Feb-25', 'Mar-25', 
           'Apr-25', 'May-25', 'Jun-25', 'Jul-25', 'Aug-25', 'Sep-25', 
           'Oct-25', 'Nov-25', 'Dec-25', 'Jan-26', 'Feb-26', 'Mar-26'],
    '行车里程': [1276.2, 1417.2, 1790.8, 2194.3, 1154.3, 1537.9, 
                1338.7, 1235.2, 1426.3, 1780.0, 1094.5, 644.8, 
                1302.5, 449.6, 337.2, 389.4, 1350.9, 337.4],
    '总能耗': [184.2, 209.9, 274.7, 362.2, 174.7, 233.8, 
              179.6, 160.9, 195.4, 252.1, 144.3, 86.7, 
              214.0, 67.3, 53.2, 63.9, 233.6, 54.3],
    '平均能耗': [14.4, 14.8, 15.3, 16.5, 15.1, 15.2, 
                13.4, 13.0, 13.7, 14.2, 13.2, 13.4, 
                16.4, 15.0, 15.8, 16.4, 17.3, 16.1],
    '行车天数': [18, 29, 29, 29, 25, 25, 
                30, 27, 28, 25, 24, 15, 
                24, 24, 26, 22, 23, 19]
}

df = pd.DataFrame(data)

# 转换日期格式
month_map = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6, 
             'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}
df['date'] = df['月份'].apply(lambda x: pd.to_datetime(f"20{x.split('-')[1]}-{month_map[x.split('-')[0]]}-01"))

# 设置绘图风格
sns.set_theme(style="whitegrid", font='SimHei') 
plt.rcParams['axes.unicode_minus'] = False 

# --- 布局调整 ---
# 整体高度稍微降低一点，因为第三个图变小了
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 20))
plt.subplots_adjust(hspace=0.35) 

fig.suptitle('车辆能耗与行驶数据分析 (2024.10 - 2026.03)', fontsize=20, y=0.95)

# --- 图表 1: 平均能耗趋势 (Y轴 10-18) ---
ax1.fill_between(df['date'], df['平均能耗'], color="#55a868", alpha=0.2)
line1 = ax1.plot(df['date'], df['平均能耗'], color="#55a868", marker='s', linewidth=2, linestyle='-')
ax1.set_ylabel('平均能耗 (kWh/100km)', fontsize=12, labelpad=15) 
ax1.set_title('百公里平均能耗趋势', fontsize=14, loc='left', pad=20) 
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

# 【修改点】设置Y轴范围 10-18
ax1.set_ylim(12, 18)

# 数据标签
for i, txt in enumerate(df['平均能耗']):
    ax1.annotate(f"{txt}", (df['date'][i], df['平均能耗'][i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color='#2c5e38')


# --- 图表 2: 行车里程 vs 总能耗 ---
bars2 = ax2.bar(df['date'], df['行车里程'], color='#4c72b0', alpha=0.6, label='行车里程 (km)', width=20)
ax2.set_ylabel('行车里程 (km)', fontsize=12, labelpad=15)
ax2.set_title('月度行车里程与总能耗', fontsize=14, loc='left', pad=20)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

# 数据标签 - 里程
for bar in bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2, height, f"{height:.0f}", ha='center', va='bottom', fontsize=9)

# 双Y轴 - 总能耗
ax2_energy = ax2.twinx()
line2 = ax2_energy.plot(df['date'], df['总能耗'], color='#c44e52', marker='o', linewidth=2, label='总能耗 (kWh)')
ax2_energy.set_ylabel('总能耗 (kWh)', fontsize=12, labelpad=15)
ax2_energy.tick_params(axis='y', labelcolor='#c44e52')

# 数据标签 - 总能耗
for i, txt in enumerate(df['总能耗']):
    ax2_energy.annotate(f"{txt}", (df['date'][i], df['总能耗'][i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color='#8b3626')

# 图例
lines_1, labels_1 = ax2.get_legend_handles_labels()
lines_2, labels_2 = ax2_energy.get_legend_handles_labels()
ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left')

# --- 图表 3: 行车天数 (Y轴 15-30) ---
bars3 = ax3.bar(df['date'], df['行车天数'], color='#ddb125', alpha=0.7)
ax3.set_ylabel('行车天数 (天)', fontsize=12, labelpad=15)
ax3.set_xlabel('日期', fontsize=12, labelpad=15)
ax3.set_title('每月行车天数', fontsize=14, loc='left', pad=20)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

# 【修改点】设置Y轴范围 15-30
ax3.set_ylim(15, 30)

# 数据标签 - 注意：低于15的数据（如Sep-25的15天）可能会被切掉，这里强制显示在柱子顶端
for bar in bars3:
    height = bar.get_height()
    # 如果高度小于15，标签显示在15的位置上方，否则显示在高度位置
    y_pos = max(height, 15) 
    ax3.text(bar.get_x() + bar.get_width()/2, y_pos, f"{int(height)}", ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.show()