import os.path

from utils import Account, SubAccount
from helpers.data_loader import src_loader, args_loader, min_qty_loader
from helpers.arguments_generator import generate, random_index_genenrate
from helpers.outputter import overview_outputter, args_outputter, indexes_outputter, curves_painter

import time


def primarily_filter():
    # Initialize
    data_open = src_loader('data/open.csv')
    data_close = src_loader('data/close.csv')
    """
    In the first roll, the args are generated instead of loading from a file.
    """
    min_qty = min_qty_loader('data/min_qty.csv')
    args_generating_rules = {
        'history_time': (12, 90, 3),
        'stop_loss': (0.05, 0.1, 0.001),
        'rising_rate_restriction': (0.1, 0.2, 0.01),
        'trailing_time': (5, 15, 1),
        'trailing_stop': (0.04, 0.1, 0.001),
        'slope_time': (9, 60, 3),
        'slope_rate': (0, 0.3, 0.01),
    }

    def loop():
        args = generate(args_generating_rules, 5)
        overviews = []
        timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
        for arg in args:
            sub_account = SubAccount(balance=10000, **arg)
            sub_account.load_data(data_open, data_close, 10000, min_qty)
            sub_account.run()
            overviews.append(sub_account.generate_overview())
            print(args.index(arg))
            curves_painter(timestamp, [sub_account.history], args.index(arg))
        # Output
        overview_outputter(timestamp, overviews)
        args_outputter(timestamp, args)


    for i in range(1):
        loop()


def secondarily_filter():
    # Initialize
    data = src_loader('data/src.csv')
    min_qty = min_qty_loader('data/min_qty.csv')
    args = args_loader(('data/args_rank_0.csv', 'data/args_rank_1.csv', 'data/args_rank_2.csv'))

    def loop():
        indexes = random_index_genenrate('data/index.csv', 2000)
        print('Data loaded.')
        overviews = []
        timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
        if not os.path.exists(f"output/{timestamp}"):
            os.makedirs(f"output/{timestamp}")
        for index in indexes:
            account = Account()
            account.load_data(data=data, args=args, min_qty=min_qty, indexes=index)
            account.run()
            curves_painter(timestamp, [account.values], indexes.index(index))
            overviews.append(account.generate_overview())
            print(indexes.index(index))
            del account

        # Output
        overview_outputter(timestamp, overviews)
        indexes_outputter(timestamp, indexes)

    for i in range(6):
        loop()


if __name__ == '__main__':
    primarily_filter()
