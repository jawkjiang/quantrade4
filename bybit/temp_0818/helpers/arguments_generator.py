import random
import csv

"""
This helper is used to generate random arguments for backtesting.
"""


def generate(rules: dict, n: int = 10) -> list:
    """
    Generate random arguments for backtesting.
    :param rules: {"attribute": (start, end, step_length)}
    :param n: number of arguments to generate
    :return: result: [{attribute1: value, attribute2: value, ...}, {attribute1: value, attribute2: value, ...}, ...]
    """
    result = []
    i = 0
    while i < n:
        temp = {}
        for key, value in rules.items():
            if isinstance(value, tuple):
                start, end, step_length = value
                steps = int((end - start) / step_length)
                num = start + random.randint(0, steps) * step_length
            else:
                num = value
            temp[key] = num
        result.append(temp)
        i += 1
    return result


def random_index_genenrate(file_path: str, n: int = 10):
    """
    Generate random index for backtesting.
    :param file_path: file path
    :param n: number of index to generate
    :return: result: [{
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
    result = []
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        src = []
        for line in reader:
            src.append([int(i) for i in line if i.strip()])
    while len(result) < n:
        temp = {}
        for j in range(len(src)):
            list_to_shuffle = src[j].copy()
            random.shuffle(list_to_shuffle)
            temp[j] = list_to_shuffle
        if temp not in result:
            result.append(temp.copy())
    return result


if __name__ == "__main__":
    random_index_genenrate('../data/index.csv', 2)