"""
融合data_fetcher、arguments_test、top_arguments_filter三个模块功能
"""

from data_fetcher import data_fetch
from arguments_test import ArgumentsTest
from top_arguments_filter import top_arguments_filter

import sched
import datetime
import time
import threading
import logging

from pybit.unified_trading import HTTP

# 清除root logger的handler
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                    filename='arguments.log', filemode='a')



def arguments(http: HTTP, scheduler: sched.scheduler):

    # fetch data
    data_fetch(http)
    # test arguments
    at = ArgumentsTest()
    at.initialize()
    logging.info('Arguments initialized')

    for param in at.parameters:
        at.run(param)
        # 当时间晚于23:45时，停止计算组合，计算最大组合
        logging.info(f"Argument {at.parameters.index(param) + 1} finished")
        current_time = datetime.datetime.now()
        if current_time.hour == 23 and current_time.minute >= 45:
            at.df_result.to_excel('../data/result.xlsx', index=True)
            top_arguments_filter('../data/tickers_raw.json', '../data/result.xlsx', '../data/wide_group.json')
            current_time = datetime.datetime.now()
            next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
            wait_time = (next_day - current_time).total_seconds()
            scheduler.enter(wait_time, 1, arguments, (http, scheduler))
            return

def main(http):
    # 创建定时任务，每天00:00刷新执行
    s = sched.scheduler()
    # 首次执行先不等待，立刻执行
    wait_time = 0
    s.enter(wait_time, 1, arguments, (http, s))

    # 创建线程
    t = threading.Thread(target=s.run)
    t.daemon = True
    t.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    import dotenv
    import os

    dotenv.find_dotenv()
    http = HTTP(
        api_key=os.getenv('API_KEY'),
        api_secret=os.getenv('API_SECRET'),
        testnet=False
    )

    main(http)



