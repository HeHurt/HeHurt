"""Reporting helpers for canonical lifecycle heat workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd

from .analysis import get_all_heat_components, get_discharge_capacity
from .heat_calibration import compute_cycle_calibrated_heat
from .simulation_rpt import snapshot_degradation_variables
from .workflow_runtime import write_json


HEAT_COLUMNS = [
    "ohmic_charge_w",
    "reaction_charge_w",
    "mixing_charge_w",
    "hysteresis_charge_w",
    "contact_charge_w",
    "reversible_reference_charge_w",
    "internal_irreversible_charge_w",
    "calibrated_total_charge_w",
    "ohmic_discharge_w",
    "reaction_discharge_w",
    "mixing_discharge_w",
    "hysteresis_discharge_w",
    "contact_discharge_w",
    "reversible_reference_discharge_w",
    "internal_irreversible_discharge_w",
    "calibrated_total_discharge_w",
]

HEAT_COLUMN_CN = {
    "target_soh_pct": "目标SOH(%)",
    "actual_soh_pct": "实际或外推SOH(%)",
    "real_cycle": "等效循环圈数",
    "diagnostic_p_rate": "诊断倍率(P)",
    "temperature_c": "温度(°C)",
    "aging_p_rate": "老化倍率(P)",
    "contact_resistance_mohm": "接触电阻(mΩ)",
    "data_source": "数据来源",
    "ohmic_charge_w": "充电欧姆热功率(W)",
    "reaction_charge_w": "充电反应热功率(W)",
    "mixing_charge_w": "充电混合热功率(W)",
    "hysteresis_charge_w": "充电滞后热功率(W)",
    "contact_charge_w": "充电接触热功率(W)",
    "reversible_reference_charge_w": "充电可逆热功率(W)",
    "internal_irreversible_charge_w": "充电不可逆热功率(W)",
    "calibrated_total_charge_w": "充电平均总产热功率(W)",
    "ohmic_discharge_w": "放电欧姆热功率(W)",
    "reaction_discharge_w": "放电反应热功率(W)",
    "mixing_discharge_w": "放电混合热功率(W)",
    "hysteresis_discharge_w": "放电滞后热功率(W)",
    "contact_discharge_w": "放电接触热功率(W)",
    "reversible_reference_discharge_w": "放电可逆热功率(W)",
    "internal_irreversible_discharge_w": "放电不可逆热功率(W)",
    "calibrated_total_discharge_w": "放电平均总产热功率(W)",
}

MECHANISM_RENAME_CN = {
    "target_soh_pct": "目标SOH(%)",
    "actual_soh_pct": "实际SOH(%)",
    "real_cycle": "等效循环圈数",
    "temperature_c": "温度(°C)",
    "aging_p_rate": "老化倍率(P)",
    "contact_resistance_mohm": "接触电阻(mΩ)",
    "q_sei_ah": "SEI损失(Ah)",
    "q_sei_on_cracks_ah": "裂纹SEI损失(Ah)",
    "q_plating_ah": "析锂损失(Ah)",
    "lam_neg_ah": "负极活性材料损失(Ah)",
    "lli_ah": "锂库存损失(Ah)",
    "negative_porosity_avg": "负极平均孔隙率",
    "diagnostic_status": "诊断状态",
    "diagnostic_error": "诊断错误",
}


def apply_heat_correction(values: Sequence[float], correction: Mapping[str, Any] | None) -> np.ndarray:
    """Apply a linear engineering correction to heat values."""
    array = np.asarray(values, dtype=float)
    if not correction or not correction.get("enabled", False):
        return array.copy()
    return array * float(correction.get("scale", 1.0)) + float(correction.get("offset_w", 0.0))


def build_diagnostic_heat_table(
    bundle: Mapping[str, Any],
    entropy_curves: Mapping[str, tuple[np.ndarray, np.ndarray]],
    *,
    contact_resistance_ohm: float,
    temperature_c: float,
    aging_p_rate: float,
    contact_resistance_mohm: float,
) -> pd.DataFrame:
    """Build one long heat table from SOH-triggered diagnostic branches."""
    rows: list[dict[str, Any]] = []
    for item in bundle.get("diagnostic_solutions", []):
        solution = item.get("solution")
        cycles = list(getattr(solution, "cycles", []))
        if not cycles:
            continue
        row = {
            "target_soh_pct": item["target_soh_pct"],
            "actual_soh_pct": item["actual_soh_pct"],
            "real_cycle": item["real_cycle"],
            "diagnostic_p_rate": item["diagnostic_p_rate"],
            "temperature_c": temperature_c,
            "aging_p_rate": aging_p_rate,
            "contact_resistance_mohm": contact_resistance_mohm,
            "data_source": "仿真实际点",
        }
        row.update(
            compute_cycle_calibrated_heat(
                cycles[-1],
                entropy_curves,
                contact_resistance_ohm=contact_resistance_ohm,
            )
        )
        rows.append(row)
    columns = [
        "target_soh_pct",
        "actual_soh_pct",
        "real_cycle",
        "diagnostic_p_rate",
        "temperature_c",
        "aging_p_rate",
        "contact_resistance_mohm",
        "data_source",
        *HEAT_COLUMNS,
    ]
    return pd.DataFrame(rows).reindex(columns=columns)


def append_unconstrained_trend_extrapolation(
    actual_df: pd.DataFrame,
    targets_pct: Sequence[float],
    diagnostic_p_rates: Sequence[float],
    *,
    group_columns: Sequence[str] = ("temperature_c", "aging_p_rate", "contact_resistance_mohm"),
) -> pd.DataFrame:
    """Append unbounded linear/quadratic trend rows for missing lower-SOH targets."""
    if actual_df.empty:
        return actual_df.copy()
    frames = [actual_df.copy()]
    for group_values, group_df in actual_df.groupby(list(group_columns), dropna=False):
        group_key = group_values if isinstance(group_values, tuple) else (group_values,)
        group_meta = dict(zip(group_columns, group_key))
        for p_rate in diagnostic_p_rates:
            rate_df = group_df.loc[group_df["diagnostic_p_rate"].eq(float(p_rate))].copy()
            rate_df = rate_df.sort_values("actual_soh_pct")
            if len(rate_df) < 2:
                continue
            existing_targets = set(rate_df["target_soh_pct"].round(8))
            last_actual_soh = float(rate_df["actual_soh_pct"].min())
            missing_targets = [
                float(target)
                for target in targets_pct
                if float(target) < last_actual_soh and round(float(target), 8) not in existing_targets
            ]
            fit_df = rate_df.head(min(5, len(rate_df))).copy()
            new_rows = []
            for target in missing_targets:
                row: dict[str, Any] = {
                    **group_meta,
                    "target_soh_pct": target,
                    "actual_soh_pct": target,
                    "diagnostic_p_rate": float(p_rate),
                    "data_source": "趋势外推",
                }
                for column in ["real_cycle", *HEAT_COLUMNS]:
                    if column not in fit_df:
                        row[column] = np.nan
                        continue
                    valid = fit_df[["actual_soh_pct", column]].dropna()
                    if len(valid) < 2:
                        row[column] = np.nan
                        continue
                    degree = min(2, len(valid) - 1)
                    coefficients = np.polyfit(valid["actual_soh_pct"], valid[column], degree)
                    row[column] = float(np.polyval(coefficients, target))
                new_rows.append(row)
            if new_rows:
                frames.append(pd.DataFrame(new_rows))
    return pd.concat(frames, ignore_index=True).sort_values(
        [*group_columns, "target_soh_pct", "diagnostic_p_rate"],
        ascending=[True] * len(group_columns) + [False, True],
    ).reset_index(drop=True)


def make_wide_summary(detail_df: pd.DataFrame, targets_pct: Sequence[float], diagnostic_p_rates: Sequence[float]) -> pd.DataFrame:
    """Create a Chinese-friendly SOH by diagnostic-rate heat summary."""
    rows: list[dict[str, Any]] = []
    if detail_df.empty:
        return pd.DataFrame()
    group_columns = ["temperature_c", "aging_p_rate", "contact_resistance_mohm"]
    for group_values, group_df in detail_df.groupby(group_columns, dropna=False):
        group_meta = dict(zip(group_columns, group_values))
        for target in targets_pct:
            target_df = group_df.loc[group_df["target_soh_pct"].eq(float(target))]
            if target_df.empty:
                continue
            first = target_df.iloc[0]
            row = {
                **group_meta,
                "目标SOH(%)": target,
                "实际或外推SOH(%)": first["actual_soh_pct"],
                "等效循环圈数": first["real_cycle"],
                "数据来源": "、".join(sorted(target_df["data_source"].dropna().unique())),
            }
            for p_rate in diagnostic_p_rates:
                rate_row = target_df.loc[target_df["diagnostic_p_rate"].eq(float(p_rate))]
                if rate_row.empty:
                    row[f"{p_rate:g}P充电平均产热功率(W)"] = np.nan
                    row[f"{p_rate:g}P放电平均产热功率(W)"] = np.nan
                    continue
                selected = rate_row.iloc[0]
                row[f"{p_rate:g}P充电平均产热功率(W)"] = selected["calibrated_total_charge_w"]
                row[f"{p_rate:g}P放电平均产热功率(W)"] = selected["calibrated_total_discharge_w"]
            rows.append(row)
    return pd.DataFrame(rows)


def build_mechanism_tables(bundle: Mapping[str, Any], *, case_meta: Mapping[str, Any] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return absolute and independent-share degradation mechanism tables."""
    diagnostic_df = bundle.get("diagnostic_df", pd.DataFrame()).copy()
    if diagnostic_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    if case_meta:
        for key, value in case_meta.items():
            diagnostic_df[key] = value
    columns = [
        "target_soh_pct",
        "actual_soh_pct",
        "real_cycle",
        "temperature_c",
        "aging_p_rate",
        "contact_resistance_mohm",
        "q_sei_ah",
        "q_sei_on_cracks_ah",
        "q_plating_ah",
        "lam_neg_ah",
        "lli_ah",
        "negative_porosity_avg",
        "diagnostic_status",
        "diagnostic_error",
    ]
    columns = [column for column in columns if column in diagnostic_df]
    mechanism = diagnostic_df[columns].drop_duplicates(
        ["temperature_c", "aging_p_rate", "contact_resistance_mohm", "target_soh_pct"],
        keep="first",
    )
    mechanism = mechanism.sort_values(
        ["temperature_c", "aging_p_rate", "contact_resistance_mohm", "target_soh_pct"],
        ascending=[True, True, True, False],
    ).reset_index(drop=True)
    mechanism = mechanism.rename(columns=MECHANISM_RENAME_CN)
    if "诊断状态" in mechanism:
        mechanism["诊断状态"] = mechanism["诊断状态"].replace({"simulated": "仿真成功", "failed": "诊断失败"})
    share_sources = {
        "SEI损失(Ah)": "SEI占比(%)",
        "裂纹SEI损失(Ah)": "裂纹SEI占比(%)",
        "析锂损失(Ah)": "析锂占比(%)",
        "负极活性材料损失(Ah)": "负极LAM占比(%)",
    }
    meta_columns = [column for column in ["目标SOH(%)", "实际SOH(%)", "等效循环圈数", "温度(°C)", "老化倍率(P)", "接触电阻(mΩ)"] if column in mechanism]
    mechanism_share = mechanism[meta_columns].copy()
    available = [column for column in share_sources if column in mechanism and mechanism[column].notna().any()]
    if available:
        nonnegative = mechanism[available].clip(lower=0)
        independent_total = nonnegative.sum(axis=1)
        for source_column in available:
            mechanism_share[share_sources[source_column]] = np.where(
                independent_total > 0,
                nonnegative[source_column] / independent_total * 100.0,
                np.nan,
            )
    return mechanism, mechanism_share


