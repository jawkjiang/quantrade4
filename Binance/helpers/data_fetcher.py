"""
This module is responsible for fetching data from Binance.
Triggered only once.
"""

from binance.spot import Spot
import json
import os
import pandas as pd
import time

timestamp_start = 1703313600000
timestamp_end = 1715313600000
timestamp_step = 60000

client = Spot()
with open('../data/tickers.json', 'r') as f:
    tickers = json.load(f)
for ticker in tickers:
    symbol = list(ticker.keys())[0]
    if ticker[symbol] == 'waiting':
        timestamp_now = timestamp_start
        if not os.path.exists(f'../data/{symbol}'):
            os.mkdir(f'../data/{symbol}')
        while timestamp_now < timestamp_end:
            k_lines = client.klines(
                symbol=symbol,
                interval='1m',
                limit=1000,
                startTime=timestamp_now,
                endTime=timestamp_now + 999 * timestamp_step
            )
            df = pd.DataFrame(k_lines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'end_time',
                                                'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df.to_csv(f'../data/{symbol}/{symbol}-{timestamp_now}.csv', index=False)
            timestamp_now += 1000 * timestamp_step
            time.sleep(0.1)
        ticker[symbol] = 'done'
        with open('../data/tickers.json', 'w', newline='') as file:
            file.write(json.dumps(tickers, indent=4))
        print(f'{symbol} saved to file.')
