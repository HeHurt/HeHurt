# 复现说明

1. 使用 `02_模型/cw368_1300_multirate.py` 运行五个倍率的恒功率充放电仿真。
2. 每个温度工况均重新创建 `pybamm.ParameterValues("OKane2022")` 并加载 CW368-1300Ah 参数，避免跨温度参数污染。
3. 原始运行目录为 `BatteryProject/output/runs/cw368_1300_temperature_map/20260904_151641_CW368_1300Ah_temperature_map`。
4. `04_输出结果` 为发布后的精简结果；完整曲线位于 Excel 的“充电曲线”和“放电曲线”工作表。
5. `99_内部文件` 保存运行配置、CSV、日志与机器验收记录。

运行脚本需要项目现有 PyBaMM 环境以及 `02_模型` 中的 OCP 数据和参数文件。
