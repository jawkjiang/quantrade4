"""
    本模块用于从bybit API获取数据。获取规则如下：
    1. 以1分钟为单位获取数据，获取的数据只包含timestamp和open字段
    2. 从timestamp_start开始，每次获取1000分钟的数据
    3. 一共获取500次，即500 * 1000分钟的数据
"""

import pandas as pd

from pybit.unified_trading import HTTP
import time
import json
import os


def data_fetcher(timestamp_start, timestamp_end, timestamp_step):
    session = HTTP(testnet=True)
    with open('../../data/tickers_status.json', 'r') as f:
        tickers = json.load(f)
    for ticker, status in tickers.items():
        try:
            if status == 'waiting' or status == 'error':
                # 设定计时器
                time_start = time.time()
                timestamp_now = timestamp_start
                if not os.path.exists(f'../data/{ticker}'):
                    os.mkdir(f'../data/{ticker}')
                while timestamp_now < timestamp_end:
                    k_lines = session.get_kline(
                        category='linear',
                        symbol=ticker,
                        interval='1',
                        limit=1000,
                        startTime=timestamp_now,
                        endTime=timestamp_now + 999 * timestamp_step
                    )
                    if k_lines['retMsg'] == 'OK':
                        df = pd.DataFrame(k_lines['result']['list'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
                        df = df[['timestamp', 'open']]
                        df.to_csv(f'../data/{ticker}/{ticker}-{timestamp_now}.csv', index=False)
                        timestamp_now += 1000 * timestamp_step
                        time.sleep(0.1)
                tickers[ticker] = 'done'
                with open('../../data/tickers_status.json', 'w', newline='') as file:
                    file.write(json.dumps(tickers, indent=4))
                print(f'{ticker} saved to file.')
                print(f'Time spent: {time.time() - time_start}')
        except Exception as e:
            print(f'Error: {e}')
            tickers[ticker] = 'error'
            with open('../../data/tickers_status.json', 'w', newline='') as file:
                file.write(json.dumps(tickers, indent=4))
            print(f'{ticker} status set to error.')
            continue


if __name__ == '__main__':
    timestamp_end = 1723392000000
    # 往上500*1000分钟，即500*1000*60*1000毫秒
    timestamp_start = timestamp_end - 500 * 1000 * 60 * 1000
    timestamp_step = 60000
    data_fetcher(timestamp_start, timestamp_end, timestamp_step)
