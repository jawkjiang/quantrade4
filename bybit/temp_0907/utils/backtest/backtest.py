"""
    回测。
    同时监测A、B两组，若存在任何一支货币对符合如下条件，则进场：
    A组：
    最近2个openPrice中，若第二个较第一个上涨了2.2%，则做空进场
    上述条件若不符合，则最近3个openPrice中，若第三个较第一个上涨了2.2%，则做空进场
    B组：
    最近2个openPrice中，若第二个较第一个上涨了2.2%，则做多进场
    上述条件若不符合，则最近3个openPrice中，若第三个较第一个上涨了2.2%，则做多进场
    回测保持在两个座位。当存在座位空置时，上述进场监测启动，否则不启动。
    本金和进场金额
    本金：
    初始本金为1000 USDT。
    进场后，本金实际为marginBalance保证金。它由当前账户余额 + 已进场座位的市值得到。
    标定本金：
    以1000 USDT为基准，当本金落在[1000 * 2^n, 1000 * 2^(n+1))范围内时（其中n为整数），标定本金为1000 * 2^n。
    进场金额：
    进场金额由如下公式计算：
    总是希望每一次交易盈余或亏损的金额为标定本金的10%。
    每一次止盈止损线为进场价格的正负1.1%，即每一次交易的止盈止损金额为进场金额的正负1.1%。
    标定本金 * 10% = 进场金额 * 1.1%，即进场金额为标定本金 * 100 / 11，杠杆率约为10。
"""

import pandas as pd
import math
from tqdm import tqdm
import primary_filter
from helper import max_draw_down_calculate
import json


"""
    能用class还是用class吧，单纯用函数传参过于复杂。
"""


class Seat:
    def __init__(self, data):
        self.data = data
        self.symbol = ''
        self.direction = ''
        self.entry_price = 0
        self.position = 0
        self.value = 0

        self.ENTRY_FLAG = True
        self.EXIT_FLAG = False

    def entry(self, symbol: str, entry_price: float, position: float, direction: str) -> None:
        self.symbol = symbol
        self.entry_price = entry_price
        self.position = position
        self.direction = direction
        self.ENTRY_FLAG = False

    def update(self, tick: int) -> None:
        current_price = self.data[self.symbol][tick]
        if current_price > self.entry_price * (1 + Backtest_Exit_Increase) \
                or current_price < self.entry_price * (1 - Backtest_Exit_Decrease):
            self.EXIT_FLAG = True

    def exit(self) -> None:
        self.entry_price = 0
        self.position = 0
        self.value = 0
        self.ENTRY_FLAG = True
        self.EXIT_FLAG = False


