"""
    用于测试最合适的参数。
    1. 读取最近20天的全部数据，固定加载到内存中
    2. 遍历生成参数组合，在每个参数组合下，遍历所有货币对，计算A组和B组的交易次数和胜率
    3. 保存结果到excel文件，以symbol为index，参数组合、A组标记、B组标记、胜率、交易次数为columns
"""

import pandas as pd
import os
import math
import random
from helper import max_draw_down_calculate
import json

import tqdm


# 常量直接写在这里
Time_Frame = 10 * 24 * 60
Backtest_Entry_Time = 46
trading_fee = 0.00055
Backtest_Entry_Start = 14


def arguments_test(data: pd.DataFrame, df_result: pd.DataFrame, direction: str) -> pd.DataFrame:
    temp = pd.DataFrame(index=[0])
    for symbol in data.columns:
        if symbol == 'timestamp':
            continue
        # 把test函数的返回值保存到temp中
        temp.loc[0, symbol] = str(backtest(data, symbol, direction)[-1])
    # concat temp到df_result中，在此之前要标记行索引，为当前的参数组合+direction
    temp['parameters'] = f'{Backtest_Entry_Increase}_{Backtest_Exit_Increase}_{Backtest_Exit_Decrease}_{direction}_{single_trade_capital}'
    temp.set_index('parameters', inplace=True)
    df_result = pd.concat([df_result, temp])
    return df_result

def read_data() -> pd.DataFrame:
    df_temp = pd.DataFrame()
    # 读取../data/k_lines文件夹下，timestamp最新的n个文件，将这些文件合并
    # 首先排列文件
    file_list = os.listdir('../../data/k_lines')
    file_list.sort(key=lambda x: int(x.split('.')[0]))
    # 读取最新的n个文件，n = Time_Frame / 120
    n = Time_Frame // 120
    for i in range(n):
        file_path = os.path.join('../../data/k_lines', file_list[-n + i])
        df = pd.read_csv(file_path)
        df_temp = pd.concat([df_temp, df], ignore_index=True)
    return df_temp


def refine_data(data: pd.DataFrame) -> pd.DataFrame:
    # 读取../data/wide_group.json文件，只选择前50个货币对
    with open('../../data/wide_group.json', 'r') as f:
        group = json.load(f)
    for symbol in data.columns:
        if symbol == 'timestamp':
            continue
        if symbol not in list(group.keys())[0:50]:
            data.drop(columns=[symbol], inplace=True)
    return data


def backtest(data: pd.DataFrame, symbol: str, direction: str) -> tuple[float, float, float, str, dict]:
    try:
        indicators = test(data, symbol, direction)
    except ValueError:
        return 0, 0, 0, direction, {}
    return Backtest_Entry_Increase, Backtest_Exit_Increase, Backtest_Exit_Decrease, direction, indicators


def test(data: pd.DataFrame, symbol: str, direction: str) -> dict:
    entry_flag = True
    entry_price = 0
    capital = 1000
    balance = 1000
    position = 0
    indicators = {
        'total_trades': 0,
        'total_wins': 0,
        'total_loses': 0,
        'max_consecutive_wins': 0,
        'consecutive_wins': 0,  # 用于计算'consecutive_wins'
        'max_consecutive_loses': 0,
        'consecutive_loses': 0,  # 用于计算'consecutive_loses'
        'win_rate': 0.0,
        'peak_capital': 0.0,
        'profit_rate': 0.0,
        'peak_profit_rate': 0.0,
        'max_drawdown': 0.0,
        'total_profit': 0.0,
        'total_loss': 0.0,
        'profit_factor': 0.0,
    }
    for i in range(Backtest_Entry_Time, Time_Frame, 1):
        entry_price, entry_flag, capital, balance, position, indicators = \
            update(data, symbol, i, entry_flag, entry_price, direction, capital, balance, position, indicators)
    if indicators['total_trades'] == 0:
        indicators['win_rate'] = 0
    else:
        indicators['win_rate'] = indicators['total_wins'] / indicators['total_trades']
    if indicators['total_loss'] == 0:
        indicators['profit_factor'] = 0
    else:
        indicators['profit_factor'] = indicators['total_profit'] / indicators['total_loss']
    return indicators


