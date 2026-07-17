"""实验循环数据加载器。

自动识别测试设备导出 CSV 的列格式（中/英文），从文件名解析温度与倍率，
返回统一 dict 供对标函数直接消费。

典型用法
--------
>>> from src.exp_loader import load_cycling_folder
>>> exp_list = load_cycling_folder(r"D:\\587\\csv_output")
>>> # exp_list = [{"label": "25°C 0.5P", "cycle": [...], ...}, ...]
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def normalize_retention_scale(arr):
    """保持率统一到 0–1 小数：均值 > 2 视为百分制并除以 100。"""
    arr = np.asarray(arr, dtype=float)
    if arr.size > 0 and np.nanmean(arr) > 2.0:
        return arr / 100.0
    return arr


# ── 列名别名映射：标准键 → CSV 中可能出现的列名（按优先级排列） ──────────
COLUMN_ALIASES: dict[str, list[str]] = {
    "cycle": ["循环圈数", "Cycle Index", "Cycle", "cycle", "Cyc#", "圈数"],
    "discharge_capacity": ["放电容量(Ah)", "放电容量", "Discharge Capacity(Ah)", "Discharge Capacity", "DChg_C(Ah)"],
    "charge_capacity": ["充电容量(Ah)", "充电容量", "Charge Capacity(Ah)", "Charge Capacity", "Chg_C(Ah)"],
    "retention": ["容量保持率", "Capacity Retention", "Retention"],
    "efficiency": ["能量效率", "Energy Efficiency", "Efficiency", "能效"],
    "max_force": ["最大膨胀力", "Max Force", "Max Swelling Force"],
    "min_force": ["最小膨胀力", "Min Force", "Min Swelling Force"],
    "discharge_energy": ["放电能量(Wh)", "放电能量", "Discharge Energy(Wh)"],
    "charge_energy": ["充电能量(Wh)", "充电能量", "Charge Energy(Wh)"],
    "temperature": [
        "放电最大温度T1(℃)", "放电最大温度T1",
        "Temperature", "Temp(℃)", "T1(℃)",
    ],
}


def _find_column(df_columns: list[str], aliases: list[str], suffix: str = "") -> str | None:
    """在 DataFrame 列名中查找第一个匹配的别名。

    suffix 用于处理多通道数据：pandas 自动附加 '.1', '.2' 等后缀。
    """
    for alias in aliases:
        target = f"{alias}{suffix}" if suffix else alias
        for col in df_columns:
            if col.strip() == target.strip():
                return col
    return None


def _channel_suffix(channel: int) -> str:
    """返回 pandas 自动重命名的通道后缀（0→'', 1→'.1', 2→'.2'）。"""
    return "" if channel == 0 else f".{channel}"


def parse_condition_from_filename(filename: str) -> dict:
    """从文件名提取温度和倍率信息。

    支持格式示例：
    - '25℃-0.5P.csv'  → {'temperature': '25°C', 'rate': '0.5P', 'label': '25°C 0.5P'}
    - '45°C_1P.csv'    → {'temperature': '45°C', 'rate': '1P',   'label': '45°C 1P'}
    - '0.25P_25C.csv'  → {'temperature': '25°C', 'rate': '0.25P','label': '25°C 0.25P'}
    """
    stem = Path(filename).stem
    result: dict[str, str] = {}

    # 温度：匹配 -10℃, 25°C, 45C 等
    temp_match = re.search(r"(-?\d+(?:\.\d+)?)\s*[°℃]?\s*[cC℃]", stem)
    if temp_match:
        result["temperature"] = f"{temp_match.group(1)}°C"

    # 倍率：匹配 0.5P, 1P, 0.25C 等
    rate_match = re.search(r"(\d+(?:\.\d+)?)\s*[PpCc](?!\w)", stem)
    if rate_match:
        result["rate"] = f"{rate_match.group(1)}P"

    parts = []
    if "temperature" in result:
        parts.append(result["temperature"])
    if "rate" in result:
        parts.append(result["rate"])
    result["label"] = " ".join(parts) if parts else stem

    return result


def load_cycling_csv(
    file_path: str | Path,
    channel: int = 0,
    label: str | None = None,
    encoding: str = "utf-8-sig",
) -> dict:
    """从测试设备导出的循环 CSV 加载数据，返回统一格式 dict。

    参数
    ----
    file_path : str or Path
        CSV 文件路径。
    channel : int
        通道索引。0 = 第一组列（无后缀），1 = 第二组列（'.1' 后缀）。
    label : str or None
        曲线标签。None 时从文件名自动解析。
    encoding : str
        文件编码，默认 utf-8-sig（兼容 BOM）。

    返回
    ----
    dict
        包含以下键（值均为 np.ndarray，不存在的列返回空数组）：
        - label : str
        - cycle, discharge_capacity, charge_capacity
        - retention, efficiency
        - max_force, min_force
        - discharge_energy, charge_energy, temperature
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"未找到文件: {path}")

    df = pd.read_csv(path, encoding=encoding)
    suffix = _channel_suffix(channel)
    cols = df.columns.tolist()

    data: dict[str, object] = {}

    # 解析标签
    if label is None:
        parsed = parse_condition_from_filename(path.name)
        data["label"] = parsed["label"]
    else:
        data["label"] = label

    # 提取各列
    for std_key, aliases in COLUMN_ALIASES.items():
        # cycle 列不分通道
        col_suffix = "" if std_key == "cycle" else suffix
        found_col = _find_column(cols, aliases, col_suffix)

        if found_col is not None:
            arr = pd.to_numeric(df[found_col], errors="coerce").to_numpy(dtype=float)
        else:
            arr = np.array([])
        data[std_key] = arr

    # 容量保持率特殊处理：CSV 里可能有多个 '容量保持率' 列
    # pandas 会自动命名为 '容量保持率', '容量保持率.1', '容量保持率.2', ...
    # channel=0 时优先用 '容量保持率.1'（通常是归一化保持率），若不存在则用 '容量保持率'
    if data["retention"].size == 0 or np.all(np.isnan(data["retention"])):
        # 尝试带后缀的变体
        for alt_suffix in [".1", ".2", ".3", ""]:
            col = _find_column(cols, COLUMN_ALIASES["retention"], alt_suffix)
            if col is not None:
                arr = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
                if np.any(np.isfinite(arr)):
                    data["retention"] = arr
                    break

    # 归一化保持率：若 mean > 2 则认为是百分制，否则是小数制 → 统一到小数
    data["retention"] = normalize_retention_scale(data["retention"])

    # 去除 NaN 行（以 cycle 列为准）
    cycle_arr = data["cycle"]
    if cycle_arr.size > 0:
        valid_mask = np.isfinite(cycle_arr)
        for key in COLUMN_ALIASES:
            arr = data[key]
            if isinstance(arr, np.ndarray) and arr.size == cycle_arr.size:
                data[key] = arr[valid_mask]

    return data


