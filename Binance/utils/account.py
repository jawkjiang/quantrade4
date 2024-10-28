import binance.helpers.indicator_calculator as ic
from sub_account import SubAccount


class Account:
    def __init__(self):
        self.subAccounts = {}

        # Indicators and internal variables
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

        # Trading status
        self.base = 3 * 10000
        self.value = self.base
        self.value_peak = self.base
        self.value_valley = self.base
        self.borrow = 0
        self.value_in_market = 0
        self.boom = False
        self.hang = False

        # Data
        self.data = {}
        self.data_length = 100000
        self.min_qty = {}
        self.args = {}
        self.indexes = {}
        self.indexes_lengths = {}
        self.pointers = {0: 0, 1: 0, 2: 0}
        self.tick = 0
        self.values = []

    def load_data(self, data, args, min_qty, indexes):
        self.data = data
        self.args = args
        self.min_qty = min_qty
        self.indexes = indexes
        self.indexes_lengths = {0: len(indexes[0]), 1: len(indexes[1]), 2: len(indexes[2])}

    def add_sub_account(self, sub_account, rank):
        sub_account.load_data(self.data, 100000, self.min_qty)
        self.subAccounts[rank] = sub_account

    def del_sub_account(self, rank):
        self.subAccounts[rank] = None

    def run(self):
        try:
            # initialize
            for rank in range(3):
                pointer = self.pointers[rank]
                index = self.indexes[rank][pointer]
                sub_account = SubAccount(rank, "long", 10000, **self.args[rank][index])
                self.add_sub_account(sub_account, rank)
                self.pointers[rank] += 1
                if self.pointers[rank] == self.indexes_lengths[rank]:
                    self.pointers[rank] = 0

            # loop
            while self.tick < self.data_length:
                self.value = 0
                self.borrow = 0
                self.value_in_market = 0
                for rank, sub_account in self.subAccounts.copy().items():
                    sub_account.hang = self.hang
                    sub_account.update(self.tick)
                    self.value += sub_account.value
                    if sub_account.symbol != '':
                        self.borrow += -sub_account.balance
                        self.value_in_market += sub_account.entry_position_value * (1 + sub_account.trading_fee)
                    self.max_profit_rate_single_trade = max(sub_account.profit_rate, self.max_profit_rate_single_trade)
                    self.max_loss_rate_single_trade = min(sub_account.profit_rate, self.max_loss_rate_single_trade)
                    if sub_account.draw_down_flag:
                        # Update stats
                        self.trade_count += sub_account.trade_count
                        self.win_count += sub_account.win_count
                        self.total_profit += sub_account.total_profit
                        self.total_loss += sub_account.total_loss

                        balance = sub_account.balance
                        self.del_sub_account(rank)
                        pointer = self.pointers[rank]
                        index = self.indexes[rank][pointer]
                        sub_account = SubAccount(rank, "long", balance, **self.args[rank][index])
                        self.add_sub_account(sub_account, rank)
                        self.pointers[rank] += 1
                        if self.pointers[rank] == self.indexes_lengths[rank]:
                            self.pointers[rank] = 0

                if self.value < 0.1 * self.borrow:
                    raise ValueError('Boom!')
                if 3 * self.value < self.value_in_market:
                    print(self.tick, self.value, self.value_in_market)
                    self.hang = True
                else:
                    self.hang = False
                self.value_peak = max(self.value, self.value_peak)
                self.value_valley = min(self.value, self.value_valley)
                self.max_draw_down = ic.max_draw_down_calculate(self.value, self.value_peak, self.max_draw_down)
                self.profit_rate = self.value / self.base - 1
                self.profit_rate_peak = max(self.profit_rate, self.profit_rate_peak)
                if self.tick % 100 == 0:
                    self.values.append(self.value)
                self.tick += 1
            return
        except ValueError:
            self.boom = True
            return

    def generate_overview(self):
        try:
            for index, sub_account in self.subAccounts.items():
                self.trade_count += sub_account.trade_count
                self.win_count += sub_account.win_count
                self.total_profit += sub_account.total_profit
                self.total_loss += sub_account.total_loss
            self.win_rate = self.win_count / self.trade_count
            self.profit_factor = self.total_profit / self.total_loss
        except ZeroDivisionError:
            pass
        overview = {
            'Trade count': self.trade_count,
            'Win rate': self.win_rate,
            'Lowest Value': self.value_valley,
            'Profit Rate Peak': self.profit_rate_peak,
            'Final Profit Rate': self.profit_rate,
            'Max Profit Rate Single Trade': self.max_profit_rate_single_trade,
            'Max Loss Rate Single Trade': self.max_loss_rate_single_trade,
            'Max Draw Down': self.max_draw_down,
            'Profit Factor': self.profit_factor,
            'Boom': 'Yes' if self.boom else 'No'
        }
        return overview
