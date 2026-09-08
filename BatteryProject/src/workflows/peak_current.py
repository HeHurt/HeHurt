"""Canonical peak-current workflow: Studio 与 headless 共用的峰值电流/功率扫描入口。

对齐 output/runs/peak_current/<时间戳>_<case>/ 惯例(见历史 run config.json),
供 api/jobs.py 的 JOB_TYPES["peak_current"] 与 notebook 复用。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import pybamm

from ..notebook import load_params
from ..simulation_peak import run_peak_current
from ..workflow_runtime import WorkflowRunContext, create_run_context, write_json

STANDARD_VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}


def _round_or_none(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class PeakCurrentWorkflowSpec:
    """Validated input contract for the peak-current workflow."""

    cell: str
    run_mode: str = "smoke"
    temperature_c: float = 25.0
    nominal_ah: float | None = None
    pulse_duration_s: float = 10.0
    mode: str = "A"  # A=恒流 / W=恒功率
    direction: str = "both"  # charge / discharge / both
    soc_list: tuple[float, ...] = (0.95, 0.5, 0.2)
    var_pts: dict[str, int] = field(default_factory=lambda: dict(STANDARD_VAR_PTS))

    def __post_init__(self) -> None:
        if not self.cell:
            raise ValueError("cell is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")
        if self.mode not in {"A", "W"}:
            raise ValueError("mode must be 'A' or 'W'")
        if self.direction not in {"charge", "discharge", "both"}:
            raise ValueError("direction must be 'charge'/'discharge'/'both'")
        if self.pulse_duration_s <= 0:
            raise ValueError("pulse_duration_s must be positive")
        if any(soc <= 0 or soc >= 1 for soc in self.soc_list):
            raise ValueError("soc_list values must be in (0, 1)")

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "PeakCurrentWorkflowSpec":
        return cls(
            cell=str(config["cell"]),
            run_mode=str(config.get("run_mode", "smoke")),
            temperature_c=float(config.get("temperature_c", 25.0)),
            nominal_ah=config.get("nominal_ah"),
            pulse_duration_s=float(config.get("pulse_duration_s", 10.0)),
            mode=str(config.get("mode", "A")),
            direction=str(config.get("direction", "both")),
            soc_list=tuple(float(v) for v in config.get("soc_list", (0.95, 0.5, 0.2))),
            var_pts=dict(config.get("var_pts", STANDARD_VAR_PTS)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_peak_workflow(
    spec: PeakCurrentWorkflowSpec,
    *,
    project_root: Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the peak-current/peak-power scan and write standard run artifacts."""
    project_root = project_root or Path(__file__).resolve().parents[2]
    context: WorkflowRunContext = create_run_context(
        "peak_current",
        spec.to_dict(),
        project_root=project_root,
        run_id=run_id,
    )
    params_fn = load_params(spec.cell)
    cell_params = params_fn(1, 298.15)
    nominal_ah = float(spec.nominal_ah or cell_params["Nominal cell capacity [A.h]"])

    model = pybamm.lithium_ion.DFN(options={"contact resistance": "true"})
    param = pybamm.ParameterValues("OKane2022")
    param.update(cell_params, check_already_exists=False)

    charge_soc = list(spec.soc_list) if spec.direction in {"charge", "both"} else []
    discharge_soc = list(spec.soc_list) if spec.direction in {"discharge", "both"} else []
    result = run_peak_current(
        model,
        param,
        spec.var_pts,
        temperature=spec.temperature_c + 273.15,
        nominal=nominal_ah,
        t_period=spec.pulse_duration_s,
        x0=1,
        charge_soc_list=charge_soc,
        discharge_soc_list=discharge_soc,
        mode=spec.mode,
    )

    rows: list[dict[str, Any]] = []
    for direction, socs, currents, powers, first_voltages in (
        ("charge", result["charge_soc"], result["charge_peak_current"], result["charge_peak_power"], result["charge_first_voltage"]),
        ("discharge", result["discharge_soc"], result["discharge_peak_current"], result["discharge_peak_power"], result["discharge_first_voltage"]),
    ):
        for soc, current, power, first_voltage in zip(socs, currents, powers, first_voltages):
            rows.append(
                {
                    "direction": direction,
                    "soc": round(float(soc), 4),
                    "peak_current_A": _round_or_none(current),
                    "peak_C_rate": _round_or_none(current / nominal_ah) if current is not None else None,
                    "peak_power_kW": _round_or_none(power / 1000.0),
                    "first_voltage_V": _round_or_none(first_voltage),
                }
            )

    summary = {
        "workflow": "peak_current",
        "cell": spec.cell,
        "run_mode": spec.run_mode,
        "temperature_c": spec.temperature_c,
        "pulse_duration_s": spec.pulse_duration_s,
        "mode": spec.mode,
        "nominal_capacity_ah": nominal_ah,
        "pybamm_version": pybamm.__version__,
        "results": rows,
    }
    write_json(context.run_dir / "summary.json", summary)
    write_json(
        context.run_dir / "metrics.json",
        {"workflow": "peak_current", "rows": len(rows), "soc_points": len(spec.soc_list)},
    )
    return {
        "workflow": "peak_current",
        "context": context,
        "summary": summary,
        "metrics_path": context.run_dir / "metrics.json",
    }
