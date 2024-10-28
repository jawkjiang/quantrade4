"""
This helper is used to output data to csv files.
"""

import csv
import os
import matplotlib.pyplot as plt


def overview_outputter(timestamp: str, data: list):
    """
    Output overview data to csv files.
    :param timestamp: timestamp of the output
    :param data: overview data
    """
    if not os.path.exists(f"output/{timestamp}"):
        os.makedirs(f"output/{timestamp}")
    with open(f"output/{timestamp}/overview.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['index', *[key for key in data[0].keys()]])
        for index, item in enumerate(data):
            items = [item[key] for key in item.keys()]
            writer.writerow([index, *items])


def args_outputter(timestamp: str, data: list):
    """
    Output args data to csv files.
    :param timestamp: timestamp of the output
    :param data: [{attribute1: value, attribute2: value, ...}, {attribute1: value, attribute2: value, ...}, ...]
    """
    if not os.path.exists(f"output/{timestamp}"):
        os.makedirs(f"output/{timestamp}")
    with open(f"output/{timestamp}/args.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['index', *[key for key in data[0].keys()]])
        for index, item in enumerate(data):
            items = [item[key] for key in item.keys()]
            writer.writerow([index, *items])


def indexes_outputter(timestamp: str, data: list):
    """
    Output indexes data to csv files.
    :param timestamp: timestamp of the output
    :param data: [{
                    0: [index1, index2, ...],
                    1: [index1, index2, ...],
                    ...
                },
                {
                    0: [index1, index2, ...],
                    1: [index1, index2, ...],
                    ...
                },
                ...
                ]
    """
    if not os.path.exists(f"output/{timestamp}/indexes"):
        os.makedirs(f"output/{timestamp}/indexes")
    for i, indexes in enumerate(data):
        with open(f"output/{timestamp}/indexes/{i}.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            for key, value in indexes.items():
                writer.writerow([key, *value])


def curves_painter(timestamp: str, data: list, index: int = 0):
    """
    Output curves to png files.
    :param timestamp: timestamp of the output
    :param data: [
        [
            (tick1, value1),
            (tick2, value2),
            ...
        ],
        [
            (tick1, value1),
            (tick2, value2),
            ...
        ],
        ...
        ]
    :param index: index of the curve
    """
    if not os.path.exists(f"output/{timestamp}/curves"):
        os.makedirs(f"output/{timestamp}/curves")
    for i, curve in enumerate(data):
        for item in curve:
            if isinstance(item, tuple):
                x = [item[0] for item in curve]
                y = [item[1] for item in curve]
                plt.plot(x, y)
            else:
                y = curve
                plt.plot(y)
        plt.savefig(f"output/{timestamp}/curves/{i}_{index}.png")
        plt.close()


if __name__ == "__main__":
    timestamp = "20210101000000"
    data = [
        [1, 2, 3, 4, 5]
    ]
    curves_painter(timestamp, data)
