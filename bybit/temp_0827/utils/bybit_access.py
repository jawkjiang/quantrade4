"""
    所有和bybit直接交互的接口必须在这个模块中重新实现，主要囊括到try-except结构，以及重试机制。
    捕获到exception时，需要向日志中记录错误信息，并重试。
    重试次数上限为5次，每次的间隔为当前的重试次数的平方乘以0.1秒。
"""

import logging
import time

from pybit.unified_trading import HTTP

def get_tickers(http: HTTP):
    for _ in range(5):
        try:
            tickers = http.get_tickers(category='linear')
            if tickers['retMsg'] == 'OK':
                return tickers
        except Exception as e:
            logging.error(f'Error occurred during get_tickers: {e}')
            time.sleep(0.1 * _ ** 2)
    raise SystemError('Failed to get tickers.')


def get_kline(http: HTTP, symbol: str, interval: str, limit: int, startTime: int, endTime: int):
    for _ in range(5):
        try:
            k_lines = http.get_kline(
                category='linear',
                symbol=symbol,
                interval=interval,
                limit=limit,
                startTime=startTime,
                endTime=endTime
            )
            if k_lines['retMsg'] == 'OK':
                return k_lines
        except Exception as e:
            logging.error(f'Error occurred during get_kline: {e}')
            time.sleep(0.1 * _ ** 2)
    raise SystemError('Failed to get kline.')


def get_marginBalance(http: HTTP):
    for _ in range(5):
        try:
            marginBalance = http.get_wallet_balance(accountType='UNIFIED')
            if marginBalance['retMsg'] == 'OK':
                return float(marginBalance['result']['list'][0]['totalMarginBalance'])
        except Exception as e:
            logging.error(f'Error occurred during get_marginBalance: {e}')
            time.sleep(0.1 * _ ** 2)
    raise SystemError('Failed to get margin balance.')


def place_order(http: HTTP, symbol: str, side: str, qty: float):
    for _ in range(5):
        try:
            order = http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Market')
            if order['retMsg'] == 'OK':
                return order
        except Exception as e:
            logging.error(f'Error occurred during place_order: {e}')
            time.sleep(0.1 * _ ** 2)
    raise SystemError('Failed to place order.')


def close_position(http: HTTP, symbol: str, side: str):
    for _ in range(5):
        try:
            order = http.place_order(category='linear', symbol=symbol, side=side, qty=0, reduceOnly=True, orderType='Market')
            if order['retMsg'] == 'OK':
                return order
        except Exception as e:
            logging.error(f'Error occurred during close_position: {e}')
            time.sleep(0.1 * _ ** 2)
    raise SystemError('Failed to close position.')
