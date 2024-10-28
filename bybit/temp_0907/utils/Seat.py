"""
    座位类。
"""

import json


# 常量改由json读取
with open('../../constants.json', 'r') as f:
    constants = json.load(f)
    Time_Frame = constants['Time_Frame']
    Interval = constants['Interval']
    Backtest_Entry_Time = constants['Backtest_Entry_Time']
    Backtest_Entry_Increase = constants['Backtest_Entry_Increase']
    Backtest_Exit_Increase = constants['Backtest_Exit_Increase']
    Backtest_Exit_Decrease = constants['Backtest_Exit_Decrease']
    Initial_Capital = constants['Initial_Capital']
    Trading_Fee = constants['Trading_Fee']


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