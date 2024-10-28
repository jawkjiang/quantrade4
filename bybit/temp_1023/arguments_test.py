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


# 常量直接写在这里
Time_Frame = 10 * 24 * 60
Backtest_Entry_Time = 46
trading_fee = 0.00055
Backtest_Entry_Start = 14



class ArgumentsTest:

    def __init__(self):
        self.data = pd.DataFrame()
        self.df_result = pd.DataFrame()
        self.parameters = []
        self.Backtest_Entry_Increase = 0
        self.Backtest_Exit_Increase = 0
        self.Backtest_Exit_Decrease = 0
        self.direction = ''
        self.single_trade_capital = 0

    def initialize(self):
        self.data = self.read_data()
        self.data = self.refine_data(self.data)
        self.parameters = self.generate_random_parameters(1000)

    def run(self, param):
        self.Backtest_Entry_Increase = param["Backtest_Entry_Increase"]
        self.Backtest_Exit_Increase = param["Backtest_Exit_Increase"]
        self.Backtest_Exit_Decrease = param["Backtest_Exit_Decrease"]
        self.direction = param["direction"]
        self.single_trade_capital = param["single_trade_capital"]
        if f'{self.Backtest_Entry_Increase}_{self.Backtest_Exit_Increase}_{self.Backtest_Exit_Decrease}_{self.direction}_{self.single_trade_capital}' in self.df_result.index:
            return
        self.df_result = self.arguments_test()

    def arguments_test(self):
        temp = pd.DataFrame(index=[0])
        for symbol in self.data.columns:
            if symbol == 'timestamp':
                continue
            # 把test函数的返回值保存到temp中
            temp.loc[0, symbol] = str(self.backtest(symbol)[-1])
        # concat temp到df_result中，在此之前要标记行索引，为当前的参数组合+direction
        temp['parameters'] = f'{self.Backtest_Entry_Increase}_{self.Backtest_Exit_Increase}_{self.Backtest_Exit_Decrease}_{self.direction}_{self.single_trade_capital}'
        temp.set_index('parameters', inplace=True)
        self.df_result = pd.concat([self.df_result, temp])
        return self.df_result

    def read_data(self):
        df_temp = pd.DataFrame()
        # 读取../data/k_lines文件夹下，timestamp最新的n个文件，将这些文件合并
        # 首先排列文件
        file_list = os.listdir('../data/k_lines')
        file_list.sort(key=lambda x: int(x.split('.')[0]))
        # 读取最新的n个文件，n = Time_Frame / 120
        n = Time_Frame // 120
        for i in range(n):
            file_path = os.path.join('../data/k_lines', file_list[-n + i])
            df = pd.read_csv(file_path)
            df_temp = pd.concat([df_temp, df], ignore_index=True)
        return df_temp

    def refine_data(self, data: pd.DataFrame) -> pd.DataFrame:
        # 读取../data/wide_group.json文件，首先选择前50个货币对
        with open('../data/wide_group.json', 'r') as f:
            group = json.load(f)
        group_keys = list(group.keys())
        # 从数据中剔除timestamp列和已经选取的50个货币对
        available_keys = [col for col in data.columns if col not in group_keys and col != 'timestamp']
        # 读取../data/tickers_raw.json文件，获取所有货币对
        with open('../data/tickers_raw.json', 'r') as f:
            tickers = json.load(f)
        tickers = {each['symbol']: each for each in tickers['result']['list']}
        # 筛选价格0.01到100的货币对
        available_keys = [key for key in available_keys if 0.01 <= float(tickers[key]['lastPrice']) <= 100]
        # 随机选择50个货币对
        if len(available_keys) > 50:
            random_50 = random.sample(available_keys, 50)
        else:
            random_50 = available_keys  # 如果不足50个，选择所有剩余的货币对
        # 合并两个列表
        selected_symbols = group_keys + random_50
        # 过滤数据框架以仅包含选择的100个货币对加上timestamp
        data = data[['timestamp'] + [symbol for symbol in selected_symbols if symbol in data.columns]]
        print(data.columns)
        return data

    def backtest(self, symbol: str) -> tuple[float, float, float, str, dict]:
        try:
            indicators = self.test(symbol)
        except ValueError:
            return 0, 0, 0, self.direction, {}
        return self.Backtest_Entry_Increase, self.Backtest_Exit_Increase, self.Backtest_Exit_Decrease, self.direction, indicators

    def test(self, symbol: str) -> dict:
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
                self.update(symbol, i, entry_flag, entry_price, capital, balance, position, indicators)
        if indicators['total_trades'] == 0:
            indicators['win_rate'] = 0
        else:
            indicators['win_rate'] = indicators['total_wins'] / indicators['total_trades']
        if indicators['total_loss'] == 0:
            indicators['profit_factor'] = 0
        else:
            indicators['profit_factor'] = indicators['total_profit'] / indicators['total_loss']
        return indicators

    def update(self, symbol: str, inner_tick: int, entry_flag: bool, entry_price: float, capital: float, balance: float, position: int, indicators: dict) -> tuple[float, bool, float, float, int, dict]:
        if entry_flag:
            entry_price, entry_flag, capital, balance, position = self.entry(symbol, inner_tick, capital, balance)
        else:
            current_price = self.data[symbol][inner_tick]
            # 设置滑点为0.1%
            if self.direction == 'long':
                if current_price < entry_price * (1 - self.Backtest_Exit_Decrease):
                    current_price = current_price * 0.999
                    balance += position * current_price * (1 - trading_fee)
                elif current_price > entry_price * (1 + self.Backtest_Exit_Increase):
                    balance += position * current_price * (1 - trading_fee)
                else:
                    return entry_price, entry_flag, capital, balance, position, indicators
            elif self.direction == 'short':
                if current_price > entry_price * (1 + self.Backtest_Exit_Increase):
                    current_price = current_price * 1.001
                    balance -= position * current_price * (1 + trading_fee)
                elif current_price < entry_price * (1 - self.Backtest_Exit_Decrease):
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

    def entry(self, symbol: str, inner_tick: int, capital: float, balance: float) -> tuple[float, bool, float, float, int]:
        for j in range(Backtest_Entry_Start, Backtest_Entry_Time):
            current_price = self.data[symbol][inner_tick]
            if current_price < 0.01:
                return 0, True, capital, balance, 0
            history_price = self.data[symbol][inner_tick - j]
            if current_price > history_price * (1 + self.Backtest_Entry_Increase):
                # 符合进场条���，做空
                entry_price = self.data[symbol][inner_tick]
                # 标定本金采用之前的方式计算
                n = -8
                while capital >= 1000 * 2 ** n:
                    n += 1
                standard_capital = 1000 * 2 ** n
                position = int(standard_capital * self.single_trade_capital / 1000 / self.Backtest_Entry_Increase / entry_price)
                if position == 0:
                    return 0, True, capital, balance, 0
                if self.direction == 'long':
                    balance -= position * entry_price * (1 + trading_fee)
                elif self.direction == 'short':
                    balance += position * entry_price / (1 + trading_fee)

                return entry_price, False, capital, balance, position
        # 不符合进场条件，继续loop
        return 0, True, capital, balance, 0

    @staticmethod
    def generate_random_parameters(num_groups):
        results = set()
        long_count = 0

        while len(results) < num_groups:
            # Step 1: Generate Backtest_Entry_Increase with step size 0.0005
            backtest_entry_increase = round(random.randint(60, 400) * 0.0002, 4)

            # Step 2: Calculate lower and upper bounds and apply ceil/floor
            lower_bound = math.ceil(
                backtest_entry_increase * 0.4 * 10000)  # Ceil to ensure the lower bound is rounded up
            upper_bound = math.floor(
                backtest_entry_increase * 0.6 * 10000)  # Floor to ensure the upper bound is rounded down

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
            param_tuple = (
            backtest_entry_increase, backtest_exit_increase, backtest_exit_decrease, direction, single_trade_capital)

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


if __name__ == '__main__':
    at = ArgumentsTest()
    at.initialize()
    for param in at.parameters:
        at.run(param)




