"""
    手动平仓。
"""

from bybit_access import get_position
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
    try:
        print(
            http.place_order(category='linear', symbol=symbol, side='Sell', qty=0, reduceOnly=True, orderType='Market'))
    except Exception as e:
        print(e)
        pass
    try:
        print(
            http.place_order(category='linear', symbol=symbol, side='Buy', qty=0, reduceOnly=True, orderType='Market'))
    except Exception as e:
        print(e)
        pass