def build_cycle_heat_table(
    bundle: Mapping[str, Any],
    entropy_curves: Mapping[str, tuple[np.ndarray, np.ndarray]],
    *,
    contact_resistance_ohm: float,
    temperature_k: float,
    temperature_c: float,
    p_rate: float,
    power_w: float,
    aging_t_factor: float,
    cycles_per_block: int,
    label: str,
    heat_correction: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Build a per-cycle heat table from stored lifecycle block solutions."""
    heat_rows: list[dict[str, Any]] = []
    for block_index, (block_end_cycle, sol) in enumerate(
        zip(bundle.get("solution_real_cycles", []), bundle.get("solutions", []))
    ):
        cycles = list(getattr(sol, "cycles", []))
        if not cycles:
            continue
        active_count = 1 if block_index == 0 else min(int(cycles_per_block), len(cycles))
        active_cycles = cycles[-active_count:]
        if block_index == 0:
            real_cycles = np.array([1.0])
        else:
            real_cycles = float(block_end_cycle) - np.arange(active_count - 1, -1, -1) * float(aging_t_factor)
        for real_cycle, cycle in zip(real_cycles, active_cycles):
            cycle_sol = SimpleNamespace(cycles=[cycle])
            native_heat = get_all_heat_components(cycle_sol, label_for_temp=label)
            capacity = get_discharge_capacity(cycle_sol)["discharge_capacity"]
            row = {
                "real_cycle": int(round(float(real_cycle))),
                "discharge_capacity_ah": float(capacity[0]) if len(capacity) else np.nan,
                "temperature_k": temperature_k,
                "temperature_c": temperature_c,
                "p_rate": p_rate,
                "power_w": power_w,
            }
            for key, values in native_heat.items():
                values = np.asarray(values, dtype=float)
                row[f"{key}_w"] = float(values[0]) if values.size else np.nan
            row.update(
                compute_cycle_calibrated_heat(
                    cycle,
                    entropy_curves,
                    contact_resistance_ohm=contact_resistance_ohm,
                )
            )
            row.update(snapshot_degradation_variables(cycle))
            heat_rows.append(row)
    heat_df = pd.DataFrame(heat_rows)
    if heat_df.empty:
        return heat_df
    heat_df = heat_df.sort_values("real_cycle").drop_duplicates("real_cycle").reset_index(drop=True)
    if np.isfinite(heat_df["discharge_capacity_ah"].iloc[0]):
        heat_df["capacity_retention_pct"] = heat_df["discharge_capacity_ah"] / heat_df["discharge_capacity_ah"].iloc[0] * 100.0
    heat_df["total_heat_charge_raw_w"] = heat_df.get("total_chg_w", np.nan)
    heat_df["total_heat_discharge_raw_w"] = heat_df.get("total_dchg_w", np.nan)
    heat_df["total_heat_charge_corrected_w"] = apply_heat_correction(heat_df["total_heat_charge_raw_w"], heat_correction)
    heat_df["total_heat_discharge_corrected_w"] = apply_heat_correction(heat_df["total_heat_discharge_raw_w"], heat_correction)
    return heat_df


def export_lifecycle_heat_excel(
    workbook_path: Path,
    *,
    summary: pd.DataFrame,
    detail: pd.DataFrame,
    mechanism: pd.DataFrame,
    mechanism_share: pd.DataFrame,
    config_table: pd.DataFrame,
    cycle_heat: pd.DataFrame | None = None,
) -> Path:
    """Export a Chinese Excel workbook for lifecycle heat results."""
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="产热汇总", index=False)
        detail.rename(columns=HEAT_COLUMN_CN).to_excel(writer, sheet_name="产热分项", index=False)
        mechanism.to_excel(writer, sheet_name="老化机制", index=False)
        mechanism_share.to_excel(writer, sheet_name="老化机制占比", index=False)
        if cycle_heat is not None and not cycle_heat.empty:
            cycle_heat.to_excel(writer, sheet_name="循环产热", index=False)
        config_table.to_excel(writer, sheet_name="仿真配置", index=False)
        _style_workbook(writer)
    return workbook_path


def _style_workbook(writer: pd.ExcelWriter) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill

    for worksheet in writer.book.worksheets:
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.font = Font(name="Microsoft YaHei", bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        worksheet.row_dimensions[1].height = 34
        for column_cells in worksheet.columns:
            width = min(max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells) + 2, 42)
            worksheet.column_dimensions[column_cells[0].column_letter].width = max(width, 12)


def save_lifecycle_heat_plots(
    plots_dir: Path,
    *,
    summary: pd.DataFrame,
    detail: pd.DataFrame,
    mechanism_share: pd.DataFrame,
) -> list[Path]:
    """Save compact PNG report figures without calling ``plt.show``."""
    import matplotlib.pyplot as plt

    plt.style.use("science")
    plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"
    plt.rcParams["axes.unicode_minus"] = False
    plots_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if not summary.empty:
        heat_columns = [column for column in summary.columns if "平均产热功率" in column]
        if heat_columns:
            fig, ax = plt.subplots(figsize=(10, 5))
            plot_df = summary.sort_values("目标SOH(%)", ascending=False)
            for column in heat_columns:
                ax.plot(plot_df["目标SOH(%)"], plot_df[column], marker="o", label=column)
            ax.set_xlabel("SOH (%)")
            ax.set_ylabel("平均产热功率 (W)")
            ax.set_title("SOH诊断产热汇总")
            ax.invert_xaxis()
            ax.grid(True, ls="--", alpha=0.35)
            ax.legend()
            path = plots_dir / "SOH诊断产热汇总.png"
            fig.savefig(path, dpi=220, bbox_inches="tight")
            plt.close(fig)
            paths.append(path)
    if not detail.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        for direction, column in {"充电": "calibrated_total_charge_w", "放电": "calibrated_total_discharge_w"}.items():
            ax.scatter(detail["actual_soh_pct"], detail[column], label=direction)
        ax.set_xlabel("SOH (%)")
        ax.set_ylabel("平均总产热功率 (W)")
        ax.set_title("诊断点产热分布")
        ax.invert_xaxis()
        ax.grid(True, ls="--", alpha=0.35)
        ax.legend()
        path = plots_dir / "诊断点产热分布.png"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    if not mechanism_share.empty:
        share_columns = [column for column in mechanism_share.columns if column.endswith("占比(%)")]
        if share_columns:
            fig, ax = plt.subplots(figsize=(10, 5))
            plot_df = mechanism_share.sort_values("目标SOH(%)", ascending=False)
            ax.stackplot(plot_df["目标SOH(%)"], [plot_df[column].fillna(0) for column in share_columns], labels=share_columns)
            ax.set_xlabel("SOH (%)")
            ax.set_ylabel("机制占比 (%)")
            ax.set_title("老化机制占比")
            ax.invert_xaxis()
            ax.set_ylim(0, 100)
            ax.grid(True, ls="--", alpha=0.35)
            ax.legend(loc="upper left")
            path = plots_dir / "老化机制占比.png"
            fig.savefig(path, dpi=220, bbox_inches="tight")
            plt.close(fig)
            paths.append(path)
    return paths


def write_artifact_manifest(run_dir: Path, artifacts: Mapping[str, Any]) -> Path:
    """Write a machine-readable artifact manifest for the run."""
    manifest_path = run_dir / "artifacts.json"
    write_json(manifest_path, dict(artifacts))
    return manifest_path
