# 安装依赖
pip install -r requirements.txt

# 测试模式（只抓取前1页）
python crawler.py --test 1

# 全量抓取所有66页
python crawler.py

# 断点续传（中断后直接再次运行即可）
python crawler.py

# 生成统计报告
python stats.py
