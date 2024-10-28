"""
    此模块用于获取交易所的所有交易对信息，仅筛选出：
    1. USDT合约
    2. lastPrice > 0.01
    的交易对
"""

from pybit.unified_trading import HTTP
import json
import logging

logging.basicConfig(level=logging.INFO, encoding='utf-8', format='%(name)s - %(levelname)s - %(asctime)s - %(message)s ',
                    datefmt='%y-%m-%d %H:%M:%S')


def tickers_fetcher():
    session = HTTP(testnet=True)
    tickers = session.get_tickers(category='linear')
    if tickers['retMsg'] == 'OK':
        tickers['result']['list'] = [ticker for ticker in tickers['result']['list'] if float(ticker['lastPrice']) >= 0.01]
        tickers['result']['list'] = [ticker for ticker in tickers['result']['list'] if ticker['symbol'].endswith('USDT')]
        with open('../../data/tickers_raw.json', 'w') as file:
            file.write(json.dumps(tickers, indent=4))
        symbols = {each['symbol']: 'waiting' for each in tickers['result']['list']}
        with open('../../data/tickers_status.json', 'w', newline='') as file:
            file.write(json.dumps(symbols, indent=4))
        logging.info('Tickers_status saved to file.')


if __name__ == '__main__':
    tickers_fetcher()
