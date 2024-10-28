"""
    经事实考验，WideTest已经有了很好的盈利能力，所以这里需求将arguments_test的功能整合进WideTest中，实现自动化的参数筛选。
    1. 为了降耦合，arguments_test应该仍旧在另一个文件中单独执行，在非逻辑变更的情况下持续运行，输入输出结果也通过外部文件IO实现。
    2. 持续运行的方法，是在每天00:00时刻，首先fetch一遍前一日的k_lines数据，然后执行arguments_test和top_arguments_filter。
        - 除test随机生成的一系列参数外，原来交易过的参数也需要重新测试。
        - 原本数据装载是以表格形式装载，如果原有参数也要测试，表格必然变得稀疏，但是可以考虑历史已交易参数单独filter一遍最佳参数，再和现有参数
            filter完的进行对比，两者取优。也就是说，历史参数应该输出一个历史的最佳组合，随机参数应当返回max的最佳组合，两个组合通过比较profit_rate
            即可选出实际的最佳组合。
        - 历史最佳组合保留50组。
    3. 每天的23:55时刻，arguments_test进行参数出清。得到最好的参数组合后，将其写入wide_group.json供WideCase使用。
    4. 为了避免信道被占，arguments_test不使用和WideCase相同的APIKEY。在每天00:00时刻，重新装载wide_group.json，此时开仓按新参数开仓。
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
from bybit_access import get_marginBalance, get_tickers, get_kline, cancel_order, get_open_orders, place_order,\
    place_limit_order, get_position, close_position, cancel_all_orders
from helper import max_draw_down_calculate

with open('../logging_config.json', 'r') as f:
    config = json.load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

# 常量改由json读取
with open('../constants.json', 'r') as f:
    constants = json.load(f)
    Backtest_Entry_Time = constants['Backtest_Entry_Time_Wide']
    Backtest_Entry_Start = constants['Backtest_Entry_Start_Wide']


class WideCase:
    def __init__(self, http: HTTP):
        self.http = http
        self.data = pd.DataFrame()
        self.lock = threading.Lock()
        self.timestamp = 0
        self.capital = get_marginBalance(http)
        self.Initial_Capital = self.capital
        self.daily_peak_capital = self.capital

        self.group = {}
        self.symbol_daily_loses = {}
        self.freezing_symbols = {}
        self.just_traded_symbols = {}

        # 初始化seats，开两个
        self.seats = [Seat(), Seat()]

        # 初始化定时器
        self.s = sched.scheduler(time.time, time.sleep)
        self.daily_s = sched.scheduler(time.time, time.sleep)

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
        # 先flush
        self.flush()
        # 等待整点，开启定时器
        current_time = datetime.datetime.now()
        # 需要在次日00:00执行daily_flush
        next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        wait_time = (next_day - current_time).total_seconds()
        self.daily_s.enter(wait_time, 0, self.daily_flush, ())

        current_time = datetime.datetime.now()
        next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        wait_time = (next_minute - current_time).total_seconds()
        self.s.enter(wait_time, 1, self.update, (int(next_minute.timestamp() * 1000),))

        # 创建两个线程
        t1 = threading.Thread(target=self.daily_s.run)
        t2 = threading.Thread(target=self.s.run)
        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()

        while True:
            time.sleep(1)

    def flush(self):
        # 先全平仓
        self.close_all()
        # 初始化self.group
        with open('../data/wide_group.json', 'r') as f:
            group = json.load(f)
        # self.group保留前20个币对，或盈利率在20%以上的币对，两者取交集
        group1 = {key: group[key] for key in list(group.keys())[0:20]}
        group2 = {key: group[key] for key in group.keys() if group[key]['profit_rate'] > 0.2}
        self.group = {key: group[key] for key in group1.keys() & group2.keys()}
        self.symbol_daily_loses = {symbol: 0 for symbol in self.group.keys()}
        # 初始化self.data
        self.data = pd.DataFrame(columns=['timestamp'] + list(self.group.keys()))
        data = self.data_init()
        # 按照timestamp将data concat到self.data，data在前，self.data在后
        # 首先要删除data中timestamp与self.data中timestamp相同的行
        data = data[~data['timestamp'].isin(self.data['timestamp'])]
        with self.lock:
            self.data = pd.concat([data, self.data], axis=0)  # 由于trim在update fetch中执行，这里不需要

    def daily_flush(self):
        # 每天00:00执行
        # flush
        self.flush()
        self.Initial_Capital = get_marginBalance(self.http)
        self.daily_peak_capital = self.Initial_Capital
        # 为当前daily_s重新安排任务
        current_time = datetime.datetime.now()
        next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
        wait_time = (next_day - current_time).total_seconds()
        self.daily_s.enter(wait_time, 0, self.daily_flush, ())

    def data_init(self) -> pd.DataFrame:
        # 只获取A_group和B_group中的币对
        data = pd.DataFrame()
        # 找到最近1分钟的整点
        current_time = datetime.datetime.now()
        timestamp = int(current_time.replace(second=0, microsecond=0).timestamp() * 1000)
        # 初始化timestamp列
        data['timestamp'] = [timestamp - (49 - i) * 60 * 1000 for i in range(50)]
        for symbol in self.group.keys():
            k_lines = get_kline(self.http, symbol, '1', 50, timestamp - 49 * 60 * 1000, timestamp)
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
                if len(self.data) == 50:
                    # 使用self.data撮合交易
                    self.trade()
                # 盈利判断，若当日亏损超过一定值，平仓当日仓位并取消所有挂单，不再enter任务，直到daily_flush重新安排任务
                loss_cases = [
                    self.indicators['profit_rate'] < -0.45,
                    self.indicators['profit_rate'] < 0.53 and self.daily_peak_capital / self.Initial_Capital - 1 > 0.7,
                    self.indicators['profit_rate'] < 0.85 and self.daily_peak_capital / self.Initial_Capital - 1 > 1,
                    any([self.symbol_daily_loses[symbol] >= 3 for symbol in self.symbol_daily_loses.keys()])
                ]
                if any(loss_cases):
                    logger.info('Loss exceeds 45% or 53% or 85%.')
                    self.close_all()
                    return
                # 判断freezing_symbols中的币对是否已经解冻
                current_time = datetime.datetime.now()
                for symbol in list(self.freezing_symbols.keys()):
                    if current_time.timestamp() * 1000 - self.freezing_symbols[symbol] > 259200000:  # 72小时
                        del self.freezing_symbols[symbol]
                # 判断just_traded_symbols中的币对是否已经解冻
                for symbol in list(self.just_traded_symbols.keys()):
                    if current_time.timestamp() * 1000 - self.just_traded_symbols[symbol] > 600000:  # 10分钟
                        del self.just_traded_symbols[symbol]
                # 写入定时器的等待时间
                current_time = datetime.datetime.now()
                next_minute = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
                wait_time = (next_minute - current_time).total_seconds()
                self.s.enter(wait_time, 1, self.update, (timestamp + 60000,))
            except Exception:
                logger.error(traceback.format_exc())
                # 平仓退出
                self.close_all()
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
        if len(data) > 50:
            data = data.iloc[-50:].reset_index(drop=True)
        return data

    def trade(self):
        # 撮合交易逻辑
        # 沿用temp中realTrade类的逻辑
        # 似乎不能在平仓后瞬间开仓，我猜测账户到账可能有延迟，
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
                    # 不能用try_except！！！平不掉就再试，五次都平不掉就关程序
                    # 似乎先取消活动止盈单再平仓可以规避ab not enough的问题
                    cancel_order(self.http, seat.symbol, seat.order_id)
                    close_position(self.http, seat.symbol, 'Sell' if seat.side == 'long' else 'Buy')
                    self.exit(seat)
                    continue

            # 如果时间已晚于当日23:30，不再开仓
            current_time = datetime.datetime.now()
            if current_time.hour == 23 and current_time.minute >= 30:
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
        self.capital = get_marginBalance(self.http)
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
        position = int(standard_capital * single_trade_capital / 1000 / Backtest_Entry_Increase / entry_price)
        # place_order
        # 由于bybit的止盈单很怪，下不了，考虑直接市价开仓，然后挂一个止盈点的限价单。止损点自己计算。
        place_order(self.http, symbol, 'Buy' if direction == 'long' else 'Sell', position)
        tp_order = place_limit_order(self.http, symbol, 'Sell' if direction == 'long' else 'Buy', position, tp_price)
        seat.entry(tp_order['result']['orderId'], symbol, entry_price, direction, position * entry_price)
        return

    def coin_filter(self) -> str:
        manual_freezing_symbols = ['PIRATEUSDT']
        for symbol in self.group.keys():
            cases = [
                symbol in [seat.symbol for seat in self.seats],
                symbol in self.freezing_symbols.keys(),
                symbol in self.just_traded_symbols.keys(),
                symbol in manual_freezing_symbols
            ]
            if any(cases):
                continue
            for i in range(Backtest_Entry_Start, Backtest_Entry_Time):
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
        current_time = datetime.datetime.now()
        self.just_traded_symbols[seat.symbol] = current_time.timestamp() * 1000
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

        elif (seat.entry_price >= current_price and seat.side == 'long') or (seat.entry_price <= current_price and seat.side == 'short'):
            self.indicators['total_loses'] += 1
            self.indicators['consecutive_loses'] += 1
            if self.indicators['consecutive_loses'] > self.indicators['max_consecutive_loses']:
                self.indicators['max_consecutive_loses'] = self.indicators['consecutive_loses']
            self.indicators['consecutive_wins'] = 0
            # 更新symbol_daily_loses
            self.symbol_daily_loses[seat.symbol] += 1
            if self.symbol_daily_loses[seat.symbol] >= 3:
                timestamp = int(datetime.datetime.now().timestamp() * 1000)
                self.freezing_symbols[seat.symbol] = timestamp

        if self.capital > 50000:
            # 平仓退出
            raise Exception('Capital exceeds 50000.')
        if self.capital > self.indicators['peak_capital']:
            self.indicators['peak_capital'] = self.capital
        if self.capital > self.daily_peak_capital:
            self.daily_peak_capital = self.capital
        self.indicators['profit_rate'] = self.capital / self.Initial_Capital - 1
        if self.indicators['profit_rate'] > self.indicators['peak_profit_rate']:
            self.indicators['peak_profit_rate'] = self.indicators['profit_rate']
        self.indicators['max_drawdown'] = max_draw_down_calculate(self.capital, self.indicators['peak_capital'],
                                                                  self.indicators['max_drawdown'])

    def close_all(self):
        # 首先要撤销掉所有活动订单
        cancel_all_orders(self.http)

        position = get_position(self.http)
        # 获取position中所有存在仓位的symbol
        symbols = [each['symbol'] for each in position['result']['list']]
        # 测试close_position
        for symbol in symbols:
            try:
                self.http.place_order(category='linear', symbol=symbol, side='Sell', qty=0, reduceOnly=True, orderType='Market')
            except Exception as e:
                print(e)
            try:
                self.http.place_order(category='linear', symbol=symbol, side='Buy', qty=0, reduceOnly=True, orderType='Market')
            except Exception as e:
                print(e)


if __name__ == '__main__':
    import dotenv
    import os
    dotenv.find_dotenv()
    dotenv.load_dotenv()
    http = HTTP(
        api_key=os.getenv('API_KEY_Wide'),
        api_secret=os.getenv('API_SECRET_Wide'),
        testnet=False
    )
    real_test = WideCase(http)
    real_test.run()