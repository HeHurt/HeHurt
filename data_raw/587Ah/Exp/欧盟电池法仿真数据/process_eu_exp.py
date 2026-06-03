"""
process_eu_exp.py
将 "587Ah-cell performance.xlsx" 中 "Cycling at 25℃ and 45℃" sheet 的原始数据
整理为标准 CSV，供欧盟电池法 Notebook 直接加载对标。

输出列：
  real_cycle_25c      — 25°C 真实圈数（原表提供，后半段可能为空）
  real_cycle_45c      — 45°C 真实圈数（原表提供，后半段可能为空）
  exp_cycle_25c       — 25°C 原始循环号（1,2,3,...）
  exp_cycle_45c       — 45°C 原始循环号（1,2,3,...）
  dchg_cap_25c_avg    — 25°C 两只电芯平均放电容量 (Ah)
  cap_ret_25c_avg     — 25°C 平均容量保持率（相对各自首圈，小数，0–1）
  eff_25c_avg         — 25°C 平均能量效率（小数，0–1）
  dchg_cap_45c_avg    — 45°C 两只电芯平均放电容量 (Ah)
  cap_ret_45c_avg     — 45°C 平均容量保持率（相对各自首圈，小数，0–1）
  eff_45c_avg         — 45°C 平均能量效率（小数，0–1）

用法：
  python process_eu_exp.py          # 在本脚本所在目录生成 eu_cycling_exp.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).parent
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_EXCEL_PATH = WORKSPACE_ROOT / "data_raw" / "587Ah" / "587Ah-cell performance.xlsx"
LEGACY_EXCEL_PATH = SCRIPT_DIR / "587Ah-cell performance.xlsx"
EXCEL_PATH = CANONICAL_EXCEL_PATH if CANONICAL_EXCEL_PATH.exists() else LEGACY_EXCEL_PATH
OUTPUT_CSV = SCRIPT_DIR / "eu_cycling_exp.csv"

SHEET = "Cycling at 25\u2103 and 45\u2103"

# --- 列索引（0-based，与原始 header=None 读取一致） ---
# 真实圈数列（两组共用 col9 和 col32）
COL_REAL_CYCLE_AB = 9     # 25°C 两组 & 45°C 两组共用
COL_REAL_CYCLE_CD = 32

# 25°C cell1 (Block A)
COL_A_CYCLE = 10
COL_A_DCHG  = 12
COL_A_CRET  = 15   # 原始值 = dchg / nominal，非首圈归一；后处理再归一
COL_A_EFF   = 17

# 25°C cell2 (Block B)
COL_B_CYCLE = 20
COL_B_DCHG  = 22
COL_B_CRET  = 25
COL_B_EFF   = 27

# 45°C cell1 (Block C)
COL_C_CYCLE = 33
COL_C_DCHG  = 35
COL_C_CRET  = 38
COL_C_EFF   = 40

# 45°C cell2 (Block D)
COL_D_CYCLE = 43
COL_D_DCHG  = 45
COL_D_CRET  = 48
COL_D_EFF   = 50


def _extract_block(df, col_real_cycle, col_cycle, col_dchg, col_cret, col_eff, label=""):
    """提取一个数据块，返回以 exp_cycle 为索引的 DataFrame。"""
    sub = df.iloc[3:, [col_real_cycle, col_cycle, col_dchg, col_cret, col_eff]].copy()
    sub.columns = ["real_cycle", "exp_cycle", "dchg_cap", "cap_ret_raw", "eff"]
    sub = sub.dropna(subset=["exp_cycle", "dchg_cap"])
    sub["real_cycle"] = pd.to_numeric(sub["real_cycle"], errors="coerce")
    sub["exp_cycle"] = pd.to_numeric(sub["exp_cycle"], errors="coerce")
    sub["exp_cycle"] = sub["exp_cycle"].astype(int)
    sub["dchg_cap"] = pd.to_numeric(sub["dchg_cap"], errors="coerce")
    sub["eff"] = pd.to_numeric(sub["eff"], errors="coerce")
    # 归一化容量保持率：相对各自首圈放电容量（剔除 NaN）
    first_cap = sub["dchg_cap"].dropna().iloc[0] if not sub["dchg_cap"].dropna().empty else np.nan
    sub["cap_ret"] = sub["dchg_cap"] / first_cap if np.isfinite(first_cap) else np.nan
    sub = sub[["real_cycle", "exp_cycle", "dchg_cap", "cap_ret", "eff"]].set_index("exp_cycle")
    if label:
        sub.columns = [f"{c}_{label}" for c in sub.columns]
    return sub


def main():
    print(f"读取: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET, header=None)
    print(f"原始数据形状: {df.shape}")

    # 提取四个块
    blk_a = _extract_block(df, COL_REAL_CYCLE_AB, COL_A_CYCLE, COL_A_DCHG, COL_A_CRET, COL_A_EFF, "a")
    blk_b = _extract_block(df, COL_REAL_CYCLE_AB, COL_B_CYCLE, COL_B_DCHG, COL_B_CRET, COL_B_EFF, "b")
    blk_c = _extract_block(df, COL_REAL_CYCLE_CD, COL_C_CYCLE, COL_C_DCHG, COL_C_CRET, COL_C_EFF, "c")
    blk_d = _extract_block(df, COL_REAL_CYCLE_CD, COL_D_CYCLE, COL_D_DCHG, COL_D_CRET, COL_D_EFF, "d")

    # 合并并取均值
    merged_25 = blk_a.join(blk_b, how="outer")
    merged_45 = blk_c.join(blk_d, how="outer")

    result = pd.DataFrame(index=merged_25.index.union(merged_45.index))
    result.index.name = "exp_cycle"

    result["real_cycle_25c"]   = merged_25[["real_cycle_a", "real_cycle_b"]].mean(axis=1)
    result["exp_cycle_25c"]    = result.index
    result["dchg_cap_25c_avg"] = merged_25[["dchg_cap_a", "dchg_cap_b"]].mean(axis=1)
    result["cap_ret_25c_avg"]  = merged_25[["cap_ret_a",  "cap_ret_b"]].mean(axis=1)
    result["eff_25c_avg"]      = merged_25[["eff_a",       "eff_b"]].mean(axis=1)
    result["real_cycle_45c"]   = merged_45[["real_cycle_c", "real_cycle_d"]].mean(axis=1)
    result["exp_cycle_45c"]    = result.index
    result["dchg_cap_45c_avg"] = merged_45[["dchg_cap_c", "dchg_cap_d"]].mean(axis=1)
    result["cap_ret_45c_avg"]  = merged_45[["cap_ret_c",  "cap_ret_d"]].mean(axis=1)
    result["eff_45c_avg"]      = merged_45[["eff_c",       "eff_d"]].mean(axis=1)

    result = result.sort_index().reset_index()
    result.to_csv(OUTPUT_CSV, index=False, float_format="%.6f")
    print(f"已输出: {OUTPUT_CSV}  ({len(result)} 行)")
    print(result.head(5).to_string())


if __name__ == "__main__":
    main()
