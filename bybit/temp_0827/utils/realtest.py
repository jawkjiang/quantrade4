"""
    实测。
    数据准备：
    - 现有数据库中数据是8/12/2024 00:00:00往前的数据。要进行实测，数据必须能和实际时间接轨。
    - 考虑每次运行时重新从bybit fetch最近2000个tick的数据，并且每分钟fetch一次tickers，对dataframe update
    - 这一方法虽然会导致启动速度变慢，但这是实操中移动到aws上最合适的方法
    框架：
    程序启动后，首先进行数据准备，然后进入主循环，每分钟进行一次数据更新，每5*60分钟进行一次初筛。
    主循环：
    - 每分钟进行一次数据更新，即fetch最新的tickers，更新dataframe，并且删除dataframe最早的一行
        - 这种方法可能导致tick计算混乱。一种解决方法是，tick并不更新，而是保持在2000这一定值，每次更新时，删除最早的一行，然后append最新的一行。
        - 但是，一旦初筛的时间大于1分钟，初筛和更新就会对同一个dataframe进行数据竞争，这会导致程序崩溃。
        - 考虑初筛并不使用原始的dataframe，而是copy一份当前时刻的dataframe，然后对这份dataframe进行初筛。
        - 另外交易逻辑也在此处完成
    - 每5*60分钟进行一次初筛，初筛后的货币对存入A_group和B_group
"""
import datetime
from pybit.unified_trading import HTTP
import logging

import sys
import pandas as pd
import math
import sched
import time
import threading
import primary_filter
from helper import max_draw_down_calculate

# Constants
Time_Frame = 456 * 60
Interval = 5 * 60
Backtest_Entry_Time = 3
Backtest_Entry_Increase = 0.022
Backtest_Exit_Increase = 0.011
Backtest_Exit_Decrease = 0.011
Initial_Capital = 1000
Trading_Fee = 0.0005

Global_Lock = threading.Lock()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


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


