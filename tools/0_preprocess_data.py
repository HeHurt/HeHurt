import pandas as pd

barcode_dict = {'0IJCBA02101111E9C0005830': 'B:E', '0IJCBA02101111E9C0005990': 'J:M', '0IJCBA02101111E9C0005992': 'R:U'}
cycle_dict = {0: 5, 200: 21, 400: 37, 500: 53}
result_list = []
for barcode, usecols in barcode_dict.items():
    for key, value in cycle_dict.items():
        df = pd.read_excel('功率特性.xlsx', sheet_name='leg1', usecols=usecols, nrows=13, header=value, index_col=0)
        df.columns = [80, 50, 20]
        for soc in [20, 50, 80]:
            result = {}
            result['Barcode'] = barcode
            result['cycle'] = key
            result['soc'] = soc
            result['Discharge DCR(mΩ)'] = df.loc['Discharge DCR(mΩ)', soc]
            result['Charge DCR(mΩ)'] = df.loc['Charge DCR(mΩ)', soc]
            result_list.append(result)
result_df = pd.DataFrame(result_list)
result_df.to_csv('DCR_data.csv', index=False)
