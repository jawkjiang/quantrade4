import json

# 要保留的键列表
keys_to_keep = [
    "TOMIUSDT", "A8USDT", "PIXFIUSDT", "LITUSDT",
    "CEEKUSDT", "MOCAUSDT", "10000COOUSDT", "BONDUSDT", "GFTUSDT"
]

# 读取 JSON 文件
with open('group.json', 'r') as file:
    data = json.load(file)

# 筛选数据，只保留指定的键
filtered_data = {key: data[key] for key in keys_to_keep if key in data}

# 将筛选后的数据写入一个新的 JSON 文件
with open('filtered_group.json', 'w') as file:
    json.dump(filtered_data, file, indent=4)

print("筛选后的数据已保存到 'filtered_group.json' 文件中。")