class Realtest:
    def __init__(self):
        self.data = pd.DataFrame()
        self.min_qty = pd.read_csv('../../data/min_qty.csv')
        self.A_group, self.B_group = [], []
        self.capital = Initial_Capital
        self.balance = self.capital
        self.seats = [Seat(self.data), Seat(self.data)]
        self.entry_difference_rates = []
        self.exit_difference_rates = []

        # 定义定时器
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

        # 定义HTTP对象
        self.http = HTTP(testnet=True)

    def run(self) -> None:
        """
        程序的运行主体。
        1. fetch最新的2000个tickers数据
        :return:
        """
        # 给主循环加一个时钟显示
        thread_clock = threading.Thread(target=self.clock)
        thread_clock.daemon = True
        thread_clock.start()
        # 获取一遍tickers数据，用于初始化data这个dataframe。
        # 筛选lastPrice = 0.1-7 之间的货币对
        self.data = self.data_init()
        # 理想情况下，不需要花费1分钟以上的时间获取2000个tickers数据，能保证这2000个是最新的。但是花费时间超过1分钟就会导致数据陈旧
        # 新的tickers数据应该暂存在一个另外的dataframe中，然后每分钟更新一次这个dataframe
        # 一旦获取完2000个tickers数据，就对两个dataframe进行拼接，并删除到2000行。这个过程不会花费超过一分钟时间。
        # 先定时update
        # 计算初次运行延迟
        # 需要把self.s.run()塞到线程里，否则会阻塞主线程
        current_time = datetime.datetime.now()
        next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        wait_time = (next_minute - current_time).total_seconds()
        self.s.enter(wait_time, 1, self.update, argument=(1999,))
        thread_scheduler = threading.Thread(target=self.s.run)
        thread_scheduler.daemon = True
        thread_scheduler.start()
        # fetch方法返回一个dataframe，包含了最新的2000个k线数据——但也可能不是最新的。
        # 这里加一个线程锁，将fetch到的data替换到self.data中
        data = self.fetch()
        # 找到self.data中最小的timestamp
        min_timestamp = self.data['timestamp'].min()
        # 选出data中timestamp大于min_timestamp的部分
        data_part = data[data['timestamp'] > min_timestamp]
        with Global_Lock:
            # 开始替换
            self.data.update(data_part)
        # fetch完成后，self.data已经保持最新。接下来需要计算初筛的时间。
        # 总是希望初筛的时间是整分钟，所以计算下一个整分钟的时间。
        current_time = datetime.datetime.now()
        next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        wait_time = (next_minute - current_time).total_seconds()
        time.sleep(wait_time)
        # 初筛
        with Global_Lock:
            data = self.data.copy()
        A_group, B_group = primary_filter.primary_filter(data, 1999)
        with Global_Lock:
            self.A_group = A_group
            self.B_group = B_group
        # 初筛完成后，计算下一次初筛的时间
        current_time = datetime.datetime.now()
        next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=300)
        wait_time = (next_minute - current_time).total_seconds()
        time.sleep(wait_time)

    def update(self, tick: int) -> None:
        # update时应该上线程锁
        with Global_Lock:
            # update方法应该更新dataframe的内容
            self.data_update()
            for seat in self.seats:
                # seat的data应该也要更新
                seat.data = self.data
                if seat.ENTRY_FLAG:
                    # 开仓
                    if not self.entry(tick, seat):
                        continue
                    logging.info(f'Entry: {seat.symbol} {seat.direction} {seat.entry_price} {seat.position}')
                seat.update(tick)
                logging.info(f'Update done.')
                if seat.EXIT_FLAG:
                    # 平仓
                    logging.info(f'Exit: {seat.symbol} {seat.direction} {self.data[seat.symbol][tick]}')
                    self.exit(tick, seat)
                    logging.info(f'Indicator: {self.indicators}')
            # 程序逻辑完成，计算下一次update的时间
            current_time = datetime.datetime.now()
            next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
            wait_time = (next_minute - current_time).total_seconds()
            self.s.enter(wait_time, 1, self.update, (1999,))

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
        position = math.floor(standard_capital * 0.1 / Backtest_Entry_Increase / entry_price /
                              self.min_qty[symbol][0]) * self.min_qty[symbol][0]
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
        if seat.direction == 'long':
            self.balance += seat.position * current_price / (1 + Trading_Fee)
            difference_rate = (current_price - seat.entry_price) / seat.entry_price
        else:
            self.balance += seat.position * current_price * (1 + Trading_Fee)
            difference_rate = (seat.entry_price - current_price) / seat.entry_price
        self.exit_difference_rates.append(difference_rate)

        seat.symbol = ''
        self.indicator_calculate(seat, tick, current_price)

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
        pd.DataFrame(self.indicators).to_csv('../output/backtest_indicators.csv', index=False)

    def clock(self) -> None:
        while True:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sys.stdout.write("\r" + current_time)
            sys.stdout.flush()
            time.sleep(1)

    def data_init(self) -> pd.DataFrame:
        tickers = self.http.get_tickers(category='linear')
        if tickers['retMsg'] != 'OK':
            raise Exception('Failed to fetch tickers data.')
        tickers['result']['list'] = [ticker for ticker in tickers['result']['list'] if 0.1 <= float(ticker['lastPrice']) <= 7]
        tickers['result']['list'] = [ticker for ticker in tickers['result']['list'] if ticker['symbol'].endswith('USDT')]
        symbols = [each['symbol'] for each in tickers['result']['list']]
        # 获取最后的一个分钟整点
        current_time = datetime.datetime.now()
        last_minute = current_time.replace(second=0, microsecond=0)
        last_stamp = int(last_minute.timestamp() * 1000)
        # 形成以last_stamp向前2000个tick的空dataframe
        data = pd.DataFrame()
        data['timestamp'] = [last_stamp - i * 60000 for i in range(2000)]
        # 时间戳应该大的 index应该大
        data = data.sort_values(by='timestamp', ascending=True)
        data.reset_index(drop=True, inplace=True)
        for symbol in symbols:
            new_column = pd.DataFrame({symbol: [0.0] * 2000})
            data = pd.concat([data, new_column], axis=1)
        return data

    def data_update(self) -> None:
        # 获取最新的tickers数据，并将此时的整分钟timestamp作为concat到data中的timestamp
        tickers = self.http.get_tickers(category='linear')
        if tickers['retMsg'] != 'OK':
            raise Exception('Failed to fetch tickers data.')
        current_prices = {}
        for symbol in self.data.columns:
            if symbol == 'timestamp':
                continue
            current_price = float([ticker['lastPrice'] for ticker in tickers['result']['list'] if ticker['symbol'] == symbol][0])
            current_prices[symbol] = [current_price]
        current_prices['timestamp'] = [self.data['timestamp'][1999] + 60000]
        # 删除self.data的第一行，然后concat一个新的行
        self.data = self.data.drop(0)
        self.data = pd.concat([self.data, pd.DataFrame(current_prices)], ignore_index=True)

    def fetch(self) -> pd.DataFrame:
        # 获取last_minute的timestamp
        current_time = datetime.datetime.now()
        last_minute = current_time.replace(second=0, microsecond=0)
        last_stamp = int(last_minute.timestamp() * 1000)
        # 往前溯源1999个k_lines的数据，只取openPrice
        with Global_Lock:
            data_raw = self.data.copy()
        data_processed = data_raw[['timestamp']]
        for symbol in data_raw.columns:
            if symbol == 'timestamp':
                continue
            # 分两次读取，因为每次只能读1000根k线
            k_lines_1 = self.http.get_kline(
                category='linear',
                symbol=symbol,
                interval='1',
                limit=1000,
                startTime=last_stamp - 1999 * 60000,
                endTime=last_stamp - 1000 * 60000
            )
            k_lines_2 = self.http.get_kline(
                category='linear',
                symbol=symbol,
                interval='1',
                limit=1000,
                startTime=last_stamp - 999 * 60000,
                endTime=last_stamp
            )
            if k_lines_1['retMsg'] != 'OK' or k_lines_2['retMsg'] != 'OK':
                raise Exception('Failed to fetch k_lines data.')
            k_lines = k_lines_1['result']['list'] + k_lines_2['result']['list']
            # 转换为dataframe
            df = pd.DataFrame(k_lines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df[['timestamp', 'open']]
            # 将timestamp转换为整数
            df['timestamp'] = df['timestamp'].apply(lambda x: int(x))
            # 将open转换为float
            df['open'] = df['open'].apply(lambda x: float(x))
            # 将df的open列改名为symbol
            df.rename(columns={'open': symbol}, inplace=True)
            # 按照timestamp合并到data_processed中
            data_processed = pd.merge(data_processed, df, on='timestamp', how='left')
        return data_processed


if __name__ == '__main__':
    realtest = Realtest()
    realtest.run()
