import pandas as pd

from helpers import arguments_generator as ag
from utils import *


def main():
    """
    Main function.
    先使用argments_generator随机生成参数组合，然后使用Account类进行回测，最后将结果保存到results.csv中。
    :return:
    """

    arguments = ag.generate({
        'history_time': (2, 5, 1),
        'entry_increase': (0.012, 0.02, 0.0002),
        'wave_rate': (0.012, 0.02, 0.0002)
    }, 100)

    results = pd.DataFrame(columns=['history_time', 'entry_increase', 'wave_rate', 'profit_rate', 'trade_count', 'win_rate',
                                    'win_count', 'profit_rate_peak', 'max_profit_rate_single_trade',
                                    'max_loss_rate_single_trade', 'max_draw_down', 'profit_factor', 'total_profit',
                                    'total_loss'])

    for i in range(len(arguments)):
        account = Account(1000, **arguments[i])
        account.run()
        results.loc[i] = [arguments[i]['history_time'], arguments[i]['entry_increase'], arguments[i]['wave_rate'],
                          account.profit_rate, account.trade_count, account.win_rate, account.win_count,
                          account.profit_rate_peak, account.max_profit_rate_single_trade,
                          account.max_loss_rate_single_trade, account.max_draw_down, account.profit_factor,
                          account.total_profit, account.total_loss]
        results.to_csv('output/results.csv', index=False)


if __name__ == '__main__':
    main()