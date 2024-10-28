import pandas as pd
import os


def main(_type: str):
    data = pd.DataFrame()

    counter = 0
    for directory in os.listdir("../data"):
        dir_path = os.path.join("../data", directory)
        if os.path.isdir(dir_path):
            temp = pd.DataFrame()
            file_lines = [file for file in os.listdir(dir_path)]
            file_lines.sort(key=lambda x: int(x.split("-")[1].split(".")[0]))
            for file in file_lines:
                df = pd.read_csv(dir_path + "/" + file, encoding="utf-8", na_values="")
                # select out the open price column
                _open = df[[_type]]
                # complement the missing values if the column's length is less than 1000
                if len(_open) < 1000:
                    _open = _open.reindex(range(1000)).fillna(value="")
                # merge it with the main dataframe
                temp = pd.concat([temp, _open], ignore_index=True)
                counter += 1
                if counter % 100 == 0:
                    print(f"Processed {counter} files.")
            data[directory] = temp[_type]

    data.to_csv(f"../data/{_type}.csv", index=False)


if __name__ == "__main__":
    main("open")
    main("close")