def update(data: pd.DataFrame, symbol: str, inner_tick: int, entry_flag: bool, entry_price: float, direction: str, capital: float, balance: float, position: int, indicators: dict) -> tuple[float, bool, float, float, int, dict]:
    if entry_flag:
        entry_price, entry_flag, capital, balance, position = entry(data, symbol, inner_tick, direction, capital, balance)
    else:
        current_price = data[symbol][inner_tick]
        # 设置滑点为0.1%
        if direction == 'long':
            if current_price < entry_price * (1 - Backtest_Exit_Decrease):
                current_price = current_price * 0.999
                balance += position * current_price * (1 - trading_fee)
            elif current_price > entry_price * (1 + Backtest_Exit_Increase):
                balance += position * current_price * (1 - trading_fee)
            else:
                return entry_price, entry_flag, capital, balance, position, indicators
        elif direction == 'short':
            if current_price > entry_price * (1 + Backtest_Exit_Increase):
                current_price = current_price * 1.001
                balance -= position * current_price * (1 + trading_fee)
            elif current_price < entry_price * (1 - Backtest_Exit_Decrease):
                balance -= position * current_price * (1 + trading_fee)
            else:
                return entry_price, entry_flag, capital, balance, position, indicators
        else:
            return entry_price, entry_flag, capital, balance, position, indicators
        indicators['total_trades'] += 1
        difference = balance - capital
        if difference > 0:
            indicators['total_profit'] += difference
            indicators['total_wins'] += 1
            indicators['consecutive_wins'] += 1
            if indicators['consecutive_wins'] > indicators['max_consecutive_wins']:
                indicators['max_consecutive_wins'] = indicators['consecutive_wins']
            indicators['consecutive_loses'] = 0
        elif difference <= 0:
            indicators['total_loss'] -= difference
            indicators['total_loses'] += 1
            indicators['consecutive_loses'] += 1
            if indicators['consecutive_loses'] > indicators['max_consecutive_loses']:
                indicators['max_consecutive_loses'] = indicators['consecutive_loses']
            indicators['consecutive_wins'] = 0

        capital = balance
        if capital > indicators['peak_capital']:
            indicators['peak_capital'] = capital
        if capital < 50:
            raise ValueError('Capital is less than 50 USDT')
        indicators['profit_rate'] = capital / 1000 - 1
        if indicators['profit_rate'] > indicators['peak_profit_rate']:
            indicators['peak_profit_rate'] = indicators['profit_rate']
        indicators['max_drawdown'] = max_draw_down_calculate(capital, indicators['peak_capital'], indicators['max_drawdown'])

        entry_flag = True
        position = 0
    return entry_price, entry_flag, capital, balance, position, indicators


def entry(data: pd.DataFrame, symbol: str, inner_tick: int, direction: str, capital: float, balance: float) -> tuple[float, bool, float, float, int]:
    for j in range(Backtest_Entry_Start, Backtest_Entry_Time):
        current_price = data[symbol][inner_tick]
        if current_price < 0.01:
            return 0, True, capital, balance, 0
        history_price = data[symbol][inner_tick - j]
        if current_price > history_price * (1 + Backtest_Entry_Increase):
            # 符合进场条件，做空
            entry_price = data[symbol][inner_tick]
            # 标定本金采用之前的方式计算
            n = -8
            while capital >= 1000 * 2 ** n:
                n += 1
            standard_capital = 1000 * 2 ** n
            position = int(standard_capital * single_trade_capital / 1000 / Backtest_Entry_Increase / entry_price)
            if position == 0:
                return 0, True, capital, balance, 0
            if direction == 'long':
                balance -= position * entry_price * (1 + trading_fee)
            elif direction == 'short':
                balance += position * entry_price / (1 + trading_fee)
                
            return entry_price, False, capital, balance, position
    # 不符合进场条件，继续loop
    return 0, True, capital, balance, 0

 
def generate_random_parameters(num_groups):
    results = set()
    long_count = 0

    while len(results) < num_groups:
        # Step 1: Generate Backtest_Entry_Increase with step size 0.0005
        backtest_entry_increase = round(random.randint(60, 400) * 0.0002, 4)

        # Step 2: Calculate lower and upper bounds and apply ceil/floor
        lower_bound = math.ceil(backtest_entry_increase * 0.4 * 10000)  # Ceil to ensure the lower bound is rounded up
        upper_bound = math.floor(backtest_entry_increase * 0.6 * 10000)  # Floor to ensure the upper bound is rounded down

        backtest_exit_increase = round(random.randint(lower_bound, upper_bound) * 0.0001, 4)
        backtest_exit_decrease = round(random.randint(lower_bound, upper_bound) * 0.0001, 4)

        direction = random.choice(["long", "short"])

        if direction == "long":
            long_count += 1
            # exit_increase 应当大于 exit_decrease + 4 * fee_rate
            decrease_upper_bound = int(upper_bound - 4 * trading_fee * 10000)
            while backtest_exit_increase < backtest_exit_decrease + 4 * trading_fee:
                backtest_exit_increase = round(random.randint(lower_bound, upper_bound) * 0.0001, 4)
                # 为防死锁，exit_decrease也要重新生成
                backtest_exit_decrease = round(random.randint(lower_bound, decrease_upper_bound) * 0.0001, 4)

        elif direction == "short":
            # exit_decrease 应当大于 exit_increase + 4 * fee_rate
            increase_upper_bound = int(upper_bound - 4 * trading_fee * 10000)
            while backtest_exit_decrease < backtest_exit_increase + 4 * trading_fee:
                backtest_exit_decrease = round(random.randint(lower_bound, upper_bound) * 0.0001, 4)
                # 为防死锁，exit_increase也要重新生成
                backtest_exit_increase = round(random.randint(lower_bound, increase_upper_bound) * 0.0001, 4)

        single_trade_capital = random.choice([40, 60, 80, 100])

        # Create a tuple of the generated parameters
        param_tuple = (backtest_entry_increase, backtest_exit_increase, backtest_exit_decrease, direction, single_trade_capital)

        # Add the tuple to the results set to ensure uniqueness
        results.add(param_tuple)

        # Convert the set of tuples back to a list of dictionaries
    results_list = [
        {
            "Backtest_Entry_Increase": param[0],
            "Backtest_Exit_Increase": param[1],
            "Backtest_Exit_Decrease": param[2],
            "direction": param[3],
            "single_trade_capital": param[4]
        } for param in results
    ]

    return results_list


