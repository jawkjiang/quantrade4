import os

def count_files_in_directory():
    base_path = '../data'
    for directory in os.listdir(base_path):
        dir_path = os.path.join(base_path, directory)
        if os.path.isdir(dir_path):
            # 获取文件夹中的所有文件
            all_files = os.listdir(dir_path)
            # 过滤出 CSV 文件
            csv_files = [file for file in all_files if file.endswith('.csv')]
            # 输出文件夹名和文件数量
            print(f"Directory: {directory}, CSV file count: {len(csv_files)}")

if __name__ == '__main__':
    count_files_in_directory()
