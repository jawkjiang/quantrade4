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
    side = input('请输入side: ')
    qty = input('请输入qty: ')

    try:
        print(
            http.place_order(category='linear', symbol=symbol, side=side, qty=qty, orderType='Market'))
    except Exception as e:
        print(e)
        pass
