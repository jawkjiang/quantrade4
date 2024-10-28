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
from bybit_access import get_marginBalance, get_tickers, get_kline, place_order, close_position
from helper import max_draw_down_calculate
from data_fetcher import data_fetch
from primary_filter import primary_filter

with open('../../logging_config.json', 'r') as f:
    config = json.load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

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


class RealTest:
    def __init__(self, http: HTTP):
        self.http = http
        self.min_qty = pd.read_csv('../../data/min_qty.csv')
        self.A_group, self.B_group = [], []
        self.data = pd.DataFrame()
        self.lock = threading.Lock()
        self.timestamp = 0
        self.capital = get_marginBalance(http)

        # 初始化seats
        self.seats = [Seat(self.data), Seat(self.data)]

        # 初始化定时器
        self.s = sched.scheduler(time.time, time.sleep)

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

    def run(self):
        # 先全平仓
        self.close_all()
        # 等待整点，开启定时器
        current_time = datetime.datetime.now()
        next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        wait_time = (next_minute - current_time).total_seconds()
        self.s.enter(wait_time, 1, self.update, (next_minute.timestamp() * 1000,))
        # 创建定时器线程
        thread_schedule = threading.Thread(target=self.s.run)
        thread_schedule.daemon = True
        thread_schedule.start()
        while True:
            try:
                # 数据初始化，首先初筛的csv
                data_fetch(self.http)
                # 初筛币
                self.A_group, self.B_group = primary_filter()
                # 初始化self.data
                self.data = pd.DataFrame(columns=['timestamp']+self.A_group+self.B_group)
                data = self.data_init()
                # 按照timestamp将data concat到self.data，data在前，self.data在后
                # 首先要删除data中timestamp与self.data中timestamp相同的行
                data = data[~data['timestamp'].isin(self.data['timestamp'])]
                with self.lock:
                    self.data = pd.concat([data, self.data], axis=0)    # 由于trim在update fetch中执行，这里不需要
                for seat in self.seats:
                    seat.data = self.data
                # 初筛和数据初始化完成后，等待下一个两小时整点
                current_time = datetime.datetime.now()
                next_hour = current_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
                wait_time = (next_hour - current_time).total_seconds()
                time.sleep(wait_time)
            except Exception:
                logger.error(traceback.format_exc())
                # 平仓退出
                self.exit_all()
                exit()

    def data_init(self) -> pd.DataFrame:
        # 只获取A_group和B_group中的币对
        data = pd.DataFrame()
        # 找到最近1分钟的整点
        current_time = datetime.datetime.now()
        timestamp = int(current_time.replace(second=0, microsecond=0).timestamp() * 1000)
        # 初始化timestamp列
        data['timestamp'] = [timestamp - (9 - i) * 60 * 1000 for i in range(10)]
        for symbol in self.A_group + self.B_group:
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
                df_temp[ticker['symbol']] = [float(ticker['markPrice'])]
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
            tick = len(self.data) - 1
            # 第一遍扫描，检定是否有需要平仓的seat
            if seat.symbol != '':
                # 先更新seat的数据
                seat.update(tick)
                if seat.EXIT_FLAG:
                    self.exit(seat)
            # 第二遍扫描，检定是否有需要开仓的seat
            if seat.ENTRY_FLAG:
                self.entry(seat)
                if seat.symbol == '':
                    continue
                seat.update(tick)
            # 此时若seat持仓，则在平仓检定中已更新；若平仓，则在开仓检定中已更新；若不持仓，则也在开仓检定中更新。
            # 因此除了开不了仓的seat，都可以正确更新数据。

    def entry(self, seat: Seat) -> None:
        # 选币
        symbol, direction = self.coin_filter()
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
        position = int(standard_capital * 0.1 / Backtest_Entry_Increase / entry_price)
        # 开仓
        seat.entry(symbol, entry_price, position, direction)
        # place_order
        place_order(self.http, symbol, 'Buy' if direction == 'long' else 'Sell', position)
        return

    def coin_filter(self) -> tuple[str, str]:
        for symbol in self.A_group + self.B_group:
            if symbol in [seat.symbol for seat in self.seats]:
                continue
            for i in range(1, Backtest_Entry_Time):
                # 找到最后一个数据点
                tick = len(self.data) - 1
                current_price = self.data[symbol][tick]
                history_price = self.data[symbol][tick - i]
                if current_price > history_price * (1 + Backtest_Entry_Increase):
                    if symbol in self.A_group:
                        return symbol, 'short'
                    elif symbol in self.B_group:
                        return symbol, 'long'
        return '', ''

    def exit(self, seat: Seat) -> None:
        tick = len(self.data) - 1
        current_price = self.data[seat.symbol][tick]
        # close_position
        close_position(self.http, seat.symbol, 'Sell' if seat.direction == 'long' else 'Buy')
        seat.symbol = ''
        self.indicator_calculate(seat, current_price)
        logging.info(self.indicators)
        seat.exit()

    def indicator_calculate(self, seat: Seat, current_price: float) -> None:
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
        self.capital = get_marginBalance(self.http)
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
                close_position(self.http, seat.symbol, 'Sell' if seat.direction == 'long' else 'Buy')
        exit()

    def close_all(self):
        # 非程序意义上的平仓，而是遍历tickers所有币对，将所有持仓平仓
        with open('../../data/tickers_raw.json', 'r') as f:
            tickers = json.load(f)
        tickers_list = tickers['result']['list']
        for ticker in tickers_list:
            # 不重试地平仓
            try:
                self.http.place_order(category='linear', symbol=ticker['symbol'], side='Sell', qty=0, orderType='Market')
            except Exception:
                pass
            try:
                self.http.place_order(category='linear', symbol=ticker['symbol'], side='Buy', qty=0, orderType='Market')
            except Exception:
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

