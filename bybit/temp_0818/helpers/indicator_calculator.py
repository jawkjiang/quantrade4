"""
This helper contains some useful functions to calculate indicators.
"""


def trailing_stop_loss_calculate(price, stop_loss_price, rate) -> float:
    """
    Calculate trailing stop loss price.
    :param price: current price
    :param stop_loss_price: latest stop loss price
    :param rate: trailing stop loss rate
    :return: new_stop_loss_price
    """
    new_stop_loss_price = max(price * (1 - rate), stop_loss_price)
    return new_stop_loss_price


def max_draw_down_calculate(value, value_peak, max_draw_down) -> float:
    """
    Calculate max draw down.
    :param value: current value
    :param value_peak: peak value
    :param max_draw_down: max draw down
    :return: new_max_draw_down
    """
    draw_down = (value_peak - value) / value_peak
    new_max_draw_down = max(draw_down, max_draw_down)
    return new_max_draw_down


def slope_calculate(open_prices: list, close_prices: list, tick: int, period: int) -> float:
    """
    Calculate slope.
    :param open_prices: open prices
    :param close_prices: close prices
    :param tick: current tick
    :param period: length of sliding window
    :return: slope
    """
    slopes = []
    for i in range(period):
        start_price = open_prices[tick - period + i]
        end_price = close_prices[tick - period + i]
        temp = end_price - start_price
        if temp >= 0:
            slopes.append(temp)
    if len(slopes) < 2 * period / 3:
        return 0
    start_price = open_prices[tick - period]
    end_price = close_prices[tick]
    slope = (end_price - start_price) / start_price
    return slope

