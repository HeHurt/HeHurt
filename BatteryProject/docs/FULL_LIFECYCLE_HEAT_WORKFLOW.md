# 全生命周期产热仿真流程

## 1. 当前统一口径

314Ah 和 587Ah 生命周期 Notebook 均保持 PyBaMM `thermal="isothermal"`，不求解温升；模型选项
`calculate heat source for isothermal models="true"` 仅用于计算内部产热分项。

最终校准产热功率为：

```text
Q_calibrated = Q_ohmic + Q_reaction + Q_mixing + Q_hysteresis
             + I^2 * R_contact + Q_reversible,SOH95
Q_reversible,SOH95 = mean(I * T * dU/dT_branch,SOH95)
```

- `dU/dT` 在整个生命周期固定使用 `SOH95%` 充、放电支路，避免 SOH 数据集切换造成台阶。
- `raw` 保留 BatteryProject 历史后处理结果；`corrected` 保留可配置修正层；默认图和摘要使用 `calibrated`。
- 314Ah 使用本电芯 SOH95 实测全电芯熵热系数。
- 587Ah 暂用 314Ah SOH95 曲线作为同体系 LFP/graphite 先验，必须在报告中标注为转用参数。

当前 BOL 标定参数：

| Cell | equilibrium charge weight | contact resistance | SOH95 entropy source |
|---|---:|---:|---|
| 314Ah | 0.350444 | 4.12e-5 ohm | 314Ah measured |
| 587Ah | 0.310139 | 7.39e-5 ohm | transferred from 314Ah |

## 2. 标准运行步骤

1. 确认工况、温度、截止电压、容量和 contact resistance 与 ARC/BOL 标定工况一致。
2. 参数或模型选项发生变化时，先分别执行 BOL thermal heat diagnosis Notebook，确认充、放电平均产热均在实测值的 +/-10% 内。
3. 在生命周期 Notebook 中先设置 `RUN_MODE="smoke"`，执行全部 cell。
4. 检查 smoke 输出：无 error、产热为有限正值、BOL 与标定一致、cycle/SOH 图无空值或突变。
5. 设置 `RUN_MODE="study_unified"`，重启 kernel 后执行全部 cell，生成 13,000 圈正式结果。
6. 验收容量保持率、BOL/EOL 产热、最大相邻跳变和 BOL/EOL 分项增量，再用于报告。

Notebook：

- `work/314Ah/notebooks/314Ah_0p5P_lifecycle_heat_rate.ipynb`
- `work/587Ah/notebooks/587Ah_0p5P_lifecycle_heat_generation.ipynb`

正式输出：

- `BatteryProject/output/314Ah_0.5P全生命周期产热/正式结果/`
- `work/587Ah/notebooks/output/587Ah_0p5P_lifecycle_heat/正式结果/`

默认每个电芯只生成 4 个文件：1 个中文 Excel 和 3 张中文图。Excel 包含
`结果汇总`、`循环产热`、`产热分项`、`老化机制`、`仿真配置` 五个 sheet。

## 3. 后处理与判读

优先读取中文工作簿：

- `循环产热`：等效循环圈数、SOH、充放电总产热、不可逆热和可逆热，共 8 列。
- `产热分项`：ohmic、reaction、hysteresis、contact 和固定 SOH95 可逆热。
- `老化机制`：各机制绝对损失及占比。
- 314Ah 为 50、100、...、13000 圈，共 260 个仿真点。
- 587Ah 保留 cycle 1 基准点及 50、100、...、13000 圈，共 261 个仿真点。

上述产热点均来自加速模型实际求解的 cycle，没有逐圈插值。SOH 图固定 100% 在左，
沿横坐标向右递减。Notebook 内仍保留 raw/corrected/calibrated 数据；只有设置
`EXPORT_DEBUG_FILES=True` 才会在 Excel 中增加 `调试明细` sheet。

若末期产热明显增大，先看分项增量。ohmic 主导通常表示阻抗增长；reversible 主导才需要优先检查熵热系数和 SOC 映射。不要直接用 `*0.9` 或 `+1 W` 覆盖原始列；如需工程修正，只设置 `HEAT_CORRECTION`，并同时保留 raw/calibrated/corrected 三套结果。

## 4. 需要重新标定的情况

- 更换电芯、化学体系、充放电倍率、温度或截止电压。
- 更新 OCP/hysteresis、contact resistance 或熵热系数数据。
- 启用 lumped/x-full thermal 温升耦合。
- 587Ah 获得本电芯实测 `dU/dT` 后，应替换转用曲线并重新执行 BOL 与全生命周期验收。

固定 SOH95 是当前避免突变的工程口径，不表示可逆热与老化无关。以后若启用 SOH 相关熵热，应先建立连续、质量受控的 `dU/dT(SOC, SOH, branch)` 曲面，并用 BOL/中期/EOL 实测同时验证，不能直接按离散 SOH 标签切换。