def load_cycling_folder(
    folder_path: str | Path,
    pattern: str = "*.csv",
    channel: int = 0,
    encoding: str = "utf-8-sig",
    sort_by: str = "label",
) -> list[dict]:
    """批量加载文件夹下所有循环 CSV，返回 list[dict]。

    参数
    ----
    folder_path : 文件夹路径。
    pattern : glob 模式，默认 '*.csv'。
    channel : 通道索引。
    encoding : 文件编码。
    sort_by : 排序键，'label' 或 'filename'。

    返回
    ----
    list[dict]  每项结构同 load_cycling_csv 返回值。
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"未找到文件夹: {folder}")

    files = sorted(folder.glob(pattern))
    if not files:
        logger.warning("未找到匹配 %r 的文件: %s", pattern, folder)
        return []

    results = []
    for f in files:
        try:
            data = load_cycling_csv(f, channel=channel, encoding=encoding)
            results.append(data)
            logger.info("%s -> %s (%d 行)", f.name, data["label"], data["cycle"].size)
        except Exception as e:
            logger.warning("%s 加载失败: %s", f.name, e)

    if sort_by == "label":
        results.sort(key=lambda d: d["label"])

    logger.info("共加载 %d 个实验条件", len(results))
    return results


def load_cycling_csv_from_peak(
    file_path: str | Path,
    channel: int = 0,
    label: str | None = None,
    encoding: str = "utf-8-sig",
    reset_cycle: bool = True,
) -> dict:
    """加载循环数据，以放电容量峰值为 BOL，删除前期爬坡圈。

    在 ``load_cycling_csv`` 基础上做寿命起点对齐，便于和仿真曲线叠加对标：

    - 以放电容量首次达到最大值的位置作为寿命起点（BOL），删除之前的爬坡圈；
    - 容量保持率以峰值容量重新归一（BOL 处 = 1.0），覆盖设备自带的保持率列；
    - ``reset_cycle=True`` 时把 BOL 重置为 cycle 0。

    参数
    ----
    file_path, channel, label, encoding : 同 ``load_cycling_csv``。
    reset_cycle : bool
        是否把 BOL 圈号平移到 0。

    返回
    ----
    dict
        字段同 ``load_cycling_csv``，额外附加 ``q_bol``（峰值放电容量 [Ah]）。
    """
    data = load_cycling_csv(file_path, channel=channel, label=label, encoding=encoding)
    q = data["discharge_capacity"]
    if q.size == 0:
        raise ValueError(f"放电容量为空，无法确定 BOL: {file_path}")

    peak_idx = int(np.argmax(q))
    q_bol = float(q[peak_idx])

    # 所有与 cycle 等长的数组同步截断
    for key in COLUMN_ALIASES:
        arr = data.get(key)
        if isinstance(arr, np.ndarray) and arr.size == q.size:
            data[key] = arr[peak_idx:]

    if reset_cycle and data["cycle"].size > 0:
        data["cycle"] = data["cycle"] - data["cycle"][0]

    data["retention"] = data["discharge_capacity"] / q_bol
    data["q_bol"] = q_bol
    return data
