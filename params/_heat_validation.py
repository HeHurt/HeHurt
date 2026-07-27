import sys, os, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:/HithiumSSD/hithium/BatteryProject")
sys.path.insert(0, r"C:/HithiumSSD/hithium/params")
import numpy as np
import pybamm
from src import config
config.ensure_entropy_loaded()
from src.analysis import get_all_heat_components
from params1300CW363 import get_hithium_params as g363

GRID = {"x_n": 8, "x_s": 8, "x_p": 8, "r_n": 16, "r_p": 16}
p = dict(g363(temperature=298.15))
pv = pybamm.ParameterValues("OKane2022"); pv.update(p, check_already_exists=False)
model = pybamm.lithium_ion.DFN()
exp = pybamm.Experiment([
    ("Charge at 0.25C until 3.65 V",),
    ("Rest for 5 minutes",),
    ("Discharge at 0.25C until 2.5 V",),
])
sim = pybamm.Simulation(model, parameter_values=pv, experiment=exp, var_pts=GRID,
                        solver=pybamm.CasadiSolver(rtol=1e-6, atol=1e-6, mode="safe"))
t0 = time.time()
sol = sim.solve()
print(f"solve time {time.time()-t0:.1f}s  (sim time {sol['Time [s]'].entries[-1]/3600:.2f} h)")
V = sol["Terminal voltage [V]"].entries
print("V range:", float(V.min()), float(V.max()))
h = get_all_heat_components(sol, label_for_temp="25°C 0.25P")
print("total_chg:", h["total_chg"], "total_dchg:", h["total_dchg"])
print("irrev_chg:", h["irrev_chg"], "rev_chg:", h["rev_chg"])
print("irrev_dchg:", h["irrev_dchg"], "rev_dchg:", h["rev_dchg"])
