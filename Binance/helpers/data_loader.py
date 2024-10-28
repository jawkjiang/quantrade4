"""
This helper is used to load data from csv files.
"""

import csv


def src_loader(file_path: str) -> dict:
    """
    Load data from csv files.
    :param file_path: file path
    :return: data: list
    """
    data = {}
    count = 0
    # Each line contains open prices for all available symbols by each tick.
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for header in headers:
            data[header] = []
        for line in reader:
            for i, value in enumerate(line):
                if value == '':
                    value = 0
                data[headers[i]].append(float(value))
            count += 1
            if count % 1000 == 0:
                print(f'Loading {count} ticks.')
            if count == 100000:
                break
    return data


def args_loader(src_paths: tuple) -> dict:
    """
    Load arguments from csv files.
    :param src_paths: file paths
    :return: result: {
                        0: {
                            index1: {
                                    arg1: value1,
                                    arg2: value2,
                                    ...
                                    },
                            index2: {
                                    arg1: value1,
                                    arg2: value2,
                                    ...
                                    },
                            ...
                        },
                        1: {
                            index1: {
                                    arg1: value1,
                                    arg2: value2,
                                    ...
                                    },
                            index2: {
                                    arg1: value1,
                                    arg2: value2,
                                    ...
                                    },
                            ...
                        },
                        ...
                    }
    """
    result = {}
    for src_path in src_paths:
        result[src_paths.index(src_path)] = {}
        with open(src_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for line in reader:
                index = int(line.pop(0))
                result[src_paths.index(src_path)][index] = {}
                for header, value in zip(headers[1:], line):
                    result[src_paths.index(src_path)][index][header] = float(value)
    return result


def min_qty_loader(file_path: str) -> dict:
    """
    Load min_qty from csv files.
    :param file_path: file path
    :return: data: dict
    """
    data = {}
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        values = next(reader)
        for header, value in zip(headers, values):
            data[header] = float(value)
    return data


if __name__ == "__main__":
    args_loader(('../data/args_rank_0.csv', '../data/args_rank_1.csv', '../data/args_rank_2.csv'))
    print(min_qty_loader('../data/min_qty.csv'))
