"""
    重构sub_account.py
    SubAccount只需负责单一交易对的value更新和指标计算，不再负责开仓和平仓的判断。
"""


class SubAccount:
    def __init__(self, wave_rate=0.012):
        self.symbol = ''
        self.open_value = 0
        self.open_price = 0
        self.position = 0
        self.stop_loss_price = 0
        self.update_price = 0
        self.stop_profit_price = 0
        self.value = 0
        self.profit = 0
        self.loss = 0
        self.profit_rate = 0
        self.wave_rate = wave_rate

        self.trading_fee = 0.0005

        self.OPEN_FLAG = True
        self.UPDATE_FLAG = False
        self.CLOSE_FLAG = False

    def init(self):
        self.symbol = ''
        self.open_value = 0
        self.open_price = 0
        self.position = 0
        self.stop_loss_price = 0
        self.update_price = 0
        self.stop_profit_price = 0
        self.value = 0
        self.profit = 0
        self.loss = 0
        self.profit_rate = 0

    def open_market(self, symbol, open_value, open_price, position):

        self.symbol = symbol
        self.open_value = open_value
        self.open_price = open_price
        self.position = position
        self.value = open_value * (1 - self.trading_fee)

        self.stop_loss_price = open_price * (1 - self.wave_rate + self.trading_fee)
        self.update_price = open_price * (1 + self.wave_rate + self.trading_fee)
        self.stop_profit_price = open_price * (1 + 2 * self.wave_rate + self.trading_fee)

        self.OPEN_FLAG = False

    def update(self, tick, data):
        # 只更新OPEN_FLAG、UPDATE_FLAG、CLOSE_FLAG
        if self.symbol == '':
            return
        current_price = data[self.symbol][tick]
        if current_price < self.stop_loss_price:
            self.CLOSE_FLAG = True
        if not self.UPDATE_FLAG and current_price > self.update_price:
            self.stop_loss_price = self.open_price * (1 + 2 * self.trading_fee)
            self.UPDATE_FLAG = True
        if current_price > self.stop_profit_price:
            self.CLOSE_FLAG = True

    def close_market(self, current_price):
        self.value = self.position * current_price * (1 - self.trading_fee)
        profit = self.value - self.open_value
        if profit > 0:
            self.profit += profit
        else:
            self.loss -= profit
        self.profit_rate = profit / self.open_value
        self.CLOSE_FLAG = False
        self.OPEN_FLAG = True
        self.UPDATE_FLAG = False
