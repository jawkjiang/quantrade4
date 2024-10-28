"""
    一次数据处理。
    由于回测数据量过大，且需要避免交易价格过低或过高的货币对，现在需要重新整理最近50000个tick， 且价格在0.01~7 USDT的货币对openPrice数据，最终存储在一张表中。

    src: ../data/merged/merged_*.csv，取最大的5个文件
    price_filter: ../data/tickers_raw.json
    dst: ../data/merged/merged.csv

"""

import os
import json
import pandas as pd


def data_process():
    dir_path = '../../../data/merged'
    csv_files = [file for file in os.listdir(dir_path) if file.startswith('merged_')]
    csv_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]), reverse=True)
    df = pd.DataFrame()
    for i in range(5):
        file_path = os.path.join(dir_path, csv_files[i])
        temp_df = pd.read_csv(file_path)
        df = pd.concat([df, temp_df], ignore_index=True)
    # 保留价格在0.01~7 USDT的货币对
    with open('../../../data/tickers_raw.json', 'r') as f:
        price_filter = json.load(f)
    for symbol in price_filter['result']['list']:
        if float(symbol['lastPrice']) < 0.01 or float(symbol['lastPrice']) > 7:
            df.drop(columns=symbol['symbol'], inplace=True)
    # 剔除存在空值的列
    df.dropna(axis=1, how='any', inplace=True)
    df.to_csv('../data/merged/merged.csv', index=False)


if __name__ == '__main__':
    data_process()

