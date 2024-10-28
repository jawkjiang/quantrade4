"""
This helper is used to filter coins. It accepts a dict of coins and returns the most suitable coin.
"""
import pandas as pd


def filter_coin(data: pd.DataFrame, tick: int, entry_increase: float, history_time: int, price_limit: float):
    """
    Filter coin by side and rank rising the most or falling the most in the past history time.
    :param data: Restoring all open prices of coins, with columns as coins and rows as timestamps.
    :param tick: Number of current tick. Used as index.
    :param entry_increase: The minimum increase rate of the coin to be considered.
    :param history_time: The length of history time.
    :param price_limit: The minimum price of the coin to be considered.
    :return: symbols: list
    """

    # Filter
    filtered_coins = {}
    for symbol in data.columns:
        if tick - history_time < 0:
            continue
        if data[symbol][tick] < price_limit or data[symbol][tick - history_time] < price_limit:
            continue
        # 测试用，超过100块的币种不考虑
        if data[symbol][tick] > 100:
            continue
        profit_rate = data[symbol][tick] / data[symbol][tick - history_time] - 1
        if profit_rate > entry_increase:
            filtered_coins[symbol] = profit_rate

    # 如果没有符合条件的币种，返回空列表
    if not filtered_coins:
        return []

    # 选择增长率最高的前两个币种
    top_symbols = sorted(filtered_coins, key=filtered_coins.get, reverse=True)[:2]

    return top_symbols


