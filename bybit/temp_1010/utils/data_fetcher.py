"""
    用于周期性从bybit API获取k线数据。获取规则如下：
    1. 每两小时获取一次。获取时刻为UTC每2小时准点。
    2. 获取下来的数据应该存储在csv文件中，命名为起始时刻的timestamp。使用7天数据，因此共存储7 * 12 = 84个文件。
    4. 对于文件夹中已有timestamp的文件，应该跳过。留存文件数应该要大于7天的，考虑留存上限为30天，即30 * 12 = 360个文件，超过这个数量时，需要删除最后的文件。
    5. 实盘中，这个函数应该塞到主程序中运行，定时器不在这里写出。这个程序本身只作为初筛的数据参考，不作为实盘loop的数据。但是实盘loop的货币对要从初筛里出。
"""

import pandas as pd
import json
from pybit.unified_trading import HTTP
import datetime
import os
from bybit_access import get_kline

import logging
import logging.config

with open('../logging_config.json', 'r') as f:
    config = json.load(f)
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)


# 现在把常量塞到json文件里，读取json文件
with open('../constants.json', 'r') as f:
    constants = json.load(f)
    Primary_Hours = constants['Primary_Hours']
    Interval_Minutes = constants['Interval']
    Data_Keep_Hours = constants['Data_Keep_Hours']
    Volume_Threshold = constants['Volume_Threshold']
    Num_Of_Intervals_Primary = int(Primary_Hours * 60 / Interval_Minutes)
    Num_Of_Intervals_Keep = int(Data_Keep_Hours * 60 / Interval_Minutes)


def data_fetch(http: HTTP) -> None:
    # 拆分为两个函数，获取数据和删除多余数据
    # 获取数据，以当前时刻为基准，上溯到最近的一个2小时整点，再上溯7天作为开始时间戳。假如现在时刻为2024-08-28 10:39:00，
    # 那么第一次上溯到2024-08-28 10:00:00，再上溯7天，即2024-08-21 10:00:00
    # 在获取之前，需要检查是否已经存在了这个时间戳的数据，如果存在，则跳过
    # 获取数据的时间间隔为2小时，获取的数据只包含timestamp和open字段
    # 遍历tickers_raw.json，获取所有货币对
    with open('../data/tickers_raw.json', 'r') as f:
        tickers = json.load(f)
    tickers = {each['symbol']: 'waiting' for each in tickers['result']['list'] if float(each['volume24h']) > Volume_Threshold}
    current_timestamp = int(datetime.datetime.now().timestamp() * 1000)
    # 找到最近的2小时整点
    mark_timestamp = current_timestamp - current_timestamp % (Interval_Minutes * 60 * 1000)
    start_timestamp = mark_timestamp - Primary_Hours * 60 * 60 * 1000
    timestamp_list = [start_timestamp + i * Interval_Minutes * 60 * 1000 for i in range(Num_Of_Intervals_Primary)]
    # 检定是否已经存在该时间戳的数据
    for timestamp in timestamp_list:
        if os.path.exists(f'../data/k_lines/{timestamp}.csv'):
            continue
        else:
            df = fetch(http, timestamp, tickers)
            df.to_csv(f'../data/k_lines/{timestamp}.csv', index=False)
    # 删除多余数据
    delete_extra_data()


def fetch(http: HTTP, timestamp: int, tickers: dict) -> pd.DataFrame:
    df_temp = pd.DataFrame()
    # 初始化timestamp列
    df_temp['timestamp'] = [timestamp + i * 60 * 1000 for i in range(Interval_Minutes)]
    for ticker in tickers.keys():
        try:
            k_lines = get_kline(http, ticker, '1', Interval_Minutes, timestamp, timestamp + (Interval_Minutes - 1) * 60 * 1000)
            df = pd.DataFrame(k_lines['result']['list'],
                              columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            # merge数据
            df.rename(columns={'open': ticker}, inplace=True)
            df = df[['timestamp', ticker]]
            df['timestamp'] = df['timestamp'].astype('int64')
            df_temp = pd.merge(df_temp, df, on='timestamp', how='left')
            logger.info(f'{timestamp} {ticker} data fetched.')
        except Exception as e:
            print(f'Error: {e}')
            continue
    return df_temp


def delete_extra_data() -> None:
    # 删除多余数据，保留最近30天的数据
    timestamp_list = [int(file.split('.')[0]) for file in os.listdir('../data/k_lines') if file.endswith('.csv')]
    timestamp_list.sort()
    if len(timestamp_list) > Num_Of_Intervals_Keep:
        for timestamp in timestamp_list[:len(timestamp_list) - Num_Of_Intervals_Keep]:
            os.remove(f'../data/k_lines/{timestamp}.csv')


# 测试
if __name__ == '__main__':
    import dotenv
    dotenv.find_dotenv()
    dotenv.load_dotenv()
    http = HTTP(
        api_key=os.getenv('API_KEY'),
        api_secret=os.getenv('API_SECRET'),
        testnet=False
    )
    data_fetch(http)
    print('Data fetch completed.')
