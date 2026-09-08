import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pybamm


PROJECT_ROOT = Path(r"D:\Users\hez\Desktop\hithium")
TASK_ROOT = (
    PROJECT_ROOT
    / "work"
    / "MIC_LDS"
    / "202607_何争_LDS CW368模型对标及0.125-0.167-0.25P产热功率仿真"
)
for path in [Path(__file__).parent, PROJECT_ROOT / "params"]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from paramsLDSCW368 import get_hithium_params


def run(direction, power_w, initial_soc):
    temperature = 298.15
    params = pybamm.ParameterValues("OKane2022")
    params.update(
        get_hithium_params(1, temperature),
        check_already_exists=False,
    )
    params.update(
        {
            "Ambient temperature [K]": temperature,
            "Initial temperature [K]": temperature,
        },
        check_already_exists=False,
    )
    model = pybamm.lithium_ion.DFN(
        {
            "thermal": "isothermal",
            "calculate heat source for isothermal models": "true",
            "contact resistance": "true",
            "open-circuit potential": ("current sigmoid", "current sigmoid"),
        }
    )
    action = "Charge" if direction == "充电" else "Discharge"
    cutoff = 3.65 if direction == "充电" else 2.5
    experiment = pybamm.Experiment(
        [f"{action} at {power_w} W until {cutoff} V"],
        period="30 seconds",
    )
    simulation = pybamm.Simulation(
        model,
        parameter_values=params,
        experiment=experiment,
        solver=pybamm.IDAKLUSolver(rtol=1e-6, atol=1e-8),
        var_pts={"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20},
    )
    solution = simulation.solve(initial_soc=initial_soc)
    capacity = np.abs(
        np.asarray(solution["Discharge capacity [A.h]"].entries, dtype=float)
    )
    capacity = np.abs(capacity - capacity[0])
    current = np.asarray(solution["Current [A]"].entries, dtype=float)
    contact_heat = current**2 * float(params["Contact resistance [Ohm]"])
    electrochemical_heat = np.asarray(
        solution["Total heating [W]"].entries,
        dtype=float,
    )
    return pd.DataFrame(
        {
            "capacity_ah": capacity,
            "voltage_v": solution["Terminal voltage [V]"].entries,
            "heat_w": electrochemical_heat + contact_heat,
            "contact_heat_w": contact_heat,
        }
    )


for direction, initial_soc_values in [
    ("充电", [0.008]),
    ("放电", [0.995]),
]:
  for initial_soc in initial_soc_values:
    curve = run(direction, 627.91, initial_soc)
    print(
        direction,
        initial_soc,
        "n",
        len(curve),
        "capacity",
        curve.capacity_ah.iloc[-1],
        "voltage",
        curve.voltage_v.iloc[0],
        curve.voltage_v.iloc[-1],
        "heat_mean",
        curve.heat_w.mean(),
        "heat_max",
        curve.heat_w.max(),
    )
