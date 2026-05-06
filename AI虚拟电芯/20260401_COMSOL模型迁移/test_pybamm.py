import pybamm
from batteryinfo.parameters.Hithium314B1 import BatteryDirect, battery_design, params, LFP, Gr, Electrolyte, Separator

# 创建模型
model = pybamm.lithium_ion.DFN()
p = 314 * 3.2 * 0.5
# 💡 使用你刚才注册的自定义参数集！
parameter_values = pybamm.ParameterValues(BatteryDirect(battery_design, [], LFP, Gr, Electrolyte, Separator).get_params('charge', params))
experiment = pybamm.Experiment(
    [
        f"Charge at {p}W until 3.65V",
        "Rest for 30 minute (0.1 minute period)",
        f"Discharge at {p}W until 2.5V",
    ]
)
# 运行模拟
sim = pybamm.Simulation(model, parameter_values=parameter_values, experiment=experiment)
sim.solve([0, 3600])
sim.plot()