import pandas as pd

# 读取Excel文件
df_a = pd.read_excel('result.xlsx')
df_b = pd.read_excel('result_1001.xlsx')

# 合并两个数据框
combined_df = pd.concat([df_b, df_a])

# 删除重复的行，保留第一次出现的行（即文件B中的行）
unique_df = combined_df.drop_duplicates(keep='first')

# 从合并后的数据框中移除所有在unique_df中的行，留下的就是文件A中新增的行
new_rows_df = combined_df.merge(unique_df, indicator=True, how='outer').loc[lambda x : x['_merge']=='right_only'].drop('_merge', axis=1)

# 保存到新的Excel文件
new_rows_df.to_excel('文件C.xlsx', index=False)
