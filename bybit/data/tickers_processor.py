"""
    把tickers_raw中的volume24h字段提取到pandas的dataframe中，保存到volume24h.csv
"""

import json
import pandas as pd


def data_process():

    with open('tickers_raw.json', 'r') as f:
        tickers = json.load(f)
    df = pd.DataFrame(tickers['result']['list'])
    df = df[['symbol', 'volume24h']]
    df.to_csv('volume24h.csv', index=False)


if __name__ == '__main__':
    data_process()