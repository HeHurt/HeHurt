"""仿真与实验自动对标工具。

提供一站式函数：传入 sol_list + 实验 CSV 文件夹，
自动生成容量保持率、能效、膨胀力的 Sim-vs-Exp 对比图。

典型用法
--------
>>> from src.compare import compare_all
>>> compare_all(
...     sol_list, sim_labels,
...     exp_folder=r"D:\\587\\csv_output",
...     params=params,              # 膨胀力需要
...     acceleration_factor=50,
... )
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from .exp_loader import load_cycling_folder
from .analysis import get_discharge_capacity, compute_cycle_energies, calculate_cycle_swelling
from .plotting import _apply_default_style

logger = logging.getLogger(__name__)


# ── 辅助：按温度+倍率做模糊匹配 ──────────────────────────────────────────

def _normalize(s: str) -> str:
    return s.strip().lower().replace("℃", "°c").replace(" ", "")


def _match_condition_filter(label: str, filter_conditions=None) -> bool:
    """判断标签是否满足工况筛选条件。

    参数
    ----
    label : str
        待检查的标签（仿真或实验）。
    filter_conditions : str | list[str] | None
        筛选条件。含 °C/℃ 的项为温度关键词，其余为倍率关键词。
        同类 OR，异类 AND。None 表示全部通过。

    示例
    ----
    >>> _match_condition_filter("25°C 0.5P", "25°C")       # True
    >>> _match_condition_filter("45°C 0.5P", "25°C")       # False
    >>> _match_condition_filter("25°C 0.5P", ["25°C", "0.5P"])  # True (AND)
    >>> _match_condition_filter("25°C 0.5P", ["25°C", "45°C"])  # True (同类 OR)
    """
    if filter_conditions is None:
        return True

    if isinstance(filter_conditions, str):
        filter_conditions = [filter_conditions]

    label_norm = _normalize(label)

    # 拆分为温度关键词和倍率/其他关键词
    temp_tokens = []
    rate_tokens = []
    for token in filter_conditions:
        t = _normalize(token)
        if not t:
            continue
        if "°c" in t:
            temp_tokens.append(t)
        else:
            rate_tokens.append(t)

    # 同类 OR，异类 AND
    temp_ok = (not temp_tokens) or any(tok in label_norm for tok in temp_tokens)
    rate_ok = (not rate_tokens) or any(tok in label_norm for tok in rate_tokens)
    return temp_ok and rate_ok


def _auto_match(sim_labels: list[str], exp_data_list: list[dict],
                filter_conditions=None) -> list[tuple[int, int]]:
    """自动匹配仿真标签与实验数据。

    匹配策略：温度与倍率同时出现在二者标签中即视为匹配。

    参数
    ----
    filter_conditions : str | list[str] | None
        工况筛选条件，例如 "25°C"、"0.5P"、["25°C", "0.5P"]。
        含 °C/℃ 的项视为温度筛选，其余视为倍率筛选。
        同类条件之间为 OR 关系，不同类之间为 AND 关系。
        None 表示不筛选。

    返回 [(sim_idx, exp_idx), ...] 配对列表。
    """
    pairs = []
    used_exp = set()

    for si, sim_lbl in enumerate(sim_labels):
        # 先检查仿真标签是否满足筛选条件
        if not _match_condition_filter(sim_lbl, filter_conditions):
            continue

        sim_norm = _normalize(sim_lbl)
        best_exp = None
        best_score = 0

        for ei, exp_d in enumerate(exp_data_list):
            if ei in used_exp:
                continue

            # 实验标签也需要满足筛选条件
            if not _match_condition_filter(exp_d["label"], filter_conditions):
                continue

            exp_norm = _normalize(exp_d["label"])

            # 计算关键词匹配得分
            score = 0
            sim_temps = re.findall(r"-?\d+(?:\.\d+)?°c", sim_norm)
            exp_temps = re.findall(r"-?\d+(?:\.\d+)?°c", exp_norm)
            for st in sim_temps:
                if st in exp_norm:
                    score += 10
            for et in exp_temps:
                if et in sim_norm:
                    score += 10

            sim_rates = re.findall(r"\d+(?:\.\d+)?p", sim_norm)
            exp_rates = re.findall(r"\d+(?:\.\d+)?p", exp_norm)
            for sr in sim_rates:
                if sr in exp_norm:
                    score += 10
            for er in exp_rates:
                if er in sim_norm:
                    score += 10

            if score > best_score:
                best_score = score
                best_exp = ei

        if best_exp is not None and best_score > 0:
            pairs.append((si, best_exp))
            used_exp.add(best_exp)

    return pairs


# ── 单指标对标函数 ────────────────────────────────────────────────────────

def compare_retention(
    sol_list,
    sim_labels: list[str],
    exp_data_list: list[dict],
    acceleration_factor: int = 50,
    ax=None,
    figsize=(8, 5),
    filter_conditions=None,
    sim_bias: float = 0.0,
    exp_bias: float = 0.0,
):
    """对标容量保持率（Sim vs Exp）。

    参数
    ----
    filter_conditions : str | list[str] | None
        工况筛选，如 "25°C"、"0.5P"、["25°C", "0.5P"]。
    sim_bias : float
        仿真结果的手动修正偏移量（直接加到保持率上）。
    exp_bias : float
        实验结果的手动修正偏移量（直接加到保持率上）。
    """
    _apply_default_style()
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    pairs = _auto_match(sim_labels, exp_data_list, filter_conditions)
    color_pool = plt.cm.tab10(np.linspace(0, 1, 10))

    for idx, (si, ei) in enumerate(pairs):
        color = color_pool[idx % 10]
        sol = sol_list[si]
        exp = exp_data_list[ei]
        lbl = sim_labels[si]

        # 仿真
        caps = get_discharge_capacity(sol).get("discharge_capacity", np.array([]))
        valid_idx = np.flatnonzero(~np.isnan(caps))
        caps = caps[valid_idx]
        if caps.size > 0 and caps[0] != 0:
            sim_cycle = valid_idx * acceleration_factor
            sim_ret = caps / caps[0] + sim_bias
            bias_tag = f" (bias={sim_bias:+g})" if sim_bias != 0 else ""
            ax.plot(sim_cycle, sim_ret, ls="--", lw=2.5, color=color, label=f"{lbl} (Sim){bias_tag}")

        # 实验
        exp_cycle = exp.get("cycle", np.array([]))
        exp_ret = exp.get("retention", np.array([]))
        if exp_cycle.size > 0 and exp_ret.size > 0:
            exp_bias_tag = f" (bias={exp_bias:+g})" if exp_bias != 0 else ""
            ax.plot(exp_cycle, exp_ret + exp_bias, ls="-", lw=2, color=color, alpha=0.7, label=f"{exp['label']} (Exp){exp_bias_tag}")

    ax.set_xlabel("Cycle Number")
    ax.set_ylabel("Capacity Retention")
    ax.set_title("容量保持率对标")
    ax.grid(True, ls="--", alpha=0.4)
    ax.legend(fontsize=9)
    return ax


def compare_efficiency(
    sol_list,
    sim_labels: list[str],
    exp_data_list: list[dict],
    acceleration_factor: int = 50,
    ax=None,
    figsize=(8, 5),
    filter_conditions=None,
    sim_bias: float = 0.0,
    exp_bias: float = 0.0,
):
    """对标能量效率（Sim vs Exp）。

    参数
    ----
    filter_conditions : str | list[str] | None
        工况筛选，如 "25°C"、"0.5P"、["25°C", "0.5P"]。
    sim_bias : float
        仿真结果的手动修正偏移量（直接加到能效上）。
    exp_bias : float
        实验结果的手动修正偏移量（直接加到能效上）。
    """
    _apply_default_style()
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)

    pairs = _auto_match(sim_labels, exp_data_list, filter_conditions)
    color_pool = plt.cm.tab10(np.linspace(0, 1, 10))

    for idx, (si, ei) in enumerate(pairs):
        color = color_pool[idx % 10]
        sol = sol_list[si]
        exp = exp_data_list[ei]
        lbl = sim_labels[si]

        # 仿真
        res = compute_cycle_energies(sol)
        eff = res.get("efficiency", np.array([]))
        if len(eff) > 0:
            sim_cycle = res.get("cycle_index", np.arange(len(eff))) * acceleration_factor
            eff_biased = np.array(eff) + sim_bias
            bias_tag = f" (bias={sim_bias:+g})" if sim_bias != 0 else ""
            ax.plot(sim_cycle, eff_biased, ls="--", lw=2.5, color=color, label=f"{lbl} (Sim){bias_tag}")

        # 实验
        exp_cycle = exp.get("cycle", np.array([]))
        exp_eff = exp.get("efficiency", np.array([]))
        if exp_cycle.size > 0 and exp_eff.size > 0:
            exp_bias_tag = f" (bias={exp_bias:+g})" if exp_bias != 0 else ""
            ax.plot(exp_cycle, np.array(exp_eff) + exp_bias, ls="-", lw=2, color=color, alpha=0.7, label=f"{exp['label']} (Exp){exp_bias_tag}")

    ax.set_xlabel("Cycle Number")
    ax.set_ylabel("Energy Efficiency")
    ax.set_title("能量效率对标")
    ax.grid(True, ls="--", alpha=0.4)
    ax.legend(fontsize=9)
    return ax


def compare_swelling(
    sol_list,
    sim_labels: list[str],
    exp_data_list: list[dict],
    params,
    acceleration_factor: int = 50,
    ax_max=None,
    ax_min=None,
    figsize=(14, 5),
    omega_n=0.1 * 3.1e-6,
    omega_p=0,
    k_stiffness=1.0e9,
    preload_force=300.0,
    method="engineering",
    reference="parameter_initial",
    filter_conditions=None,
    sim_bias: float = 0.0,
    exp_bias: float = 0.0,
    **swelling_kwargs,
):
    """对标膨胀力（最大/最小，Sim vs Exp）。

    参数
    ----
    filter_conditions : str | list[str] | None
        工况筛选，如 "25°C"、"0.5P"、["25°C", "0.5P"]。
    method : {"engineering", "pybamm_thickness"}
        膨胀位移来源；pybamm_thickness 会优先读取 Cell thickness change [m]。
    reference : {"cycle_start", "solution_start", "parameter_initial"}
        膨胀位移零点定义。
    sim_bias : float
        仿真结果的手动修正偏移量（直接加到膨胀力上，单位 N）。
    exp_bias : float
        实验结果的手动修正偏移量（直接加到膨胀力上，单位 N）。
    """
    _apply_default_style()
    if ax_max is None or ax_min is None:
        fig, (ax_max, ax_min) = plt.subplots(1, 2, figsize=figsize)

    pairs = _auto_match(sim_labels, exp_data_list, filter_conditions)
    color_pool = plt.cm.tab10(np.linspace(0, 1, 10))

    for idx, (si, ei) in enumerate(pairs):
        color = color_pool[idx % 10]
        sol = sol_list[si]
        exp = exp_data_list[ei]
        lbl = sim_labels[si]

        # 仿真
        max_f, min_f = calculate_cycle_swelling(
            sol, params,
            omega_n=omega_n, omega_p=omega_p,
            k_stiffness=k_stiffness, preload_force=preload_force,
            method=method, reference=reference,
            **swelling_kwargs,
        )
        if len(max_f) > 0:
            sim_cycle = np.arange(1, len(max_f) + 1) * acceleration_factor
            bias_tag = f" (bias={sim_bias:+g})" if sim_bias != 0 else ""
            ax_max.plot(sim_cycle, max_f + sim_bias, ls="--", lw=2.5, color=color, label=f"{lbl} (Sim){bias_tag}")
            ax_min.plot(sim_cycle, min_f + sim_bias, ls="--", lw=2.5, color=color, label=f"{lbl} (Sim){bias_tag}")

        # 实验
        exp_cycle = exp.get("cycle", np.array([]))
        exp_max = exp.get("max_force", np.array([]))
        exp_min = exp.get("min_force", np.array([]))
        exp_bias_tag = f" (bias={exp_bias:+g})" if exp_bias != 0 else ""
        if exp_cycle.size > 0 and exp_max.size > 0:
            ax_max.plot(exp_cycle, exp_max + exp_bias, ls="-", lw=2, color=color, alpha=0.7, label=f"{exp['label']} (Exp){exp_bias_tag}")
        if exp_cycle.size > 0 and exp_min.size > 0:
            ax_min.plot(exp_cycle, exp_min + exp_bias, ls="-", lw=2, color=color, alpha=0.7, label=f"{exp['label']} (Exp){exp_bias_tag}")

    ax_max.set_xlabel("Cycle Number")
    ax_max.set_ylabel("Force (N)")
    ax_max.set_title("最大膨胀力对标")
    ax_max.grid(True, ls="--", alpha=0.4)
    ax_max.legend(fontsize=9)

    ax_min.set_xlabel("Cycle Number")
    ax_min.set_ylabel("Force (N)")
    ax_min.set_title("最小膨胀力对标")
    ax_min.grid(True, ls="--", alpha=0.4)
    ax_min.legend(fontsize=9)
    return ax_max, ax_min


# ── 一站式对标 ────────────────────────────────────────────────────────────

def compare_all(
    sol_list,
    sim_labels: list[str],
    exp_folder: str | Path | None = None,
    exp_data_list: list[dict] | None = None,
    params=None,
    acceleration_factor: int = 50,
    channel: int = 0,
    metrics: list[str] | None = None,
    figsize_single=(8, 5),
    omega_n=0.1 * 3.1e-6,
    omega_p=0,
    k_stiffness=1.0e9,
    preload_force=0.0,
    method="engineering",
    reference="parameter_initial",
    filter_conditions=None,
    sim_bias: dict | float = 0.0,
    exp_bias: dict | float = 0.0,
    **swelling_kwargs,
):
    """一站式自动对标。

    参数
    ----
    sol_list : list
        PyBaMM 仿真结果列表。
    sim_labels : list[str]
        仿真标签列表，例如 ['25°C 0.25P', '25°C 0.5P']。
    exp_folder : str or Path or None
        实验 CSV 文件夹路径。与 exp_data_list 二选一。
    exp_data_list : list[dict] or None
        已加载的实验数据列表（来自 load_cycling_folder）。
    params : pybamm.ParameterValues or None
        仿真参数（膨胀力对标需要）。无则跳过膨胀力。
    acceleration_factor : int
        仿真加速因子。
    channel : int
        实验 CSV 通道索引。
    metrics : list[str] or None
        要对标的指标，默认 ['retention', 'efficiency', 'swelling']。
    method : {"engineering", "pybamm_thickness"}
        膨胀位移来源；pybamm_thickness 会优先读取 Cell thickness change [m]。
    reference : {"cycle_start", "solution_start", "parameter_initial"}
        膨胀位移零点定义。
    filter_conditions : str | list[str] | None
        工况筛选，如 "25°C"、"0.5P"、["25°C", "0.5P"]。
    sim_bias : dict | float
        仿真结果的手动修正偏移量。
        - 若为 float，则对所有指标统一偏移。
        - 若为 dict，按指标分别指定，如 {"retention": 0.02, "efficiency": -0.01, "swelling": 100}。
    exp_bias : dict | float
        实验结果的手动修正偏移量，格式同 sim_bias。

    返回
    ----
    dict[str, matplotlib.axes.Axes]
        各指标对应的 Axes 对象。
    """
    _apply_default_style()

    if metrics is None:
        metrics = ["retention", "efficiency", "swelling"]

    # 解析 sim_bias
    if isinstance(sim_bias, (int, float)):
        bias_map = {m: float(sim_bias) for m in metrics}
    else:
        bias_map = {m: float(sim_bias.get(m, 0.0)) for m in metrics}

    # 解析 exp_bias
    if isinstance(exp_bias, (int, float)):
        exp_bias_map = {m: float(exp_bias) for m in metrics}
    else:
        exp_bias_map = {m: float(exp_bias.get(m, 0.0)) for m in metrics}

    # 加载实验数据
    if exp_data_list is None:
        if exp_folder is None:
            raise ValueError("必须提供 exp_folder 或 exp_data_list")
        exp_data_list = load_cycling_folder(exp_folder, channel=channel)

    if not exp_data_list:
        logger.warning("未加载到任何实验数据，跳过对标。")
        return {}

    # 自动匹配并显示匹配结果
    pairs = _auto_match(sim_labels, exp_data_list, filter_conditions)
    logger.info("自动匹配结果 (%d 对):", len(pairs))
    for si, ei in pairs:
        logger.info("  Sim[%s]  ↔  Exp[%s]", sim_labels[si], exp_data_list[ei]["label"])
    unmatched_sim = [i for i in range(len(sim_labels)) if i not in {p[0] for p in pairs}]
    unmatched_exp = [i for i in range(len(exp_data_list)) if i not in {p[1] for p in pairs}]
    if unmatched_sim:
        logger.warning("未匹配仿真: %s", [sim_labels[i] for i in unmatched_sim])
    if unmatched_exp:
        logger.warning("未匹配实验: %s", [exp_data_list[i]["label"] for i in unmatched_exp])
    if filter_conditions is not None:
        logger.info("筛选条件: %s", filter_conditions)

    axes = {}

    if "retention" in metrics:
        fig_r, ax_r = plt.subplots(1, 1, figsize=figsize_single)
        compare_retention(sol_list, sim_labels, exp_data_list, acceleration_factor, ax=ax_r,
                          filter_conditions=filter_conditions, sim_bias=bias_map.get("retention", 0.0),
                          exp_bias=exp_bias_map.get("retention", 0.0))
        plt.tight_layout()
        axes["retention"] = ax_r

    if "efficiency" in metrics:
        fig_e, ax_e = plt.subplots(1, 1, figsize=figsize_single)
        compare_efficiency(sol_list, sim_labels, exp_data_list, acceleration_factor, ax=ax_e,
                           filter_conditions=filter_conditions, sim_bias=bias_map.get("efficiency", 0.0),
                           exp_bias=exp_bias_map.get("efficiency", 0.0))
        plt.tight_layout()
        axes["efficiency"] = ax_e

    if "swelling" in metrics:
        if params is None:
            logger.warning("未提供 params，跳过膨胀力对标。")
        else:
            fig_s, (ax_mx, ax_mn) = plt.subplots(1, 2, figsize=(14, 5))
            compare_swelling(
                sol_list, sim_labels, exp_data_list, params,
                acceleration_factor,
                ax_max=ax_mx, ax_min=ax_mn,
                omega_n=omega_n, omega_p=omega_p,
                k_stiffness=k_stiffness, preload_force=preload_force,
                method=method, reference=reference,
                filter_conditions=filter_conditions, sim_bias=bias_map.get("swelling", 0.0),
                exp_bias=exp_bias_map.get("swelling", 0.0),
                **swelling_kwargs,
            )
            plt.tight_layout()
            axes["swelling_max"] = ax_mx
            axes["swelling_min"] = ax_mn

    return axes
