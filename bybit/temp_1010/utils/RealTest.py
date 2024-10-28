"""
    实测类，为程序核心代码
"""

import pandas as pd
from pybit.unified_trading import HTTP
import threading
import logging
import logging.config
import json
import sched
import time
import datetime
import traceback

from Seat import Seat
from bybit_access import get_marginBalance, get_tickers, get_kline, cancel_order, get_open_orders, place_order, place_limit_order, get_position, close_position
from helper import max_draw_down_calculate

with open('../logging_config.json', 'r') as f:
    config = json.load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

# 常量改由json读取
with open('../constants.json', 'r') as f:
    constants = json.load(f)
    Backtest_Entry_Time = constants['Backtest_Entry_Time']
    Initial_Capital = constants['Initial_Capital']



class RealTest:
    def __init__(self, http: HTTP):
        self.http = http
        self.data = pd.DataFrame()
        self.lock = threading.Lock()
        self.timestamp = 0
        self.capital = get_marginBalance(http)
        # 这一步修改为读取../data/group.json文件，且不再区分A_group和B_group，所有参数均在json中给出
        with open('../data/group.json', 'r') as f:
            group = json.load(f)
        # 只读取前20个币对
        self.group = {key: group[key] for key in list(group.keys())[0:70]}
        self.symbol_consecutive_loses = {symbol: 0 for symbol in self.group.keys()}
        self.freezing_symbols = {}

        # 初始化seats
        self.seats = [Seat(), Seat()]

        # 初始化定时器
        self.s = sched.scheduler(time.time, time.sleep)

        # indicators
        self.indicators = {
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

    def run(self):
        # 先全平仓
        # self.close_all()
        # 初始化self.data
        self.data = pd.DataFrame(columns=['timestamp'] + list(self.group.keys()))
        data = self.data_init()
        # 按照timestamp将data concat到self.data，data在前，self.data在后
        # 首先要删除data中timestamp与self.data中timestamp相同的行
        data = data[~data['timestamp'].isin(self.data['timestamp'])]
        with self.lock:
            self.data = pd.concat([data, self.data], axis=0)  # 由于trim在update fetch中执行，这里不需要
        # 等待整点，开启定时器
        current_time = datetime.datetime.now()
        next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        wait_time = (next_minute - current_time).total_seconds()
        self.s.enter(wait_time, 1, self.update, (int(next_minute.timestamp() * 1000),))
        # 创建定时器线程
        thread_schedule = threading.Thread(target=self.s.run)
        thread_schedule.daemon = True
        thread_schedule.start()
        while True:
            time.sleep(1)

    def data_init(self) -> pd.DataFrame:
        # 只获取A_group和B_group中的币对
        data = pd.DataFrame()
        # 找到最近1分钟的整点
        current_time = datetime.datetime.now()
        timestamp = int(current_time.replace(second=0, microsecond=0).timestamp() * 1000)
        # 初始化timestamp列
        data['timestamp'] = [timestamp - (9 - i) * 60 * 1000 for i in range(10)]
        for symbol in self.group.keys():
            k_lines = get_kline(self.http, symbol, '1', 10, timestamp - 9 * 60 * 1000, timestamp)
            df = pd.DataFrame(k_lines['result']['list'],
                              columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            # merge数据
            df.rename(columns={'open': symbol}, inplace=True)
            df = df[['timestamp', symbol]]
            df['timestamp'] = df['timestamp'].astype('int64')
            df[symbol] = df[symbol].astype('float64')
            data = pd.merge(data, df, on='timestamp', how='left')
        return data

    def update(self, timestamp: int):
        # 该方法需要加锁
        with self.lock:
            try:
                self.data = self.fetch(self.data, timestamp)
                # 给self.seats中的每个seat更新数据
                for seat in self.seats:
                    seat.data = self.data
                # 检查self.data是否已经符合交易条件
                if len(self.data) == 10:
                    # 使用self.data撮合交易
                    self.trade()
                # 判断freezing_symbols中的币对是否已经解冻
                current_time = datetime.datetime.now()
                for symbol in list(self.freezing_symbols.keys()):
                    if current_time.timestamp() * 1000 - self.freezing_symbols[symbol] > 32400000:  # 9小时
                        del self.freezing_symbols[symbol]
                # 写入定时器的等待时间
                current_time = datetime.datetime.now()
                next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
                wait_time = (next_minute - current_time).total_seconds()
                self.s.enter(wait_time, 1, self.update, (timestamp + 60000,))
            except Exception:
                logger.error(traceback.format_exc())
                # 平仓退出
                self.exit_all()
                exit()

    def fetch(self, data: pd.DataFrame, timestamp: int) -> pd.DataFrame:
        # 读取tickers
        tickers = get_tickers(self.http)
        # 时间控制由主函数控制，这里只负责获取数据
        tickers_list = tickers['result']['list']
        df_temp = pd.DataFrame()
        # 初始化timestamp列
        df_temp['timestamp'] = [timestamp]
        for ticker in tickers_list:
            if ticker['symbol'] in data.columns:
                df_temp[ticker['symbol']] = [float(ticker['lastPrice'])]
        # 在原data末尾添加新数据
        data = pd.concat([data, df_temp], axis=0)
        # 删除多余数据
        if len(data) > 10:
            data = data.iloc[-10:].reset_index(drop=True)
        return data

    def trade(self):
        # 撮合交易逻辑
        # 沿用temp中realTrade类的逻辑
        for seat in self.seats:
            # 第一遍扫描，检定是否有需要平仓的seat
            if seat.order_id != '':
                # 止盈检定
                order = get_open_orders(self.http, seat.order_id)['result']['list'][0]
                if order['orderStatus'] == 'Filled':
                    self.exit(seat)
                    continue
                # 止损检定
                current_price = self.data[seat.symbol][len(self.data) - 1]
                Backtest_Exit_Increase = self.group[seat.symbol]['Backtest_Entry_Increase']
                Backtest_Exit_Decrease = self.group[seat.symbol]['Backtest_Exit_Decrease']
                if (current_price < seat.entry_price * (1 - Backtest_Exit_Decrease) and seat.side == 'long')\
                        or (current_price > seat.entry_price * (1 + Backtest_Exit_Increase) and seat.side == 'short'):
                    # 下市价单平仓
                    # 有极小的概率，平仓不掉，这里try_except
                    # 不能用try_except！！！平不掉就再试，五次都平不掉就关程序
                    close_position(self.http, seat.symbol, 'Sell' if seat.side == 'long' else 'Buy')
                    cancel_order(self.http, seat.symbol, seat.order_id)
                    self.exit(seat)
                    continue

            # 第二遍扫描，检定是否有需要开仓的seat
            if seat.symbol == '':
                self.entry(seat)
                if seat.symbol == '':
                    continue
            # 此时若seat持仓，则在平仓检定中已更新；若平仓，则在开仓检定中已更新；若不持仓，则也在开仓检定中更新。
            # 因此除了开不了仓的seat，都可以正确更新数据。

    def entry(self, seat: Seat) -> None:
        # 选币
        symbol = self.coin_filter()
        if symbol == '':
            return
        # 计算进场金额
        tick = len(self.data) - 1
        entry_price = self.data[symbol][tick]
        # 计算本金（即保证金marginBalance）
        self.capital = get_marginBalance(self.http) / 10    # 测试用
        # 计算标定本金
        n = -8
        while self.capital >= 1000 * 2 ** n:
            n += 1
        standard_capital = 1000 * 2 ** (n - 1)
        # 又不是买不起，干脆直接买一个整数的币，这样就不会有这种问题了。
        Backtest_Entry_Increase = self.group[symbol]['Backtest_Entry_Increase']
        Backtest_Exit_Increase = self.group[symbol]['Backtest_Exit_Increase']
        Backtest_Exit_Decrease = self.group[symbol]['Backtest_Exit_Decrease']
        direction = self.group[symbol]['direction']
        tp_price = entry_price * (1 + Backtest_Exit_Increase) if direction == 'long' else entry_price * (1 - Backtest_Exit_Decrease)
        single_trade_capital = self.group[symbol]['single_trade_capital']
        position = int(standard_capital * single_trade_capital / Initial_Capital / Backtest_Entry_Increase / entry_price)
        # place_order
        # 由于bybit的止盈单很怪，下不了，考虑直接市价开仓，然后挂一个止盈点的限价单。止损点自己计算。
        place_order(self.http, symbol, 'Buy' if direction == 'long' else 'Sell', position)
        tp_order = place_limit_order(self.http, symbol, 'Sell' if direction == 'long' else 'Buy', position, tp_price)
        seat.entry(tp_order['result']['orderId'], symbol, entry_price, direction)
        return

    def coin_filter(self) -> str:
        for symbol in self.group.keys():
            if symbol in [seat.symbol for seat in self.seats] or symbol in self.freezing_symbols.keys():
                continue
            for i in range(1, Backtest_Entry_Time):
                # 找到最后一个数据点
                tick = len(self.data) - 1
                current_price = self.data[symbol][tick]
                history_price = self.data[symbol][tick - i]
                if current_price > history_price * (1 + self.group[symbol]['Backtest_Entry_Increase']):
                    return symbol
        return ''

    def exit(self, seat: Seat) -> None:
        self.indicator_calculate(seat)
        logging.info(self.indicators)
        seat.exit()

    def indicator_calculate(self, seat: Seat) -> None:
        # update indicators
        self.indicators['total_trades'] += 1
        self.capital = get_marginBalance(self.http)
        current_price = self.data[seat.symbol][len(self.data) - 1]
        # 和单座位不同，这里使用difference计算差额的话，由于另一个座位的存在，capital计算必然有误。因此依旧改为price计算。
        if (seat.entry_price < current_price and seat.side == 'long') or (seat.entry_price > current_price and seat.side == 'short'):
            self.indicators['total_wins'] += 1
            self.indicators['consecutive_wins'] += 1
            if self.indicators['consecutive_wins'] > self.indicators['max_consecutive_wins']:
                self.indicators['max_consecutive_wins'] = self.indicators['consecutive_wins']
            self.indicators['consecutive_loses'] = 0
            # 更新symbol_consecutive_loses
            self.symbol_consecutive_loses[seat.symbol] = 0

        elif (seat.entry_price >= current_price and seat.side == 'long') or (seat.entry_price <= current_price and seat.side == 'short'):
            self.indicators['total_loses'] += 1
            self.indicators['consecutive_loses'] += 1
            if self.indicators['consecutive_loses'] > self.indicators['max_consecutive_loses']:
                self.indicators['max_consecutive_loses'] = self.indicators['consecutive_loses']
            self.indicators['consecutive_wins'] = 0
            # 更新symbol_consecutive_loses
            self.symbol_consecutive_loses[seat.symbol] += 1
            if self.symbol_consecutive_loses[seat.symbol] > 3:
                timestamp = int(datetime.datetime.now().timestamp() * 1000)
                self.freezing_symbols[seat.symbol] = timestamp

        if self.capital > 50000:
            # 平仓退出
            raise Exception('Capital exceeds 50000.')
        if self.capital > self.indicators['peak_capital']:
            self.indicators['peak_capital'] = self.capital
        self.indicators['profit_rate'] = self.capital / Initial_Capital - 1
        if self.indicators['profit_rate'] > self.indicators['peak_profit_rate']:
            self.indicators['peak_profit_rate'] = self.indicators['profit_rate']
        self.indicators['max_drawdown'] = max_draw_down_calculate(self.capital, self.indicators['peak_capital'],
                                                                  self.indicators['max_drawdown'])

    def exit_all(self):
        for seat in self.seats:
            if seat.symbol != '':
                try:
                    self.http.place_order(category='linear', symbol=seat.symbol, side='Sell', qty=0, orderType='Market')
                except Exception:
                    pass
                try:
                    self.http.place_order(category='linear', symbol=seat.symbol, side='Buy', qty=0, orderType='Market')
                except Exception:
                    pass
        exit()

    def close_all(self):
        position = get_position(http)
        # 获取position中所有存在仓位的symbol
        symbols = [each['symbol'] for each in position['result']['list']]
        # 测试close_position
        for symbol in symbols:
            try:
                http.place_order(category='linear', symbol=symbol, side='Sell', qty=0, reduceOnly=True, orderType='Market')
            except Exception as e:
                pass
            try:
                http.place_order(category='linear', symbol=symbol, side='Buy', qty=0, reduceOnly=True, orderType='Market')
            except Exception as e:
                pass

if __name__ == '__main__':
    import dotenv
    import os
    dotenv.find_dotenv()
    dotenv.load_dotenv()
    http = HTTP(
        api_key=os.getenv('API_KEY'),
        api_secret=os.getenv('API_SECRET'),
        testnet=False
    )
    real_test = RealTest(http)
    real_test.run()