class Backtest:
    def __init__(self):
        # data的读取方式变为merge
        self.data = pd.read_csv('../../../data/merged.csv')
        self.min_qty = pd.read_csv('../../../data/min_qty.csv')
        self.A_group, self.B_group = [], []
        self.capital = Initial_Capital
        self.balance = self.capital
        self.seats = [Seat(self.data), Seat(self.data)]
        self.entry_difference_rates = []
        self.exit_difference_rates = []

        # indicators
        self.indicators = {
            'total_trades': 0,
            'total_wins': 0,
            'total_loses': 0,
            'win_rate': 0.0,
            'peak_capital': 0.0,
            'profit_rate': 0.0,
            'peak_profit_rate': 0.0,
            'max_drawdown': 0.0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'profit_factor': 0.0,
        }

    def run(self) -> None:
        print(f"Backtest_Entry_Increase: {Backtest_Entry_Increase}, Backtest_Exit_Increase: {Backtest_Exit_Increase},"
              f" Backtest_Exit_Decrease: {Backtest_Exit_Decrease}")
        with tqdm(total=len(self.data) - Time_Frame - Backtest_Entry_Time, desc='Backtest', leave=True, position=0) as mainBar:
            for tick in range(Time_Frame + Backtest_Entry_Time, len(self.data)):
                if (tick - Backtest_Entry_Time - Time_Frame) % Interval == 0:
                    with tqdm(total=len(self.data.columns) - 1, desc='Primary Filter', leave=False, position=1) as subBar:
                        self.A_group, self.B_group = primary_filter.primary_filter(self.data, tick, subBar)
                self.update(tick)
                mainBar.update(1)
        self.output()

    def update(self, tick: int) -> None:
        for seat in self.seats:
            if seat.ENTRY_FLAG:
                # 开仓
                if not self.entry(tick, seat):
                    continue
            seat.update(tick)
            if seat.EXIT_FLAG:
                # 平仓
                self.exit(tick, seat)

    def entry(self, tick: int, seat: Seat) -> bool:
        # 选币
        symbol, direction = self.coin_filter(tick)
        if symbol == '':
            return False
        # 计算进场金额
        entry_price = self.data[symbol][tick]
        # 计算本金（即保证金marginBalance）
        self.capital = self.capital_calculate(tick)
        # 计算标定本金
        n = -8
        while self.capital >= 1000 * 2 ** n:
            n += 1
        standard_capital = 1000 * 2 ** (n - 1)
        # 计算进场仓位，注意需要读取min_qty取整
        # 不读取min_qty，直接取整
        position = int(standard_capital * 0.1 / Backtest_Entry_Increase / entry_price)
        # 计算进场金额
        if direction == 'long':
            entry_value = position * entry_price * (1 + Trading_Fee)
        else:
            position = -position
            entry_value = position * entry_price / (1 + Trading_Fee)
        # 更新本金
        self.balance -= entry_value
        # 开仓
        seat.entry(symbol, entry_price, position, direction)
        return True

    def coin_filter(self, tick: int) -> tuple[str, str]:
        for symbol in self.A_group + self.B_group:
            if symbol in [seat.symbol for seat in self.seats]:
                continue
            for i in range(1, Backtest_Entry_Time):
                current_price = self.data[symbol][tick]
                history_price = self.data[symbol][tick - i]
                if current_price > history_price * (1 + Backtest_Entry_Increase):
                    difference_rate = (current_price - history_price) / history_price
                    self.entry_difference_rates.append(difference_rate)
                    if symbol in self.A_group:
                        return symbol, 'short'
                    elif symbol in self.B_group:
                        return symbol, 'long'
        return '', ''

    def exit(self, tick: int, seat: Seat) -> None:

        # 我怀疑我算错了，这个本金增加的速率太离谱了
        # 画一个实时差价比例的图，看看是不是这个问题

        current_price = self.data[seat.symbol][tick]

        # update 0916
        # 实际交易过程中滑点严重，为了模拟实际情况，将滑点设置为0.1%

        if seat.direction == 'long':
            current_price *= 0.999
            self.balance += seat.position * current_price / (1 + Trading_Fee)
            difference_rate = (current_price - seat.entry_price) / seat.entry_price
        else:
            current_price *= 1.001
            self.balance += seat.position * current_price * (1 + Trading_Fee)
            difference_rate = (seat.entry_price - current_price) / seat.entry_price
        self.exit_difference_rates.append(difference_rate)

        seat.symbol = ''
        self.indicator_calculate(seat, tick, current_price)
        print(self.indicators)

        seat.exit()

    def capital_calculate(self, tick: int) -> float:
        temp = 0
        for st in self.seats:
            if st.symbol == '':
                continue
            if st.direction == 'long':
                temp += st.position * self.data[st.symbol][tick] / (1 + Trading_Fee)
            elif st.direction == 'short':
                temp += st.position * self.data[st.symbol][tick] * (1 + Trading_Fee)
        capital = self.balance + temp
        return capital

    def indicator_calculate(self, seat: Seat, tick: int, current_price: float) -> None:
        # update indicators
        self.indicators['total_trades'] += 1

        if seat.direction == 'long':
            if current_price > seat.entry_price:
                self.indicators['total_wins'] += 1
                self.indicators['total_profit'] += seat.position * (current_price - seat.entry_price)
            else:
                self.indicators['total_loses'] += 1
                self.indicators['total_loss'] += seat.position * (seat.entry_price - current_price)
        elif seat.direction == 'short':
            if current_price < seat.entry_price:
                self.indicators['total_wins'] += 1
                self.indicators['total_profit'] += seat.position * (current_price - seat.entry_price)
            else:
                self.indicators['total_loses'] += 1
                self.indicators['total_loss'] += seat.position * (seat.entry_price - current_price)

        self.capital = self.capital_calculate(tick)
        if self.capital > self.indicators['peak_capital']:
            self.indicators['peak_capital'] = self.capital

        self.indicators['profit_rate'] = self.capital / Initial_Capital - 1

        if self.indicators['profit_rate'] > self.indicators['peak_profit_rate']:
            self.indicators['peak_profit_rate'] = self.indicators['profit_rate']

        self.indicators['max_drawdown'] = max_draw_down_calculate(self.capital, self.indicators['peak_capital'],
                                                                  self.indicators['max_drawdown'])

    def output(self) -> None:
        if self.indicators['total_trades'] == 0:
            self.indicators['win_rate'] = 0
        self.indicators['win_rate'] = self.indicators['total_wins'] / self.indicators['total_trades']
        if self.indicators['total_loss'] == 0:
            self.indicators['profit_factor'] = math.inf
        self.indicators['profit_factor'] = - self.indicators['total_profit'] / self.indicators['total_loss']
        print(self.indicators)
        # 将indicators转换为DataFrame输出到csv文件
        df = pd.DataFrame(self.indicators, index=[0])
        df.to_csv(f'../../output/{Backtest_Entry_Increase}_{Backtest_Exit_Increase}_backtest_indicators.csv', index=True)


if __name__ == '__main__':
    global Backtest_Entry_Increase, Backtest_Exit_Increase, Backtest_Exit_Decrease
    with open('../../../constants.json', 'r') as f:
        constants = json.load(f)
        Time_Frame = constants['Time_Frame']
        Interval = constants['Interval']
        Backtest_Entry_Time = constants['Backtest_Entry_Time']
        Backtest_Entry_Increase = constants['Backtest_Entry_Increase']
        Backtest_Exit_Increase = constants['Backtest_Exit_Increase']
        Backtest_Exit_Decrease = constants['Backtest_Exit_Decrease']
        Initial_Capital = constants['Initial_Capital']
        Trading_Fee = constants['Trading_Fee']
    # 在全局变量生命中更改值
    for i in range(1, 10):
        Backtest_Entry_Increase = 0.01 + i * 0.002
        Backtest_Exit_Increase = 0.005 + i * 0.001
        Backtest_Exit_Decrease = 0.005 + i * 0.001

        backtest = Backtest()
        backtest.run()
