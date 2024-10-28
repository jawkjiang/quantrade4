"""
    concat../../../data/k_lines下，最近14天的文件，即timestamp最大的14*12=168个文件，合并成一个dataframe，保存到merged.csv
"""

import os
import json
import pandas as pd


def data_process():
    dir_path = '../../data/k_lines'
    csv_files = [file for file in os.listdir(dir_path)]
    csv_files.sort(key=lambda x: int(x.split('.')[0]), reverse=True)
    # 提取最近10天的数据
    csv_files = csv_files[:120]
    df = pd.DataFrame()
    for i in range(len(csv_files)):
        file_path = os.path.join(dir_path, csv_files[i])
        temp_df = pd.read_csv(file_path)
        df = pd.concat([df, temp_df], ignore_index=True)
    # 保留价格在0.01~7 USDT的货币对
    with open('../../data/tickers_raw.json', 'r') as f:
        price_filter = json.load(f)
    for symbol in price_filter['result']['list']:
        if float(symbol['lastPrice']) < 0.01 or float(symbol['lastPrice']) > 7:
            try:
                df.drop(columns=symbol['symbol'], inplace=True)
            except KeyError:
                pass
    # 剔除存在空值的列
    df.dropna(axis=1, how='any', inplace=True)
    df.to_csv('../../data/merged.csv', index=False)


if __name__ == '__main__':
    data_process()

