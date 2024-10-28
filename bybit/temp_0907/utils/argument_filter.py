import pandas as pd
import numpy as np
import ast

# 读取Excel文件
df = pd.read_excel('result.xlsx', index_col=0)

# 使用 ast.literal_eval 来解析字典字符串
def parse_dict_string(dict_str):
    try:
        return ast.literal_eval(dict_str)
    except (ValueError, SyntaxError):
        return np.nan  # 如果解析失败，则返回 NaN

# 逐个单元格解析字典字符串
for col in df.columns:
    df[col] = df[col].apply(lambda x: parse_dict_string(x) if pd.notna(x) else np.nan)

# 根据 "profit_rate" 进行筛选，筛选出 "profit_rate" > 9 的单元格
def filter_condition(cell):
    if pd.isna(cell) or not isinstance(cell, dict):
        return np.nan
    profit_rate = cell.get('profit_rate', 0)
    max_drawdown = cell.get('max_drawdown', 0)
    if profit_rate > 1:
        return cell
    else:
        return np.nan

df_filtered = df.applymap(filter_condition)

# 筛选出不全是 NaN 的列
non_empty_columns = df_filtered.dropna(axis=1, how='all').columns.tolist()

# 输出不全是 NaN 的列名列表和长度
print("Non-empty columns:", non_empty_columns)
print("Number of non-empty columns:", len(non_empty_columns))

# 将过滤后的结果保存到新的Excel文件
df_filtered.to_excel('filtered_results.xlsx')

