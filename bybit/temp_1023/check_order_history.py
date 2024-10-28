"""
检查订单历史。
"""

from bybit_access import get_order_history
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

    history = get_order_history(http)
    print(history)
