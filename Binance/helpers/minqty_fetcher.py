from binance.spot import Spot
import csv

client = Spot()
trading_info = client.exchange_info()
symbols = [symbol['symbol'] for symbol in trading_info['symbols']]
minqty = {}
for symbol in symbols:
    filters = trading_info['symbols'][symbols.index(symbol)]['filters']
    for filter in filters:
        if filter['filterType'] == 'LOT_SIZE':
            minqty[symbol] = float(filter['minQty'])
            break
print(minqty)
with open('../data/min_qty.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(minqty.keys())
    writer.writerow(minqty.values())