"""
用于测试下单后，持仓能否实时更新。
选择如下4个时间点进行测试：
1. 下单后瞬间
2. 下单后15s
3. 下单后30s
4. 下单后60s
"""

import time
from bybit_access import get_position, get_tickers
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

    position = get_position(http)
    print(position)

    symbol = input('请输入symbol: ')
    side = input('请输入side: ')
    qty = input('请输入qty: ')

    try:
        print(
            http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Market'))
    except Exception as e:
        print(e)
        pass
    position = get_position(http)
    print('下单后瞬间')
    print(position)
    print('---------------------------------')

    # 测试如果部分平仓，会不会报错
    # 模拟止盈单部分filled的情况
    # try:
    #     tickers = get_tickers(http)['result']['list']
    #     last_price = 0
    #     for ticker in tickers:
    #         if ticker['symbol'] == symbol:
    #             last_price = float(ticker['lastPrice'])
    #     order_price = last_price * 0.99 if side == 'Buy' else last_price * 1.01
    #     print(
    #         http.place_order(category='linear', symbol=symbol, side='Sell' if side == 'Buy' else 'Buy', qty=str(int(qty)-5), orderType='Limit', price=str(order_price)))
    # except Exception as e:
    #     print(e)
    #     pass
    # position = get_position(http)
    # print('部分平仓后')
    # print(position)
    # print('---------------------------------')

    # 测试存在活动止盈单时，能否正常平仓
    try:
        tickers = get_tickers(http)['result']['list']
        last_price = 0
        for ticker in tickers:
            if ticker['symbol'] == symbol:
                last_price = float(ticker['lastPrice'])
        order_price = last_price * 1.01 if side == 'Buy' else last_price * 0.99
        order = http.place_order(category='linear', symbol=symbol, side='Sell' if side == 'Buy' else 'Buy', qty=qty, orderType='Limit', price=str(order_price))
        print(order)
    except Exception as e:
        print(e)
        pass
    position = get_position(http)
    print('挂活动止盈单后')
    print(position)
    print('---------------------------------')


    # # 尝试平仓的时候多平，看会不会报错
    # try:
    #     print(
    #         http.place_order(category='linear', symbol=symbol, side='Sell' if side == 'Buy' else 'Buy', qty=str(int(qty)+5), orderType='Market'))
    # except Exception as e:
    #     print(e)
    #     pass
    # position = get_position(http)
    # print('多平后')
    # print(position)
    # print('---------------------------------')
    # exit(0)

    # time.sleep(15)
    # position = get_position(http)
    # print('下单后15s')
    # print(position)
    # print('---------------------------------')
    # time.sleep(15)
    # position = get_position(http)
    # print('下单后30s')
    # print(position)
    # print('---------------------------------')
    # time.sleep(30)
    # position = get_position(http)
    # print('下单后60s')
    # print(position)
    # print('---------------------------------')

    """
    已发现问题所在：
    当账户内存在活动止盈单，且存在一定的杠杆时，平仓就会提示ab not enough。
    尝试先取消活动止盈单，再平仓。
    """

    # 平仓
    try:
        print(
            http.place_order(category='linear', symbol=symbol, side='Sell' if side == 'Buy' else 'Buy', qty=0, reduceOnly=True, orderType='Market'))
    except Exception as e:
        print(e)
        pass
    position = get_position(http)
    print('平仓后')
    print(position)

    # 取消原来的活动止盈单
    try:
        print(
            http.cancel_order(category='linear', symbol=symbol, orderId=order['result']['orderId']))
    except Exception as e:
        print(e)
        pass
    position = get_position(http)
    print('取消活动止盈单后')
    print(position)