# 考虑随机参数生成改为穷举生成
def generate_parameters():
    results = []
    for entry_increase in range(60, 401):
        entry_increase = round(entry_increase * 0.0002, 4)
        for direction in ['long', 'short']:
            if direction == 'long':
                for exit_increase in range(int(entry_increase * 0.4 * 10000), int(entry_increase * 0.6 * 10000 + 1)):
                    exit_increase = round(exit_increase * 0.0001, 4)
                    for exit_decrease in range(int(entry_increase * 0.4 * 10000), int(entry_increase * 0.6 * 10000 + 1)):
                        exit_decrease = round(exit_decrease * 0.0001, 4)
                        if exit_increase >= exit_decrease + 4 * trading_fee:
                            results.append({
                                'Backtest_Entry_Increase': entry_increase,
                                'Backtest_Exit_Increase': exit_increase,
                                'Backtest_Exit_Decrease': exit_decrease,
                                'direction': direction
                            })
            elif direction == 'short':
                for exit_decrease in range(int(entry_increase * 0.4 * 10000), int(entry_increase * 0.6 * 10000 + 1)):
                    exit_decrease = round(exit_decrease * 0.0001, 4)
                    for exit_increase in range(int(entry_increase * 0.4 * 10000), int(entry_increase * 0.6 * 10000 + 1)):
                        exit_increase = round(exit_increase * 0.0001, 4)
                        if exit_decrease >= exit_increase + 4 * trading_fee:
                            results.append({
                                'Backtest_Entry_Increase': entry_increase,
                                'Backtest_Exit_Increase': exit_increase,
                                'Backtest_Exit_Decrease': exit_decrease,
                                'direction': direction
                            })
    return results


if __name__ == '__main__':
    global Backtest_Entry_Increase, Backtest_Exit_Increase, Backtest_Exit_Decrease, single_trade_capital
    data = read_data()
    data = refine_data(data)
    # 送进去loop
    df_result = pd.DataFrame()
    # 先读一遍data/result.xlsx，如果有内容，就直接跳过已经计算过的参数组合
    if os.path.exists('data/result.xlsx'):
        df_result = pd.read_excel('data/result.xlsx', index_col=0)
    # 生成参数组合
    parameters = generate_random_parameters(1000)
    print(parameters)
    # 写进度条
    with tqdm.tqdm(total=len(parameters)) as pbar:
        for param in parameters:
            Backtest_Entry_Increase = param["Backtest_Entry_Increase"]
            Backtest_Exit_Increase = param["Backtest_Exit_Increase"]
            Backtest_Exit_Decrease = param["Backtest_Exit_Decrease"]
            direction = param["direction"]
            single_trade_capital = param["single_trade_capital"]
            # 看看这个参数组合是否已经计算过
            if f'{Backtest_Entry_Increase}_{Backtest_Exit_Increase}_{Backtest_Exit_Decrease}_{direction}_{single_trade_capital}' in df_result.index:
                pbar.update(1)
                continue
            df_result = arguments_test(data, df_result, direction)
            df_result.to_excel('data/result.xlsx')
            pbar.update(1)

    """
    # 测试一组参数，这组参数有问题，测出来的结果很大
    Backtest_Entry_Increase = 0.0666
    Backtest_Exit_Increase = 0.0304
    Backtest_Exit_Decrease = 0.0393
    direction = 'short'
    single_trade_capital = 60
    df_result = arguments_test(data, df_result, direction)
    print(df_result)
    """




