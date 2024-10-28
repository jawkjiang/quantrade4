"""
    座位类。由于止盈止损指令不再由本地发出，Seat类不需要记录价格等数据，只需要记录当前座位上的订单号和symbol即可。
"""


class Seat:
    def __init__(self):
        self.order_id = ''
        self.symbol = ''
        self.entry_price = 0
        self.side = ''
        self.entry_margin = 0

    def entry(self, order_id: str, symbol: str, entry_price: float, side: str, entry_margin: float):
        self.order_id = order_id
        self.symbol = symbol
        self.entry_price = entry_price
        self.side = side
        self.entry_margin = entry_margin


    def exit(self):
        self.order_id = ''
        self.symbol = ''
        self.entry_price = 0
        self.side = ''
        self.entry_margin = 0
