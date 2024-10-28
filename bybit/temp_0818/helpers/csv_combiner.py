import os
import pandas as pd


def csv_concat():
    for directory in os.listdir('../../data'):
        # 忽略 merged 文件夹
        if directory == 'merged':
            continue
        dir_path = os.path.join('../../data', directory)
        if os.path.isdir(dir_path):
            # 删除 ".csv.csv" 结尾的文件
            for file in os.listdir(dir_path):
                if file.endswith('.csv.csv'):
                    os.remove(os.path.join(dir_path, file))
            # 忽略已经 merge 过的文件夹，即文件夹下有 merged_ 开头的文件，且数量为 50
            if len([file for file in os.listdir(dir_path) if file.startswith('merged_')]) == 50:
                continue
            csv_files = [file for file in os.listdir(dir_path) if file.endswith('.csv') and not file.startswith('merged')]
            # 将 csv_files 按照时间戳排序
            csv_files.sort(key=lambda x: int(x.split('-')[1].split('.')[0]))
            for i in range(50):
                df = pd.DataFrame()
                for j in range(10):
                    file_path = os.path.join(dir_path, csv_files[i * 10 + j])
                    temp_df = pd.read_csv(file_path)

                    # 确保只保留 timestamp 和 open 列，防止其他无关列干扰
                    temp_df = temp_df[['timestamp', 'open']]

                    # 将数据合并到主 DataFrame 中
                    df = pd.concat([df, temp_df], ignore_index=True)

                # 保留 NaN 数据的行
                timestamp = csv_files[i * 10].split('-')[1].split('.')[0]
                output_file = os.path.join(dir_path, f'merged_{timestamp}.csv')
                df.to_csv(output_file, index=False, na_rep='NaN')


def csv_merge():
    dir_list = [os.path.join('../../data', directory) for directory in os.listdir('../../data')
                if os.path.isdir(os.path.join('../../data', directory)) and directory != 'merged']

    for i in range(50):
        # 若当前i已经合并过，则跳过
        if len([file for file in os.listdir('../../data/merged') if file.startswith(f'merged_{i}')]) == 1:
            print(f'merged_{i}.csv already exists.')
            # continue
        df = None
        for dir_path in dir_list:
            directory_name = os.path.basename(dir_path).replace('\\', '_').replace('/', '_')
            # 获取合并后的文件名
            merged_files = [file for file in os.listdir(dir_path) if file.startswith('merged_')]
            merged_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
            file_path = os.path.join(dir_path, merged_files[i])
            temp_df = pd.read_csv(file_path)

            # 重命名 'open' 列为当前目录名
            temp_df.rename(columns={'open': directory_name}, inplace=True)

            # 合并数据帧，按 timestamp 进行合并
            if df is None:
                df = temp_df
            else:
                df = pd.merge(df, temp_df, on='timestamp', how='outer')

        # 保存最终合并的文件
        output_file = f'../data/merged/merged_{i}.csv'
        df.to_csv(output_file, index=False, na_rep='NaN')
        print(f'merged_{i}.csv saved.')


if __name__ == '__main__':
    # csv_concat()
    csv_merge()
