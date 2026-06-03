"""
处理 CW391(C组) + CW511(G组) 仿真支持数据
输出 .dat 文件：每个文件 = 一个型号 + 一个温度 + 所有倍率的充放电曲线
列格式: 0.125P_chg_Cap  0.125P_chg_Volt  0.125P_dis_Cap  0.125P_dis_Volt  0.25P_chg_Cap  ...
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

BASE = Path(r"d:\Users\hez\Desktop\314\CW391+CW511-仿真支持数据 to 何争")
OUTPUT = BASE / "dat_output"
OUTPUT.mkdir(exist_ok=True)

RATES = ["0.125P", "0.25P", "0.5P"]
TEMPS = ["25℃", "45℃"]

# 电芯编码 -> 组别映射 (C=CW391, G=CW511)
# C组: PD26012114C开头, G组: PD26012114G开头

CYCLE_TO_USE = 3  # 选取第3圈（稳定循环）


def get_group(cell_code: str) -> str:
    """根据电芯编码判断组别"""
    if "C0" in cell_code:
        return "C"
    elif "G0" in cell_code:
        return "G"
    return ""


def find_first_cell_file(rate: str, temp: str, group: str) -> tuple:
    """找到指定倍率、温度、组别下的第一个电芯文件"""
    folder = BASE / rate / temp
    if not folder.exists():
        return None, None
    for cell_dir in sorted(folder.iterdir()):
        if not cell_dir.is_dir():
            continue
        cell_code = cell_dir.name
        if get_group(cell_code) != group:
            continue
        # 找xlsx文件（排除断点数据等临时文件）
        xlsx_files = [f for f in cell_dir.iterdir()
                      if f.suffix == '.xlsx' and '断点' not in f.name]
        if xlsx_files:
            return cell_code, xlsx_files[0]
    return None, None


def extract_curve(filepath: Path, cycle: int) -> tuple:
    """
    从xlsx文件提取指定循环的充放电曲线
    返回 (chg_cap, chg_volt, dis_cap, dis_volt)
    """
    print(f"  Reading: {filepath.name} ...")
    df = pd.read_excel(filepath, sheet_name='记录层', engine='calamine')
    needed_cols = ['电压(V)', '充电容量(Ah)', '放电容量(Ah)', '循环号', '工步类型']
    df = df[needed_cols]

    # 充电曲线
    chg = df[(df['循环号'] == cycle) & (df['工步类型'].str.contains('充电', na=False))].copy()
    chg_cap = chg['充电容量(Ah)'].values
    chg_volt = chg['电压(V)'].values

    # 放电曲线
    dis = df[(df['循环号'] == cycle) & (df['工步类型'].str.contains('放电', na=False))].copy()
    dis_cap = dis['放电容量(Ah)'].values
    dis_volt = dis['电压(V)'].values

    print(f"    Cycle {cycle}: charge {len(chg_cap)} pts, discharge {len(dis_cap)} pts")
    return chg_cap, chg_volt, dis_cap, dis_volt


def main():
    for group in ["C", "G"]:
        group_name = "CW391" if group == "C" else "CW511"
        for temp in TEMPS:
            print(f"\n=== {temp}-{group} ({group_name}) ===")
            all_data = {}  # rate -> (chg_cap, chg_volt, dis_cap, dis_volt)
            max_len = 0

            for rate in RATES:
                cell_code, filepath = find_first_cell_file(rate, temp, group)
                if filepath is None:
                    print(f"  {rate}: No data found!")
                    continue
                print(f"  {rate}: {cell_code}")
                chg_cap, chg_volt, dis_cap, dis_volt = extract_curve(filepath, CYCLE_TO_USE)
                all_data[rate] = (chg_cap, chg_volt, dis_cap, dis_volt)
                max_len = max(max_len, len(chg_cap), len(dis_cap))

            if not all_data:
                print("  No data, skipping.")
                continue

            # 构建列数据，短列用NaN填充
            columns = []
            headers = []
            for rate in RATES:
                if rate not in all_data:
                    continue
                chg_cap, chg_volt, dis_cap, dis_volt = all_data[rate]

                def pad(arr):
                    padded = np.full(max_len, np.nan)
                    padded[:len(arr)] = arr
                    return padded

                columns.extend([pad(chg_cap), pad(chg_volt), pad(dis_cap), pad(dis_volt)])
                headers.extend([
                    f"{rate}_chg_Cap(Ah)", f"{rate}_chg_Volt(V)",
                    f"{rate}_dis_Cap(Ah)", f"{rate}_dis_Volt(V)"
                ])

            # 写 .dat 文件
            out_file = OUTPUT / f"{temp}-{group}({group_name}).dat"
            data = np.column_stack(columns)
            with open(out_file, 'w') as f:
                # f.write('\t'.join(headers) + '\n')
                for row in data:
                    vals = []
                    for v in row:
                        if np.isnan(v):
                            vals.append('')
                        else:
                            vals.append(f"{v:.5f}")
                    f.write('\t'.join(vals) + '\n')

            print(f"  -> Saved: {out_file.name} ({max_len} rows, {len(headers)} cols)")


if __name__ == '__main__':
    main()
