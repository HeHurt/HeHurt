"""开启接触电阻后，计算 params587（局部覆盖）与 paramsMIC 的 10 s 恒功率充电峰值。"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pybamm


def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "BatteryProject" / "src" / "simulation_peak.py").exists():
            return candidate
    raise RuntimeError(f"Cannot locate hithium project root from {here}")


PROJECT_ROOT = find_project_root()
BATTERYPROJECT_ROOT = PROJECT_ROOT / "BatteryProject"
PARAMS_ROOT = PROJECT_ROOT / "params"
for path in (BATTERYPROJECT_ROOT, PARAMS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from params587 import get_hithium_params as get_params587  # noqa: E402
from paramsMIC import get_hithium_params as get_paramsMIC  # noqa: E402
from src.simulation import run_peak_current  # noqa: E402
from src.simulation_peak import peak_current_condition  # noqa: E402


TEMPERATURE_K = 293.15
SOC = 0.98
PULSE_SECONDS = 10
REFERENCE_VOLTAGE_V = 3.2
UPPER_CUTOFF_V = 3.65
VAR_PTS = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
LOCAL_OVERRIDE_KEYS = [
    "Negative electrode conductivity [S.m-1]",
    "Positive particle radius [m]",
    "Negative particle diffusivity [m2.s-1]",
    "Positive particle diffusivity [m2.s-1]",
    "Negative electrode exchange-current density [A.m-2]",
    "Positive electrode exchange-current density [A.m-2]",
]


run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_587Ah_override_MIC_contact_on_20C_98SOC_10s_charge_peak_power"
run_dir = BATTERYPROJECT_ROOT / "output" / "runs" / "peak_power" / run_id
plots_dir = run_dir / "plots"
plots_dir.mkdir(parents=True, exist_ok=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(run_dir / "run.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,
)
logger = logging.getLogger("charge_peak_power_20C_98SOC")

config = {
    "workflow": "peak_power",
    "parameter_modules": ["params587", "paramsMIC"],
    "temperature_K": TEMPERATURE_K,
    "temperature_C": TEMPERATURE_K - 273.15,
    "initial_soc": SOC,
    "pulse_seconds": PULSE_SECONDS,
    "direction": "charge",
    "search_mode": "W",
    "upper_voltage_cutoff_V": UPPER_CUTOFF_V,
    "power_ratio_reference_voltage_V": REFERENCE_VOLTAGE_V,
    "587Ah_local_override_source": "paramsMIC at the same temperature",
    "587Ah_local_override_keys": LOCAL_OVERRIDE_KEYS,
    "global_parameter_files_modified": False,
    "model_options": {"contact resistance": "true"},
    "var_pts": VAR_PTS,
    "pybamm_version": pybamm.__version__,
}
(run_dir / "config.json").write_text(
    json.dumps(config, ensure_ascii=False, indent=2),
    encoding="utf-8",
)


def build_case_parameters(case_name):
    mic_params = get_paramsMIC(t_factor=1, temperature=TEMPERATURE_K)
    if case_name == "587Ah_local_MIC_kinetics":
        cell_params = get_params587(t_factor=1, temperature=TEMPERATURE_K)
        for key in LOCAL_OVERRIDE_KEYS:
            cell_params[key] = mic_params[key]
        return cell_params
    if case_name == "MIC_1175Ah":
        return mic_params
    raise KeyError(case_name)


def validate_constant_power_pulse(model, param, nominal_capacity, power_w):
    ratio = power_w / (nominal_capacity * REFERENCE_VOLTAGE_V)
    experiment = peak_current_condition(
        nominal_capacity,
        TEMPERATURE_K,
        ratio,
        time=PULSE_SECONDS,
        mode="W",
    )["charge_peak"]
    solver = pybamm.IDAKLUSolver(
        output_variables=["Time [s]", "Current [A]", "Voltage [V]"],
        rtol=1e-6,
        atol=1e-6,
    )
    simulation = pybamm.Simulation(
        model,
        parameter_values=param,
        experiment=experiment,
        solver=solver,
        var_pts=VAR_PTS,
    )
    solution = simulation.solve(initial_soc=SOC, direction="charge")
    first_voltage = float(solution["Voltage [V]"].entries[0])
    end_voltage = float(solution["Voltage [V]"].entries[-1])
    first_current = abs(float(solution["Current [A]"].entries[0]))
    end_current = abs(float(solution["Current [A]"].entries[-1]))
    return {
        "validation_end_time_s": float(solution["Time [s]"].entries[-1]),
        "validation_first_voltage_V": first_voltage,
        "validation_end_voltage_V": end_voltage,
        "validation_first_current_A": first_current,
        "validation_end_current_A": end_current,
        "validation_first_power_kW": first_voltage * first_current / 1000,
        "validation_end_power_kW": end_voltage * end_current / 1000,
    }


rows = []
for case_name, parameter_module in [
    ("587Ah_local_MIC_kinetics", "params587 + local paramsMIC override"),
    ("MIC_1175Ah", "paramsMIC"),
]:
    logger.info("Start %s", case_name)
    model = pybamm.lithium_ion.DFN(options={"contact resistance": "true"})
    cell_params = build_case_parameters(case_name)
    param = pybamm.ParameterValues("OKane2022")
    param.update(cell_params, check_already_exists=False)
    nominal_capacity = float(cell_params["Nominal cell capacity [A.h]"])

    result = run_peak_current(
        model,
        param,
        VAR_PTS,
        temperature=TEMPERATURE_K,
        nominal=nominal_capacity,
        t_period=PULSE_SECONDS,
        x0=1,
        charge_soc_list=[SOC],
        discharge_soc_list=[],
        mode="W",
    )
    peak_power_w = float(result["charge_peak_power"][0])
    equivalent_current_a = float(result["charge_peak_current"][0])
    validation = validate_constant_power_pulse(
        model,
        param,
        nominal_capacity,
        peak_power_w,
    )
    row = {
        "cell": case_name,
        "parameter_configuration": parameter_module,
        "nominal_capacity_Ah": nominal_capacity,
        "temperature_C": TEMPERATURE_K - 273.15,
        "initial_SOC": SOC,
        "pulse_duration_s": PULSE_SECONDS,
        "charge_peak_power_kW": peak_power_w / 1000,
        "equivalent_current_A_at_3p2V": equivalent_current_a,
        "equivalent_power_rate_at_3p2V": peak_power_w / (nominal_capacity * REFERENCE_VOLTAGE_V),
        **validation,
    }
    rows.append(row)
    logger.info("Done %s: %s", case_name, row)

metrics = pd.DataFrame(rows)
metrics.to_csv(run_dir / "metrics.csv", index=False, encoding="utf-8-sig")
metrics.to_excel(run_dir / "metrics.xlsx", index=False)

fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.6))
colors = ["#2878B5", "#C82423"]
labels = ["587Ah (MIC kinetics override)", "MIC 1175Ah"]

bars = axes[0].bar(labels, metrics["charge_peak_power_kW"], color=colors)
axes[0].set_ylabel("10 s charge peak power [kW]")
axes[0].set_title("Absolute constant-power capability")
axes[0].grid(axis="y", alpha=0.25)
axes[0].tick_params(axis="x", rotation=12)
for bar, value in zip(bars, metrics["charge_peak_power_kW"]):
    axes[0].text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}", ha="center", va="bottom")

bars = axes[1].bar(labels, metrics["equivalent_power_rate_at_3p2V"], color=colors)
axes[1].set_ylabel("Equivalent power rate [P/Pnom at 3.2 V]")
axes[1].set_title("Capacity-normalized capability")
axes[1].grid(axis="y", alpha=0.25)
axes[1].tick_params(axis="x", rotation=12)
for bar, value in zip(bars, metrics["equivalent_power_rate_at_3p2V"]):
    axes[1].text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom")

fig.suptitle("20°C, 98% SOC, 10 s constant-power charge (contact resistance on)")
fig.tight_layout()
fig.savefig(plots_dir / "charge_peak_power_comparison.png", dpi=200)
plt.close(fig)

summary = {"run_dir": str(run_dir), "results": rows}
(run_dir / "summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
