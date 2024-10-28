"""
This helper is used to combine output csvs into a whole part.
"""


import pandas as pd
import os


def combine(src_path: str, tp: str):
    """
    :param src_path: src path of csvs
    :param tp: overview or args
    :return:
    """
    data = pd.DataFrame()
    pd.DataFrame(os.listdir(src_path)).to_csv(src_path+"/order.csv", index=False)
    for directory in os.listdir(src_path):
        dir_path = os.path.join(src_path, directory)
        if os.path.isdir(dir_path):
            for file in os.listdir(dir_path):
                if file == tp+".csv":
                    df = pd.read_csv(src_path+"/"+directory+"/"+file, encoding="utf-8")
                    df.drop(df.columns[0], axis=1, inplace=True)
                    data = pd.concat([data, df], ignore_index=True)
    data.index.name = 'index'
    data.to_csv(src_path+"/"+tp+".csv", index=True)


if __name__ == "__main__":
    combine("../output/second", "overview")
