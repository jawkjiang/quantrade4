"""
    初筛，该函数在data_fetch调用完之后调用，用于初筛符合交易条件的货币对。
    1. 读取../data/k_lines文件夹下，timestamp最新的84个文件，将这些文件合并。
    2. 计算的方法已经在之前temp文件夹里实现过了，直接搬过来就可以。
    注意：
    之前是一张整的大表，所以tick会随着loop更新，但是这里每次固定读取84张表，所以tick固定为84 * 120 = 10080。
"""


import pandas as pd
import os
import logging
import logging.config
import json

import dotenv
import os
from pybit.unified_trading import HTTP
from bybit_access import get_tickers

with open('../logging_config.json', 'r') as f:
    config = json.load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

dotenv.find_dotenv()
dotenv.load_dotenv()
http = HTTP(
    api_key=os.environ.get('API_KEY'),
    api_secret=os.environ.get('API_SECRET'),
    testnet=False
)

# 常量改由json读取
with open('../constants.json', 'r') as f:
    constants = json.load(f)
    Time_Frame = constants['Time_Frame']
    Backtest_Entry_Time = constants['Backtest_Entry_Time']
    Backtest_Entry_Increase = constants['Backtest_Entry_Increase']
    Backtest_Exit_Increase = constants['Backtest_Exit_Increase']
    Backtest_Exit_Decrease = constants['Backtest_Exit_Decrease']
    A_Win_Rate = constants['A_Win_Rate']
    A_Trade_Times = constants['A_Trade_Times']
    B_Win_Rate = constants['B_Win_Rate']
    B_Trade_Times = constants['B_Trade_Times']
    A_Win_Rate_Threshold = constants['A_Win_Rate_Threshold']
    B_Win_Rate_Threshold = constants['B_Win_Rate_Threshold']


# 注意面对复杂的函数功能时，应先写好函数的框架，再把框架中的功能分解到其它子函数中实现
def primary_filter() -> tuple[list[str], list[str]]:
    """
    初筛。
    :return: A_group, B_group: A组和B组的货币对名列表
    """
    # 读取data
    data = read_data()
    # 去除价格过高或过低的货币对
    data = refine_data(data)

    A_group, B_group = {}, {}
    for symbol in data.columns:
        # 去除timestamp列
        if symbol == 'timestamp':
            continue
        judge_A, judge_B, win_rate, trade_count = backtest(data, symbol)
        if judge_A:
            A_group[symbol] = win_rate
        if judge_B:
            B_group[symbol] = win_rate
    A_group_filtered = filter_group(A_group, A_Win_Rate_Threshold)
    B_group_filtered = filter_group(B_group, B_Win_Rate_Threshold)
    logging.info(f'A_group: {A_group_filtered}')
    logging.info(f'B_group: {B_group_filtered}')

    return A_group_filtered, B_group_filtered


def read_data() -> pd.DataFrame:
    df_temp = pd.DataFrame()
    # 读取../data/k_lines文件夹下，timestamp最新的84个文件，将这些文件合并
    # 首先排列文件
    file_list = os.listdir('../data/k_lines')
    file_list.sort(key=lambda x: int(x.split('.')[0]))
    # 读取最新的84个文件
    for i in range(84):
        file_path = os.path.join('../data/k_lines', file_list[-84 + i])
        df = pd.read_csv(file_path)
        df_temp = pd.concat([df_temp, df], ignore_index=True)
    return df_temp


def refine_data(data: pd.DataFrame) -> pd.DataFrame:
    for symbol in data.columns:
        # 去除价格过高或过低的货币对，直接以最后一个时间点的价格为准
        if data[symbol][Time_Frame - 1] > 7 or data[symbol][Time_Frame - 1] < 0.005:
            data.drop(columns=[symbol], inplace=True)
    return data


def backtest(data: pd.DataFrame, symbol: str) -> tuple[bool, bool, float, int]:
    trade_count, win_rate = test(data, symbol)
    mark_A, mark_B = False, False
    for i in range(len(A_Trade_Times)):
        if trade_count >= A_Trade_Times[i] and win_rate > A_Win_Rate[i]:
            mark_A = True
            break
    for i in range(len(B_Trade_Times)):
        if trade_count >= B_Trade_Times[i] and win_rate < B_Win_Rate[i]:
            mark_B = True
            break
    return mark_A, mark_B, win_rate, trade_count


def test(data: pd.DataFrame, symbol: str) -> tuple[int, float]:
    trade_count = 0
    win_count = 0
    entry_flag = True
    entry_price = 0
    for i in range(Backtest_Entry_Time, Time_Frame, 1):
        entry_price, entry_flag, trade_count, win_count = \
            update(data, symbol, i, entry_flag, entry_price, trade_count, win_count)
    if trade_count == 0:
        win_rate = 0
    else:
        win_rate = win_count / trade_count
    return trade_count, win_rate


def update(data: pd.DataFrame, symbol: str, inner_tick: int, entry_flag: bool, entry_price: float, trade_count: int,
           win_count: int) -> tuple[float, bool, int, int]:
    if entry_flag:
        entry_price, entry_flag = entry(data, symbol, inner_tick)
    else:
        current_price = data[symbol][inner_tick]
        if current_price > entry_price * (1 + Backtest_Exit_Increase):
            # 做空亏损，平仓
            trade_count += 1
            # 允许进场
            entry_flag = True
        elif current_price < entry_price * (1 - Backtest_Exit_Decrease):
            # 做空盈利，平仓
            trade_count += 1
            win_count += 1
            # 允许进场
            entry_flag = True
    return entry_price, entry_flag, trade_count, win_count


def entry(data: pd.DataFrame, symbol: str, inner_tick: int) -> tuple[float, bool]:
    for j in range(1, Backtest_Entry_Time):
        current_price = data[symbol][inner_tick]
        history_price = data[symbol][inner_tick - j]
        if current_price > history_price * (1 + Backtest_Entry_Increase):
            # 符合进场条件，做空
            entry_price = data[symbol][inner_tick]
            return entry_price, False
    # 不符合进场条件，继续loop
    return 0, True


def filter_group(group: dict[str], threshold: int) -> list[str]:
    # 弃用原来按胜率排序的方法，现在所有符合要求的货币对都能入选
    # 但是，需要重新fetch一遍tickers，按照volume24h排序，取前threshold个

    # fetch tickers
    tickers = get_tickers(http)['result']['list']
    # 提取dict，key为symbol，value为volume24h
    tickers_dict = {ticker['symbol']: float(ticker['volume24h']) for ticker in tickers}
    # 筛选只包含在group里的货币对
    tickers_dict = {symbol: volume for symbol, volume in tickers_dict.items() if symbol in group}
    # 按volume24h排序
    tickers_dict = dict(sorted(tickers_dict.items(), key=lambda item: item[1], reverse=True))
    # 取前threshold个
    tickers_list = list(tickers_dict.keys())[:threshold]
    return tickers_list

# 测试
if __name__ == '__main__':
    A_group, B_group = primary_filter()
    print(A_group)
    print(B_group)