import json

# 读取之前生成的json文件
with open('max_profit_rates_filtered_sorted.json', 'r') as f:
    data = json.load(f)

# 设置要统计的前n项
n = 10  # 可以根据需要调整

# 设置目标total_trades的累加和阈值
threshold = 5760  # 可以根据需要调整

# 初始化变量
total_trades_sum = 0
count = 0

# 逐项累加total_trades，直到超过阈值
for key, value in data.items():
    total_trades = value.get('total_trades', 0)
    total_trades_sum += total_trades
    count += 1

    if total_trades_sum > threshold:
        break

# 输出当前统计的项数
print(f"Number of items when total_trades_sum exceeds {threshold}: {count}")
