"""
    初筛。

    回测backtest中，每5个小时需要对300余支货币对进行初筛，规则如下：
    过去456小时（19日），对每支货币对进行纵向回测。
    若该货币对符合如下条件，则进场：
    最近2个openPrice中，若第二个较第一个上涨了2.2%，则做空进场
    上述条件若不符合，则最近3个openPrice中，若第三个较第一个上涨了2.2%，则做空进场
    进场后：
    若上涨1.1%，则平仓
    若下跌1.1%，也平仓
    筛选出如下两组货币对：
    第一组（标记为A组）：
    交易次数	胜率
    >=9	>63%
    =8	>7/8
    =7	>6/7
    =4~6	=100%
    =0~3	不考虑
    第二组（标记为B组）：
    交易次数	胜率
    >=9	<37%
    =8	<1/8
    =7	<1/7
    =4~6	=0%
    =0~3	不考虑
    （这个数值怎么来的我也不知道）
    筛选出两组货币后，若：
    A组的货币对支数 > 15支，则将A组按胜率正向排序，剔除胜率15名之外的货币对
    B组的货币对支数 > 15支，则将B组按胜率反向排序，剔除胜率15名之外的货币对

    注意，需求中数字极其蹊跷，不要写死，日后必改。
"""

import pandas as pd
from tqdm import tqdm
import json

with open('../../../constants.json', 'r') as f:
    constants = json.load(f)
    Time_Frame = constants['Time_Frame']
    Interval = constants['Interval']
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
def primary_filter(data: pd.DataFrame, tick: int, subBar: tqdm) -> tuple[list[str], list[str]]:
    """
    初筛。
    :param data: openPrice数据，每一行为一个timestamp，index为传入的tick；每一列为一个货币对的openPrice，column为货币对名
    :param tick: data的index，即当前时间点
    :param mainBar: tqdm进度条
    :return: A_group, B_group: A组和B组的货币对名列表
    """
    A_group, B_group = {}, {}
    for symbol in data.columns:
        # 如果价格过高或过低，跳过
        if data[symbol][tick] < 0.005 or data[symbol][tick] > 7:
            continue
        # 去除timestamp列
        if symbol == 'timestamp':
            continue
        judge_A, judge_B, win_rate = backtest(data, symbol, tick)
        if judge_A:
            A_group[symbol] = win_rate
        if judge_B:
            B_group[symbol] = win_rate
        subBar.update(1)
    A_group_filtered = filter_group(A_group, A_Win_Rate_Threshold)
    B_group_filtered = filter_group(B_group, B_Win_Rate_Threshold)

    return A_group_filtered, B_group_filtered


def backtest(data: pd.DataFrame, symbol: str, tick: int) -> tuple[bool, bool, float]:
    trade_count, win_rate = test(data, symbol, tick)
    mark_A, mark_B = False, False
    for i in range(len(A_Trade_Times)):
        if trade_count >= A_Trade_Times[i] and win_rate > A_Win_Rate[i]:
            mark_A = True
            break
    for i in range(len(B_Trade_Times)):
        if trade_count >= B_Trade_Times[i] and win_rate < B_Win_Rate[i]:
            mark_B = True
            break
    return mark_A, mark_B, win_rate


def test(data: pd.DataFrame, symbol: str, tick: int) -> tuple[int, float]:
    trade_count = 0
    win_count = 0
    entry_flag = True
    entry_price = 0
    for i in range(tick - Time_Frame, tick, 1):
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
    if len(group) > threshold:
        # 剔除胜率15名之外的货币对
        group = sorted(group, key=lambda x: group[x], reverse=True)[:threshold]
    else:
        group = list(group.keys())
    return group


if __name__ == '__main__':
    # 测试
    data = pd.read_csv('../../../data/merged/merged.csv')
    tick = 40000
    A_group, B_group = primary_filter(data, tick)
    print(A_group)
    print(B_group)