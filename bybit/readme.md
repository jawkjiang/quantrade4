# 经验总结
就上次的实盘的情况来说，效果和实测、回测差别很大，这主要是实盘的数据和实测回测数据不一致导致的。实盘使用的是主网，而实测回测使用的是测试网。主网上获取到的k线、tickers数据和测试网获取到的不一样，波动较后者要小得多，这就导致了可筛选的股少、很久不开盘的问题。

既然是实际做交易，肯定要用主网的数据。针对上面这两个问题，可能的解决方法如下：
1. 可筛选的股少：
   - 那初筛就还是用过去19天的数据，而不是24小时，或者7天的数据。
   - 前面测试的经验来看，用主网的价格数据，初筛里交易次数少了很多，7天一般就几次十几次。这也符合之前的预期，毕竟股价不会像测试网里一样不断抖动。
   - 在服务器上要常驻一个项目，每天00:00:00就抓取前一天的k线数据。
2. 很久不开盘：
   - 应不应该为了高频交易降低做空准入的门槛？比如现在准入是3分钟内涨幅达到2.2%进场，降到1.1%，或者更低，交易频次就会高很多。
   - 但就初筛而言，7天内，平均到每支股的交易次数至少也有5次。300支股，19天内，也有1500次交易，平均每天可以到70、80次。
   - 目前的建议是暂时不改门槛，先放着测试。如果不担心账户里那100多USDT，也可以直接上实盘。
   - 之前不开盘可能是程序出了问题，着急忙慌改的，我得再看一看。