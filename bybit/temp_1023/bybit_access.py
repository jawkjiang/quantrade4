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
            logging.error(f'Exception occurred during get_tickers: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get tickers.')


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
            logging.error(f'Exception occurred during get_kline: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get kline.')


def get_marginBalance(http: HTTP):
    for _ in range(5):
        try:
            marginBalance = http.get_wallet_balance(accountType='UNIFIED')
            if marginBalance['retMsg'] == 'OK':
                logging.info(f'Margin balance fetched successfully: {marginBalance["result"]["list"][0]["totalMarginBalance"]}')
                return float(marginBalance['result']['list'][0]['totalMarginBalance'])
        except Exception as e:
            logging.error(f'Exception occurred during get_marginBalance: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get margin balance.')


def place_order(http: HTTP, symbol: str, side: str, qty: float):
    for _ in range(5):
        try:
            # 规范side首字母大写
            side = side.capitalize()
            order = http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Market')
            if order['retMsg'] == 'OK':
                logging.info(f'Order placed successfully: {symbol} {side} {qty}')
                return order
        except Exception as e:
            logging.error(f'Exception occurred during place_order: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to place order.')


def place_limit_order(http: HTTP, symbol: str, side: str, qty: float, price: float):
    for _ in range(5):
        try:
            # 规范side首字母大写
            side = side.capitalize()
            order = http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Limit', price=price)
            if order['retMsg'] == 'OK':
                logging.info(f'Limit order placed successfully: {symbol} {side} {qty} {price}')
                return order
        except Exception as e:
            logging.error(f'Exception occurred during place_limit_order: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to place limit order.')


def place_sltp_order(http: HTTP, symbol: str, side: str, qty: float, slprice: float = None, tpprice: float = None):
    for _ in range(5):
        try:
            # 规范side首字母大写
            side = side.capitalize()
            if slprice is None:
                order = http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Market', takeProfit=tpprice, tpLimitPrice=tpprice, tpOrderType="Limit", tpslMode='Partial')
            else:
                order = http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Market', stopLoss=slprice, takeProfit=tpprice, tpslMode='Full')
            if order['retMsg'] == 'OK':
                logging.info(f'SL/TP order placed successfully: {symbol} {side} {qty} SL: {slprice} TP: {tpprice}')
                return order
        except Exception as e:
            logging.error(f'Exception occurred during place_sltp_order: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to place SL/TP order.')


def close_position(http: HTTP, symbol: str, side: str):
    for _ in range(5):
        try:
            # 规范side首字母大写
            side = side.capitalize()
            order = http.place_order(category='linear', symbol=symbol, side=side, qty=0, reduceOnly=True, orderType='Market')
            if order['retMsg'] == 'OK':
                logging.info(f'Position closed successfully: {symbol} {side}')
                return order
        except Exception as e:
            logging.error(f'Exception occurred during close_position: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to close position.')

def get_open_orders(http: HTTP, order_id: str = None):
    for _ in range(5):
        try:
            if order_id is None:
                orders = http.get_open_orders(category='linear', baseCoin='USDT')
            else:
                orders = http.get_open_orders(category='linear', orderId=order_id)
            if orders['retMsg'] == 'OK':
                return orders
        except Exception as e:
            logging.error(f'Exception occurred during get_open_orders: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get open orders.')


def cancel_order(http: HTTP, symbol: str, order_id: str):
    for _ in range(5):
        try:
            order = http.cancel_order(category='linear', symbol=symbol, orderId=order_id)
            if order['retMsg'] == 'OK':
                logging.info(f'Order cancelled successfully: {order_id}')
                return order
        except Exception as e:
            logging.error(f'Exception occurred during cancel_order: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to cancel order.')


def get_position(http: HTTP):
    for _ in range(5):
        try:
            position = http.get_positions(category='linear', settleCoin='USDT')
            if position['retMsg'] == 'OK':
                return position
        except Exception as e:
            logging.error(f'Exception occurred during get_position: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get position.')

