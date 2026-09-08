import importlib.util
import sys
import time
from pathlib import Path

import numpy as np
import pybamm

TASK_MODULE = Path(
    r"D:\Users\hez\Desktop\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW501模型对标及峰值电流Mapping"
    r"\02_模型\cw501_peak_current_mapping.py"
)

spec = importlib.util.spec_from_file_location("cw501_peak_current_mapping", TASK_MODULE)
workflow = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(workflow)

sys.path.insert(0, str(workflow.BATTERY_PROJECT))
from src.simulation_peak import _prepare_peak_current_parameter_values

model = workflow.build_peak_model()
params = _prepare_peak_current_parameter_values(
    workflow.fresh_parameter_values(25), model
)
params.update({"Current function [A]": "[input]"})
solver = pybamm.IDAKLUSolver(
    output_variables=["Time [s]", "Current [A]", "Voltage [V]"],
    rtol=1e-6,
    atol=1e-6,
)
sim = pybamm.Simulation(
    model,
    parameter_values=params,
    solver=solver,
    var_pts=workflow.VAR_PTS,
)
t_eval = np.arange(0, 10.0 + 1e-9, 2.0)

for current_a, soc in [
    (-2316.74, 0.5),
    (-2000.0, 0.5),
    (-1800.0, 0.4),
    (-1000.0, 0.0),
    (1000.0, 1.0),
    (5681.82, 0.5),
]:
    direction = "charge" if current_a < 0 else "discharge"
    started = time.perf_counter()
    try:
        solution = sim.solve(
            t_eval=t_eval,
            initial_soc=soc,
            direction=direction,
            inputs={"Current function [A]": current_a},
        )
    except pybamm.SolverError as error:
        print(current_a, soc, "ERROR", error)
        continue
    elapsed = time.perf_counter() - started
    print(
        current_a,
        soc,
        elapsed,
        solution["Time [s]"].entries[-1],
        solution["Voltage [V]"].entries[0],
        solution["Voltage [V]"].entries[-1],
        solution.termination,
    )
