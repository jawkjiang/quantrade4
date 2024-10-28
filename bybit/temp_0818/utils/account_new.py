"""
    重构account.py
    现在update loop由Account类总管。SubAccount虽然保留update方法，但是其入参tick由Account给入。
    SubAccount达到开仓和平仓条件时，应该由Account进行coin_filter，并选择给入到不同Sub的交易对分配。
    开仓时，Sub仍会将下单金额从总账户的余额中扣除，但是value是所有Sub的value和Account的余额一起计算。
    平仓时，Sub会把value返回给Account，并且状态归零。Sub内部会调用一个函数更新自身的交易指标。
"""
import math

import pandas as pd

import bybit.temp_0818.helpers.coin_filter as cf
import bybit.temp_0818.helpers.indicator_calculator as ic
from bybit.temp_0818.utils.sub_account_new import SubAccount


class Account:
    def __init__(self, balance, **kargs):
        self.balance = balance
        self.base_value = balance
        self.history_time = kargs.get('history_time', 2)
        self.entry_increase = kargs.get('entry_increase', 0.012)
        self.wave_rate = kargs.get('wave_rate', 0.012)

        self.data = pd.DataFrame()
        self.data0 = pd.DataFrame()
        self.data1 = pd.DataFrame()

        self.min_qty = pd.read_csv('data/min_qty.csv')

        self.subAccounts = {}
        # Initialize subAccounts
        for i in range(1):
            self.subAccounts[i] = SubAccount()

        # Initialize indicators
        self.profit_rate = 0
        self.trade_count = 0
        self.win_rate = 0
        self.win_count = 0
        self.profit_rate_peak = 0
        self.max_profit_rate_single_trade = 0
        self.max_loss_rate_single_trade = 0
        self.max_draw_down = 0
        self.profit_factor = 0
        self.total_profit = 0
        self.total_loss = 0
        self.value_peak = 0

    def run(self):
        # 注意这里的run方法和之前不同。现在的data是分段存储的，除第一段merged_0.csv之外，每隔10000个tick应该读取下一个csv文件。
        # 总体的dataframe应保持在20000个tick的长度，且当前的tick应该在后10000个tick中，这样保证计算history时不会越界。
        # 由于dataframe的tick并不指示真正的timestamp index，所以每次重新读取csv文件时，需要重新计算当前tick的index。
        try:
            for i in range(50):
                if i == 0:
                    tick = 0
                    self.data = pd.read_csv(f'data/merged/merged_{i}.csv')
                else:
                    tick = 10000
                    self.data0 = pd.read_csv(f'data/merged/merged_{i-1}.csv')
                    self.data1 = pd.read_csv(f'data/merged/merged_{i}.csv')
                    self.data = pd.concat([self.data0, self.data1], ignore_index=True)
                for j in range(10000):
                    self.update(tick)
                    tick += 1
                print(f'{(i+1)*10000} ticks finished.')
        except ValueError as e:
            print(e)

        self.profit_factor = self.total_profit / self.total_loss
        self.win_rate = self.win_count / self.trade_count

    def update(self, tick):
        for subAccount in self.subAccounts.values():
            # 开仓检定，若sub没有交易对，则开仓
            # 注意开仓货币对由Account决定
            if subAccount.OPEN_FLAG:
                self.open_market(subAccount, tick)

            # 调用subAccount的update方法
            subAccount.update(tick, self.data)

            # 平仓检定
            if subAccount.CLOSE_FLAG:
                self.close_market(subAccount, tick)

    def open_market(self, subAccount, tick):
        #  首先选择交易对
        symbols = cf.filter_coin(data=self.data, tick=tick, history_time=self.history_time,
                                 entry_increase=self.entry_increase, price_limit=0.01)
        if not symbols:
            return
        if len(symbols) == 1:
            # 先判断symbols[0]是否在别的subAccount中超过三次
            if sum([1 for sub in self.subAccounts.values() if sub.symbol == symbols[0]]) >= 3:
                return
            symbol = symbols[0]
        else:
            # 先判断symbols[0]是否在别的subAccount中超过三次
            if sum([1 for sub in self.subAccounts.values() if sub.symbol == symbols[0]]) < 3:
                symbol = symbols[0]
            else:
                symbol = symbols[1]
        # 计算开仓金额
        # 公式算法：以base_value的2^n作为基础，持仓value落在[2^n, 2^(n+1))之间，open_base为2^n
        # 持仓value可按如下方法计算：遍历sub，用每个sub的 position * current_price 再乘以手续费磨损
        # 下单计算时，open_base亏5%，相当于open_value亏wave_rate，所以open_value = open_base * 5% / wave_rate
        value = self.balance
        for sub in self.subAccounts.values():
            if sub == subAccount or sub.symbol == '':
                continue
            value += sub.position * self.data[sub.symbol][tick] * (1 - sub.trading_fee)
        if value < 50:
            raise ValueError('Value should not be less than 50.')
        n = -5
        while self.base_value * 2 ** n <= value:
            n += 1
        open_base = self.base_value * 2 ** (n - 1)
        current_price = self.data[symbol][tick]
        min_qty = self.min_qty[symbol][0]
        # open_value应该按min_qty的倍数开仓
        open_value = open_base * 0.05 / subAccount.wave_rate
        position = math.floor(open_value / current_price / min_qty) * min_qty
        open_value = position * current_price
        self.balance -= open_value / (1 - subAccount.trading_fee)

        # 开仓
        subAccount.open_market(symbol, open_value, current_price, position)

    def close_market(self, subAccount, tick):
        # 平仓
        symbol = subAccount.symbol
        current_price = self.data[symbol][tick]
        subAccount.close_market(current_price)
        # 更新value
        self.balance += subAccount.value
        # 更新indicators
        self.update_indicators(subAccount, tick)
        # 将subAccount状态归零
        subAccount.init()

    def update_indicators(self, subAccount, tick):
        # 更新indicators
        self.trade_count += 1
        self.total_profit += subAccount.profit
        self.total_loss += subAccount.loss
        if subAccount.profit > 0:
            self.win_count += 1
        self.max_profit_rate_single_trade = max(self.max_profit_rate_single_trade, subAccount.profit_rate)
        self.max_loss_rate_single_trade = min(self.max_loss_rate_single_trade, subAccount.profit_rate)
        value = self.balance
        for sub in self.subAccounts.values():
            if sub == subAccount or sub.symbol == '':
                continue
            value += sub.position * self.data[sub.symbol][tick] * (1 - sub.trading_fee)
        if value < 0:
            raise ValueError('Value should not be negative.')
        self.value_peak = max(self.value_peak, value)
        self.profit_rate = value / self.base_value - 1
        self.profit_rate_peak = max(self.profit_rate_peak, self.profit_rate)
        self.max_draw_down = ic.max_draw_down_calculate(value, self.value_peak, self.max_draw_down)

    def output(self):
        return pd.DataFrame({
            'profit_rate': [self.profit_rate],
            'trade_count': [self.trade_count],
            'win_rate': [self.win_rate],
            'win_count': [self.win_count],
            'profit_rate_peak': [self.profit_rate_peak],
            'max_profit_rate_single_trade': [self.max_profit_rate_single_trade],
            'max_loss_rate_single_trade': [self.max_loss_rate_single_trade],
            'max_draw_down': [self.max_draw_down],
            'profit_factor': [self.profit_factor],
            'total_profit': [self.total_profit],
            'total_loss': [self.total_loss]
        })
