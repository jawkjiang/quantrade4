"""
SubAccount is the most basic trading unit in the backtesting system.
"""

import helpers.indicator_calculator as ic
import helpers.coin_filter as cf
from utils.exceptions import OpenMarketError, CloseMarketError
import math


class SubAccount:
    def __init__(self, balance, **kwargs):
        # Required parameters
        self.leverage = 1
        self.history_time = kwargs.get('history_time', 12)
        self.stop_loss = kwargs.get('stop_loss', 0.05)
        self.trading_fee = 0.00075

        # Optional parameters
        self.rising_rate_restriction = kwargs.get('rising_rate_restriction', 0.1)
        self.trailing_time = round(kwargs.get('trailing_time', 5))
        self.trailing_stop = kwargs.get('trailing_stop', 0.04)
        self.slope_time = round(kwargs.get('slope_time', 3))
        self.slope_rate = kwargs.get('slope_rate', 0.1)
        self.slope_history = 60

        # Indicators and internal variables
        self.profit_rate = 0
        self.trade_count = 0
        self.win_rate = 0
        self.win_count = 0
        self.profit_rate_peak = 0
        self.max_profit_rate_single_trade = 0
        self.max_loss_rate_single_trade = 0
        self.max_streak = 0
        self.current_streak = 0
        self.max_loss_streak = 0
        self.current_loss_streak = 0
        self.max_draw_down = 0
        self.profit_factor = 0
        self.total_profit = 0
        self.total_loss = 0

        # Trading status
        self.base = 10000
        self.balance = balance
        self.entry_position_value = 0
        self.value = balance
        self.value_peak = balance
        self.value_valley = balance
        self.symbol = ''
        self.position = 0
        self.entry_price = 0
        self.entry_tick = 0
        self.stop_loss_price = 0
        self.trailing_stop_price = 0
        self.history = []
        self.banned_coins = {}

        # Data
        self.data_open = {}
        self.data_close = {}
        self.min_qty = {}
        self.data_length = 0
        self.tick = 0

        self.overview = []

    def load_data(self, data_open, data_close, data_length, min_qty):
        self.data_open = data_open
        self.data_close = data_close
        self.data_length = data_length
        self.min_qty = min_qty

    def generate_args(self):
        args = {
            'History Time': self.history_time,
            'Stop Loss': self.stop_loss,
            'Rising Rate Restriction': self.rising_rate_restriction,
            'Trailing Time': self.trailing_time,
            'Trailing Stop': self.trailing_stop,
            'Slope Time': self.slope_time
        }
        return args

    def generate_overview(self):
        # Calculate some indicators after the backtesting
        self.win_rate = self.win_count / self.trade_count if self.trade_count > 0 else 0
        self.profit_factor = self.total_profit / self.total_loss if self.total_loss > 0 else 0
        # Generate overview and arguments
        overview = {
            'Trade Count': self.trade_count,
            'Win Rate': self.win_rate,
            'Lowest Value': self.value_valley,
            'Profit Rate Peak': self.profit_rate_peak,
            'Final Profit Rate': self.profit_rate,
            'Max Profit Rate Single Trade': self.max_profit_rate_single_trade,
            'Max Loss Rate Single Trade': self.max_loss_rate_single_trade,
            'Max Streak': self.max_streak,
            'Max Loss Streak': self.max_loss_streak,
            'Max Draw Down': self.max_draw_down,
            'Profit Factor': self.profit_factor
        }
        return overview

    def run(self):
        while self.tick < self.data_length:
            self.update(self.tick)
            self.tick += 1
        return

    # Update is the core method in SubAccount. It updates the account status by each tick.
    def update(self, tick):
        try:
            self.tick = tick
            # Judge if the subAccount is newly created, or unactivated
            if self.entry_tick == 0 or self.symbol == '':
                self.open_market()

            # Fetch basic information
            price = self.data_open[self.symbol][self.tick]
            self.value = self.balance + self.position * price
            self.value_peak = max(self.value_peak, self.value)
            self.value_valley = min(self.value_valley, self.value)
            self.profit_rate = self.value / self.base - 1
            self.profit_rate_peak = max(self.profit_rate_peak, self.profit_rate)
            self.trailing_stop_price = ic.trailing_stop_loss_calculate(price, self.trailing_stop_price,
                                                                       self.trailing_stop)
            self.max_draw_down = ic.max_draw_down_calculate(self.value, self.value_peak, self.max_draw_down)
            # Mention: common stop_loss and profit_stop won't be updated by each tick.
            # They're updated in the open_market method.

            # Detect closing conditions
            past_tick = self.tick - self.entry_tick
            closing_conditions = [
                price <= self.stop_loss_price,
                price <= self.trailing_stop_price and past_tick >= self.trailing_time,
            ]
            if any(closing_conditions):
                if price <= self.stop_loss_price:
                    print(f'{self.symbol} stop loss triggered at tick {self.tick}.')
                elif price <= self.trailing_stop_price and past_tick >= self.trailing_time:
                    print(f'{self.symbol} trailing stop triggered at tick {self.tick}.')
                self.close_market()
            # Judge if the subAccount is just closed
            if self.symbol == '':
                self.open_market()
            return
        except OpenMarketError:
            return
        except CloseMarketError:
            return

    def open_market(self):
        # Open market is the method to open a new position.
        # It's called when the subAccount is newly created and just closed.
        symbol = cf.filter_coin(self.history_time, self.data_open, self.data_close, self.tick,
                                self.rising_rate_restriction, self.slope_time, self.slope_rate, self.slope_history)
        self.symbol = symbol
        symbol = ''     # For debugging
        if symbol == '':
            raise OpenMarketError
        self.entry_price = self.data_open[symbol][self.tick]
        self.entry_tick = self.tick
        min_qty = self.min_qty[symbol]
        self.position = math.floor(self.balance / (1 + self.trading_fee) * self.leverage / self.entry_price) // min_qty * min_qty
        self.entry_position_value = self.position * self.entry_price
        self.balance -= self.entry_position_value * (1 + self.trading_fee)
        self.stop_loss_price = self.entry_price * (1 - self.stop_loss)
        return

    def close_market(self):
        # Close market is the method to close a position.
        # It's called when the subAccount is newly created and just closed.
        price = self.data_open[self.symbol][self.tick]

        # Update indicators
        self.trade_count += 1
        if price > self.entry_price:
            self.win_count += 1
            self.current_streak += 1
            self.max_streak = max(self.max_streak, self.current_streak)
            self.current_loss_streak = 0
            profit_rate = price / self.entry_price - 1
            self.max_profit_rate_single_trade = max(self.max_profit_rate_single_trade, profit_rate)

            self.total_profit += self.position * (price - self.entry_price)
        else:
            self.current_loss_streak += 1
            self.max_loss_streak = max(self.max_loss_streak, self.current_loss_streak)
            self.current_streak = 0
            loss_rate = price / self.entry_price - 1
            self.max_loss_rate_single_trade = min(self.max_loss_rate_single_trade, loss_rate)

            self.total_loss += self.position * (self.entry_price - price)

        # Update trading status
        self.balance += self.position * price * (1 - self.trading_fee)
        self.symbol = ''
        self.position = 0
        self.stop_loss_price = 0
        self.trailing_stop_price = 0
        self.history.append((self.tick, self.profit_rate))
