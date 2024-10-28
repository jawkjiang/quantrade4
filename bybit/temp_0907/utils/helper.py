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
