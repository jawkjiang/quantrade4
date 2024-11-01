# 抛硬币策略
本策略是基于货币对的历史极短时上涨/下跌特性（几分钟范围内）进行初筛，再以最近
该特性进行选股的思路进行的。它的具体实现思路如下：
## 1. 数据准备
已准备2024年8月12日00:00:00时刻，往前500,000分钟，所有lastPrice > 0的
bybit合约交易数据，共300余支。经过合并merge后，将500,000分钟的所有
openPrice合并到50张csv表格中，每张表格存储10,000个tick所有合约的openPrice。

由于回测数据量过大，且需要避免交易价格过低或过高的货币对，现在需要重新整理最近50000个tick，
且价格在0.01~7 USDT的货币对openPrice数据，最终存储在一张表中。
## 2. 初筛
回测backtest中，每5个小时需要对300余支货币对进行初筛，规则如下：

- 过去456小时（19日），对每支货币对进行纵向回测。
- 若该货币对符合如下条件，则进场：
    - 最近2个openPrice中，若第二个较第一个上涨了2.2%，则做空进场
    - 上述条件若不符合，则最近3个openPrice中，若第三个较第一个上涨了2.2%，则做空进场
- 进场后：
    - 若上涨1.1%，则平仓
    - 若下跌1.1%，也平仓
- 筛选出如下两组货币对：

第一组（标记为A组）：

| 交易次数  | 胜率     |
|-------|--------|
| \>=9  | \>63%  |
| \=8   | \>7/8  |
| \=7   | \>6/7  |
| \=4~6 | \=100% |
| \=0~3 | 不考虑    |

第二组（标记为B组）：    

| 交易次数  | 胜率    |
|-------|-------|
| \>=9  | \<37% |
| \=8   | \<1/8 |
| \=7   | \<1/7 |
| \=4~6 | \=0%  |
| \=0~3 | 不考虑   |

（这个数值怎么来的我也不知道）

- 筛选出两组货币后，若：
    - A组的货币对支数 > 15支，则将A组按胜率正向排序，剔除胜率15名之外的货币对
    - B组的货币对支数 > 15支，则将B组按胜率反向排序，剔除胜率15名之外的货币对
## 选股回测
同时监测A、B两组，若存在任何一支货币对符合如下条件，则进场：

A组：
- 最近2个openPrice中，若第二个较第一个上涨了2.2%，则做空进场
- 上述条件若不符合，则最近3个openPrice中，若第三个较第一个上涨了2.2%，则做空进场

B组：
- 最近2个openPrice中，若第二个较第一个上涨了2.2%，则做多进场
- 上述条件若不符合，则最近3个openPrice中，若第三个较第一个上涨了2.2%，则做多进场

回测保持在两个座位。当存在座位空置时，上述进场监测启动，否则不启动。
## 本金和进场金额
本金：
- 初始本金为1000 USDT。
- 进场后，本金实际为marginBalance保证金。它由当前账户余额 + 已进场座位的市值得到。

标定本金：
- 以1000 USDT为基准，当本金落在[1000 * 2^n, 1000 * 2^(n+1))范围内时（其中n为整数），标定本金为1000 * 2^n。

进场金额：
- 进场金额由如下公式计算：
  - 总是希望每一次交易盈余或亏损的金额为标定本金的10%。
  - 每一次止盈止损线为进场价格的正负1.1%，即每一次交易的止盈止损金额为进场金额的正负1.1%。
  - 标定本金 * 10% = 进场金额 * 1.1%，即进场金额为标定本金 * 100 / 11，杠杆率约为10。
