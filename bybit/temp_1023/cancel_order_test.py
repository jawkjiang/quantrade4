"""
测试取消订单接口能否正常工作。
"""

from bybit_access import get_realtime_order, cancel_all_orders, get_tickers
from pybit.unified_trading import HTTP
import dotenv
import os

if __name__ == '__main__':

    dotenv.find_dotenv()
    dotenv.load_dotenv()
    http = HTTP(
        api_key=os.getenv('API_KEY_Wide'),
        api_secret=os.getenv('API_SECRET_Wide'),
        testnet=False
    )

    orders = get_realtime_order(http)
    print(orders)

    input('Enter to cancel all orders')
    cancel_all_orders(http)

    orders = get_realtime_order(http)
    print(orders)

    input('Enter to place an order')
    symbol = input('请输入symbol: ')
    side = input('请输入side: ')
    qty = input('请输入qty: ')

    price = 0
    tickers = get_tickers(http)['result']['list']
    for ticker in tickers:
        if ticker['symbol'] == symbol:
            price = float(ticker['lastPrice'])
            print(ticker)
            break

    # 为了保证不成交，设置一个不可能成交的价格
    price = price * 0.5 if side == 'Buy' else price * 1.5

    try:
        print(
            http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Limit', price=price))
    except Exception as e:
        print(e)
        pass

    orders = get_realtime_order(http)
    print(orders)

    input('Enter to cancel all orders')
    cancel_all_orders(http)

    orders = get_realtime_order(http)
    print(orders)

