from pybit.unified_trading import HTTP
import csv

session = HTTP(testnet=True)
trading_info = session.get_instruments_info(category='linear')['result']['list']
symbols = [symbol['symbol'] for symbol in trading_info]
minqty = {}
for symbol in symbols:
    filter = trading_info[symbols.index(symbol)]['lotSizeFilter']
    minqty[symbol] = float(filter['minOrderQty'])
print(minqty)
with open('../../data/min_qty.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(minqty.keys())
    writer.writerow(minqty.values())