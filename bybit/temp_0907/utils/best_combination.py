import pandas as pd
import numpy as np
import ast

# 假设手续费率
fee_rate = 0.00055  # 根据实际情况调整

# 读取Excel文件
df = pd.read_excel('result.xlsx', index_col=0)

# 使用 ast.literal_eval 来解析元组字符串
def parse_tuple_string(tuple_str):
    try:
        return ast.literal_eval(tuple_str)
    except (ValueError, SyntaxError):
        return np.nan  # 如果解析失败，则返回 NaN

# 解析参数组合名称
def parse_parameters(index_name):
    params = index_name.split('_')
    return {
        'Backtest_Entry_Increase': float(params[0]),
        'Backtest_Exit_Increase': float(params[1]),
        'Backtest_Exit_Decrease': float(params[2]),
        'direction': params[3]
    }

# 调整后的盈利计算
def adjusted_profitability(trade_count, win_rate, params):
    if params['direction'] == 'long':
        adjusted_exit_increase = params['Backtest_Exit_Increase'] - 2 * fee_rate
        adjusted_exit_decrease = params['Backtest_Exit_Decrease'] + 2 * fee_rate
        return trade_count * (win_rate * adjusted_exit_increase - (1 - win_rate) * adjusted_exit_decrease)
    elif params['direction'] == 'short':
        adjusted_exit_increase = params['Backtest_Exit_Increase'] - 2 * fee_rate
        adjusted_exit_decrease = params['Backtest_Exit_Decrease'] + 2 * fee_rate
        return trade_count * (win_rate * adjusted_exit_decrease - (1 - win_rate) * adjusted_exit_increase)
    return np.nan

# 逐个单元格解析元组字符串
for col in df.columns:
    df[col] = df[col].apply(lambda x: parse_tuple_string(x) if pd.notna(x) else (0, 0))

# 筛选交易次数 >= 50 且胜率 >= 0.625 的参数组合
def filter_condition(cell):
    if pd.isna(cell) or cell == {}:
        return np.nan
    profit_rate = cell['profit_rate']
    if profit_rate > 9:
        return cell
    else:
        return np.nan


df_filtered = df.applymap(filter_condition)


# 计算新的盈利指标
def calculate_expected_profitability(cell, index_name):
    if pd.isna(cell) or cell == {}:
        return np.nan
    trade_count, win_rate = cell
    params = parse_parameters(index_name)
    return adjusted_profitability(trade_count, win_rate, params)


# 为每个货币对计算新的盈利指标并选出最佳组合
profitability_results = []

for col in df_filtered.columns:
    best_profitability = -np.inf
    best_combination = None
    best_combination_name = None

    for index in df_filtered.index:
        profitability = calculate_expected_profitability(df_filtered.loc[index, col], index)
        if pd.notna(profitability) and profitability > best_profitability:
            best_profitability = profitability
            best_combination = index
            best_combination_name = col

    profitability_results.append({
        'Currency Pair': best_combination_name,
        'Best Combination': best_combination,
        'Profitability': best_profitability
    })

# 将结果转换为 DataFrame
df_results = pd.DataFrame(profitability_results)

# 输出最佳参数组合和对应的收益
print("Best combinations with profitability:")
print(df_results)

# 将结果保存到Excel
df_results.to_excel('best_combinations_with_profitability.xlsx', index=False)