# 新增获取抵押余额的接口
def get_collateral_info(http: HTTP):
    for _ in range(5):
        try:
            position = http.get_collateral_info()
            if position['retMsg'] == 'OK':
                return position
        except Exception as e:
            logging.error(f'Exception occurred during get_position: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get collateral info.')

# 新增获取杠杆信息的接口
def get_leverage(http: HTTP):
    for _ in range(5):
        try:
            leverage = http.spot_margin_trade_get_status_and_leverage()
            if leverage['retMsg'] == 'OK':
                return leverage
        except Exception as e:
            logging.error(f'Exception occurred during get_leverage: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get leverage.')

# 新增钱包余额查询接口
def get_wallet_balance(http: HTTP):
    for _ in range(5):
        try:
            wallet_balance = http.get_wallet_balance(accountType='UNIFIED')
            if wallet_balance['retMsg'] == 'OK':
                return wallet_balance
        except Exception as e:
            logging.error(f'Exception occurred during get_wallet_balance: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get wallet balance.')

# 新增获取历史订单的接口
def get_order_history(http: HTTP, limit: int = 20):
    for _ in range(5):
        try:
            order_history = http.get_order_history(category='linear', limit=limit)
            if order_history['retMsg'] == 'OK':
                return order_history
        except Exception as e:
            logging.error(f'Exception occurred during get_order_history: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get order history.')


# 新增查询实时订单的接口
def get_realtime_order(http: HTTP):
    for _ in range(5):
        try:
            realtime_order = http.get_open_orders(category='linear', settleCoin='USDT')
            if realtime_order['retMsg'] == 'OK':
                return realtime_order
        except Exception as e:
            logging.error(f'Exception occurred during get_realtime_order: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to get realtime order.')


# 新增撤销所有委托单的接口
def cancel_all_orders(http: HTTP):
    for _ in range(5):
        try:
            cancel_all = http.cancel_all_orders(category='linear', settleCoin='USDT')
            if cancel_all['retMsg'] == 'OK':
                return cancel_all
        except Exception as e:
            logging.error(f'Exception occurred during cancel_all_orders: {e}')
            time.sleep(0.1 * _ ** 2)
    raise Exception('Failed to cancel all orders.')


# 接口测试
if __name__ == '__main__':
    import dotenv
    import os
    dotenv.find_dotenv()
    dotenv.load_dotenv()
    http = HTTP(
        api_key=os.getenv('API_KEY_Wide'),
        api_secret=os.getenv('API_SECRET_Wide'),
        testnet=False
    )
    """
    tickers = get_tickers(http)['result']['list']
    # 买0.1个TOMIUSDT进行测试
    last_price = 0
    for ticker in tickers:
        if ticker['symbol'] == 'TOMIUSDT':
            last_price = float(ticker['lastPrice'])
        # 测试place_limit_order、cancel_order
    order = place_limit_order(http, 'TOMIUSDT', 'buy', 150, round(last_price*0.8, 4))
    print(last_price*100)
    print(order)
    try:
        cancel_text = cancel_order(http, 'TOMIUSDT', order['result']['orderId'])
        print("cancel"+str(cancel_text))
    except Exception as e:
        print(e)
        pass
    # 测试get_open_orders
    open_orders = get_open_orders(http)
    print(open_orders)

    # 测试get_position
    position = get_position(http)
    print(position)

    # 获取position中所有存在仓位的symbol
    symbols = [each['symbol'] for each in position['result']['list']]
    # 测试close_position
    for symbol in symbols:
        try:
            print(http.place_order(category='linear', symbol=symbol, side='Sell', qty=0, reduceOnly=True, orderType='Market'))
        except Exception as e:
            print(e)
            pass
        try:
            print(http.place_order(category='linear', symbol=symbol, side='Buy', qty=0, reduceOnly=True, orderType='Market'))
        except Exception as e:
            print(e)
            pass
    
    """
    # 只测试get_position
    position = get_position(http)
    print(position)

    # 测试get_marginBalance
    marginBalance = get_marginBalance(http)
    print(marginBalance)

    # 测试get_leverage
    leverage = get_leverage(http)
    print(leverage)

    # 测试get_wallet_balance
    wallet_balance = get_wallet_balance(http)
    print(wallet_balance)
