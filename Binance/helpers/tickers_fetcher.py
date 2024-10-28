"""
This module is responsible for fetching tickers from Binance.
"""

from binance.spot import Spot
import json

client = Spot()
tickers = client.ticker_price()

"""
tickers = [
    {
        "symbol": "BTCUSDT",
        "price": "10000"
    },
    {
        "symbol": "ETHUSDT",
        "price": "300"
    },
    ...
]
"""
print(tickers)
with open('../data/tickers_raw.json', 'w') as f:
    json.dump(tickers, f, indent=4)

exit()
# clear out crypto pairs whose price is less than 0.1
tickers = [ticker for ticker in tickers if float(ticker['price']) >= 0.1]

ticker_status = [{ticker['symbol']: 'waiting'} for ticker in tickers]

print(ticker_status)

with open('../data/tickers.json', 'w') as f:
    json.dump(ticker_status, f, indent=4)
