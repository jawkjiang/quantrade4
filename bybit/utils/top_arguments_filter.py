import pandas as pd
import ast
import json


def top_arguments_filter(json_file_path, excel_file_path, output_file_path):
    # 读取tickers_raw.json文件
    with open(json_file_path, 'r') as f:
        tickers_data = json.load(f)

    # 提取symbol对应的lastPrice
    symbol_last_price = {
        item['symbol']: float(item['lastPrice'])
        for item in tickers_data['result']['list']
    }

    # 筛选出lastPrice在0.01到100之间的symbol
    valid_symbols = [symbol for symbol, price in symbol_last_price.items() if 0.01 <= price <= 100]

    # 读取Excel文件
    df = pd.read_excel(excel_file_path, index_col=0)

    # 使用 ast.literal_eval 来解析字典字符串
    def parse_dict_string(dict_str):
        try:
            # 替换np.float64为float
            dict_str = dict_str.replace("np.float64(", "").replace(")", "")
            return ast.literal_eval(dict_str)
        except (ValueError, SyntaxError):
            return None

    # 解析index的函数
    def parse_index(index_str):
        parts = index_str.split('_')
        if len(parts) == 5:
            return {
                "Backtest_Entry_Increase": float(parts[0]),
                "Backtest_Exit_Increase": float(parts[1]),
                "Backtest_Exit_Decrease": float(parts[2]),
                "direction": parts[3],
                "single_trade_capital": float(parts[4])
            }
        return {}

    # 初始化存储结果的字典
    result = {}

    # 逐个列处理，仅保留valid_symbols中的列
    for col in df.columns:
        if col in valid_symbols:
            df[col] = df[col].apply(lambda x: parse_dict_string(x) if pd.notna(x) else None)

            # 获取profit_rate最高的行
            max_row = df[col].apply(
                lambda x: float(x['profit_rate']) if isinstance(x, dict) and 'profit_rate' in x else None
            ).idxmax()

            if pd.notna(max_row):
                max_profit_rate = df.loc[max_row, col]['profit_rate']
                trade_counts = df.loc[max_row, col].get('total_trades', None)
                parsed_index = parse_index(max_row)
                parsed_index['profit_rate'] = max_profit_rate
                parsed_index['total_trades'] = trade_counts
                result[col] = parsed_index

    # 按照 profit_rate 大小排序
    sorted_result = dict(sorted(result.items(), key=lambda item: item[1]['profit_rate'], reverse=True))

    # 将排序后的结果保存为json文件
    with open(output_file_path, 'w') as f:
        json.dump(sorted_result, f, indent=4)

    print(f"Results saved to {output_file_path}")
    return sorted_result


# 测试用例
if __name__ == "__main__":
    json_file_path = '../data/tickers_raw.json'
    excel_file_path = '../data/result.xlsx'
    output_file_path = 'max_profit_rates_filtered_sorted_2.json'

    result = top_arguments_filter(json_file_path, excel_file_path, output_file_path)
    print(result)
