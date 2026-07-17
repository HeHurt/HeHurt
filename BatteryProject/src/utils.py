"""通用 IO 与辅助函数。"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis import get_discharge_capacity
from .exp_loader import normalize_retention_scale

logger = logging.getLogger(__name__)


def safe_var_access(step, candidates):
    """从候选变量名中返回首个可用变量。"""
    for name in candidates:
        try:
            return step[name].entries
        except Exception:
            continue
    raise KeyError(f"未找到任何可用变量: {candidates}")


class BatteryDataLoader:
    def __init__(self):
        self.COLUMN_MAPPING = {
            "cycle": ["Cycle Index", "Cycle", "Cycle_ID", "循环", "圈数", "Cyc#"],
            "step": ["Step Index", "Step", "Step_ID", "工步", "Step Type"],
            "time": ["Time", "Test Time", "Total Time", "时间", "测试时间", "t"],
            "voltage": ["Voltage", "Voltage(V)", "Volts", "V", "电压", "电压(V)"],
            "current": ["Current", "Current(A)", "Amps", "I", "电流", "电流(A)"],
            "capacity": ["Capacity", "Cap", "Ah", "Capacity(Ah)", "容量", "放电容量"],
            "energy": ["Energy", "Wh", "Energy(Wh)", "能量"],
        }
        self.HEADER_KEYWORDS = ["Voltage", "Current", "Time", "Cycle", "Step", "电压", "电流", "时间", "循环", "容量"]

    def _find_header_row_index(self, file_path, sheet_name=0, scan_rows=30):
        try:
            df_temp = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=scan_rows)
        except Exception as e:
            logger.warning("Header pre-read failed: %s", e)
            return 0
        max_score = 0
        best_row_index = 0
        for idx, row in df_temp.iterrows():
            row_str = " ".join([str(val) for val in row.values if pd.notna(val)])
            score = sum(1 for kw in self.HEADER_KEYWORDS if kw.lower() in row_str.lower())
            if score > max_score:
                max_score = score
                best_row_index = idx
        if max_score == 0:
            logger.warning("未在前 %d 行中检测到表头特征，默认使用第 1 行。", scan_rows)
            return 0
        logger.info("自动检测到表头在第 %d 行 (匹配度: %d)", best_row_index + 1, max_score)
        return best_row_index

    def _standardize_columns(self, df):
        new_df = df.copy()
        for std_key, aliases in self.COLUMN_MAPPING.items():
            found = False
            for col in df.columns:
                col_str = str(col).strip()
                for alias in aliases:
                    if alias.lower() in col_str.lower():
                        new_df.rename(columns={col: std_key}, inplace=True)
                        found = True
                        break
                if found:
                    break
        return new_df

    def load_data(self, file_path, sheet_name=0):
        header_idx = self._find_header_row_index(file_path, sheet_name)
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_idx)
        return self._standardize_columns(df)


def load_excel_to_plotter(plotter_instance, file_path, sheet_names=None):
    """读取 Excel 并注入实验曲线到 BatteryPlotter。"""
    try:
        xl = pd.ExcelFile(file_path)
        sheets = xl.sheet_names if sheet_names is None or sheet_names == "all" else sheet_names
    except Exception as e:
        logger.error("无法读取 Excel 文件信息: %s", e)
        return
    for sheet in sheets:
        try:
            df_meta = pd.read_excel(file_path, sheet_name=sheet, header=None, nrows=1)
            labels_row = df_meta.iloc[0].ffill().values
            df_data = pd.read_excel(file_path, sheet_name=sheet, header=2)
            df_data = df_data.dropna(subset=[df_data.columns[0]])
            x_data = df_data.iloc[:, 0].values
            temp_storage = {}
            for i, col_name in enumerate(df_data.columns):
                if i >= len(labels_row):
                    break
                label = str(labels_row[i])
                if pd.isna(label) or label == "nan":
                    continue
                if label not in temp_storage:
                    temp_storage[label] = {}
                col_data = df_data.iloc[:, i].values
                if "放电容量" in str(col_name):
                    temp_storage[label]["cap"] = col_data
                elif "容量保持率" in str(col_name):
                    # 统一为 0–1 小数（百分制自动 /100），与 exp_loader 契约一致
                    temp_storage[label]["ret"] = normalize_retention_scale(col_data)
            count = 0
            for lbl, vals in temp_storage.items():
                if "cap" in vals and "ret" in vals:
                    plotter_instance.add_exp_data(lbl, x_data, vals["cap"], vals["ret"])
                    count += 1
            logger.info("工作表 %r 读取完成，添加了 %d 条曲线", sheet, count)
        except Exception as e:
            logger.warning("读取工作表 %r 失败: %s", sheet, e)


def process_sol_list_with_custom_extractor(plotter_instance, sol_list, label_list, t_factor=50):
    """处理仿真结果并注入放电容量曲线。"""
    logger.info("处理 %d 个仿真结果 (加速因子=%d)...", len(sol_list), t_factor)
    for sol, label in zip(sol_list, label_list):
        try:
            res = get_discharge_capacity(sol)
            cap_data = res["discharge_capacity"]
            valid_mask = ~np.isnan(cap_data)
            cap_clean = cap_data[valid_mask]
            if len(cap_clean) > 0:
                cap_Ah = cap_clean
                raw_cycles = np.arange(0, len(cap_Ah))
                real_cycles = raw_cycles * t_factor
                # 首圈通常是 conditioning，保持率以第 2 圈为基线；单圈数据退回首圈
                base_cap = cap_Ah[1] if cap_Ah.size > 1 else cap_Ah[0]
                retention = cap_Ah / base_cap  # 0–1 小数，与 exp_loader 契约一致
                plotter_instance.add_sim_data(label, real_cycles, cap_Ah, retention)
        except Exception as e:
            logger.error("%s 错误: %s", label, e)


def load_dat_folder_to_plotter(
    plotter_instance,
    folder_path,
    pattern="**/*.dat",
    label_mode="relative",
    t_factor=1,
    flip_negative_capacity=True,
):
    """读取文件夹内 .dat 文件，并注入实验曲线到 BatteryPlotter。

    约定：每个 .dat 文件前两列分别为：循环圈数、放电容量。

    参数
    - folder_path: 文件夹路径
    - pattern: glob 模式，默认递归读取所有 .dat
    - label_mode: 'relative' | 'stem'
        - relative: 用相对路径(不含扩展名)作为 label，适配子文件夹
        - stem: 仅用文件名(不含扩展名)作为 label
    - t_factor: 循环圈数缩放因子（例如仿真/实验对齐时 1 圈代表 50 圈）
    - flip_negative_capacity: 若容量整体为负，自动取相反数（常见于放电为负号的导出格式）

    返回
    - labels: 实际注入的 label 列表
    """

    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"未找到文件夹: {folder}")

    files = sorted(folder.glob(pattern))
    if not files:
        logger.warning("未找到任何 dat 文件: %s / %s", folder, pattern)
        return []

    labels = []
    for f in files:
        try:
            df = pd.read_csv(
                f,
                sep=r"\s+",
                header=None,
                engine="python",
                comment="#",
            )
            if df.shape[1] < 2:
                logger.warning("跳过 %s: 列数不足 2", f.name)
                continue

            cycles = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy(dtype=float)
            cap = pd.to_numeric(df.iloc[:, 1], errors="coerce").to_numpy(dtype=float)

            mask = np.isfinite(cycles) & np.isfinite(cap)
            cycles = cycles[mask]
            cap = cap[mask]
            if cycles.size < 2:
                logger.warning("跳过 %s: 有效点太少", f.name)
                continue

            order = np.argsort(cycles)
            cycles = cycles[order] * float(t_factor)
            cap = cap[order]

            if flip_negative_capacity and np.nanmedian(cap) < 0:
                cap = -cap

            base = cap[0]
            if base == 0 or not np.isfinite(base):
                retention = np.full_like(cap, np.nan, dtype=float)
            else:
                retention = cap / base  # 0–1 小数，与 exp_loader 契约一致

            if label_mode == "stem":
                label = f.stem
            else:
                rel = f.relative_to(folder).as_posix()
                label = rel.rsplit(".", 1)[0]

            plotter_instance.add_exp_data(label, cycles, cap, retention)
            labels.append(label)
        except Exception as e:
            logger.warning("读取 %s 失败: %s", f, e)

    logger.info("dat 注入完成：%d 条曲线", len(labels))
    return labels


def export_cycle_data(sol, filename="cycle_analysis.xlsx", step=100):
    """导出每圈充/放电曲线到 Excel。

    参数
    ----
    step : int
        每隔多少圈采样导出，默认 100。
    """
    all_charge = []
    all_discharge = []
    for i in range(0, len(sol.cycles), step):
        cycle = sol.cycles[i]
        current = cycle["Current [A]"].entries
        if any(current < 0):
            charge_mask = current < 0
            charge_df = pd.DataFrame({
                "Cycle": [i] * sum(charge_mask),
                "Type": ["Charge"] * sum(charge_mask),
                "Capacity [Ah]": cycle["Throughput capacity [A.h]"].entries[charge_mask] - cycle["Throughput capacity [A.h]"].entries[charge_mask][0],
                "Voltage [V]": cycle["Voltage [V]"].entries[charge_mask],
            })
            all_charge.append(charge_df)
        if any(current > 0):
            discharge_mask = current > 0
            discharge_df = pd.DataFrame({
                "Cycle": [i] * sum(discharge_mask),
                "Type": ["Discharge"] * sum(discharge_mask),
                "Capacity [Ah]": cycle["Throughput capacity [A.h]"].entries[discharge_mask] - cycle["Throughput capacity [A.h]"].entries[discharge_mask][0],
                "Voltage [V]": cycle["Voltage [V]"].entries[discharge_mask],
            })
            all_discharge.append(discharge_df)
    with pd.ExcelWriter(filename) as writer:
        if all_charge:
            pd.concat(all_charge).to_excel(writer, sheet_name="Charge", index=False)
        if all_discharge:
            pd.concat(all_discharge).to_excel(writer, sheet_name="Discharge", index=False)
