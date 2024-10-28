"""
This helper is used to filter coins. It accepts a dict of coins and returns the most suitable coin.
"""

from indicator_calculator import slope_calculate as sc


def filter_coin(history_time: int, data_open: dict, data_close: dict, tick: int,
                rising_rate_restriction: float, slope_time: int, slope_rate: float, slope_history: int) -> str:
    """
    Filter coin by side and rank rising the most or falling the most in the past history time.
    :param history_time: past history time
    :param data_open: open prices of coins
    :param data_close: close prices of coins
    :param tick: current tick
    :param rising_rate_restriction: history rising rate restriction
    :param slope_time: length of sliding window
    :param slope_rate: slope rate
    :param slope_history: number of history slopes
    :return: symbol: str
    """
    # To boost efficiency, no use of sort() function here.
    if tick - (slope_history + slope_time) < 0:
        return ''
    filtered_coins = {}
    for symbol, open_prices in data_open.items():
        if open_prices[tick] < 0.1 or open_prices[tick - history_time] < 0.1 or open_prices[tick - slope_time - slope_history] < 0.1:
            continue
        profit_rate = data_close[symbol][tick] / open_prices[tick - history_time] - 1
        if profit_rate > rising_rate_restriction:
            print(f'{symbol} profit rate: {profit_rate}')
            try:
                slope = sc(open_prices, data_close[symbol], tick, slope_time)
                if slope == 0:
                    print(f'{symbol} not enough data to calculate slope.')
                    continue
                histories = []
                for i in range(slope_history):
                    histories.append(sc(open_prices, data_close[symbol], tick - i - 1, slope_time))
                if slope > max(histories) * (1 + slope_rate):
                    filtered_coins[symbol] = slope
                    print(f'{symbol} slope: {slope}')
                else:
                    continue
            except ValueError:
                continue
    if filtered_coins:
        return max(filtered_coins, key=filtered_coins.get)
    else:
        return ''

    # Origin codes in older versions
    """
    filtered_coins = {}
    for symbol, data in coins.items():
        if data[tick] < 2 or data[tick - history_time] < 2:
            continue
        if side == 'long':
            profit_rate = data[tick] / data[tick - history_time] - 1
        elif side == 'short':
            profit_rate = data[tick - history_time] / data[tick] - 1
        else:
            raise ValueError('side must be long or short.')
        if profit_rate > rising_rate_restriction:
            filtered_coins[symbol] = profit_rate
    while rank >= 0:
        if filtered_coins:
            max_symbol = max(filtered_coins, key=filtered_coins.get)
        else:
            return ''
        if rank == 0:
            return max_symbol
        else:
            filtered_coins.pop(max_symbol)
            if max_symbol not in banned_coins:
                rank -= 1
    return ''
    """

