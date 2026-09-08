# 复现说明

## 直接运行

打开并执行全部单元格：

`02_模型/MIC_1175Ah_0p25P统一老化路径_多倍率全生命周期产热_参数标定.ipynb`

当前配置为25℃、0.25P统一老化，SOH节点100%至65%，诊断倍率为
0.125/0.167/0.25/0.5P，接触电阻为0.07018/0.0748 mΩ。参数指纹不一致时，
Notebook 不会复用旧检查点。

容量与DCR标定值已写入 `params/paramsMIC.py`；Notebook 内的 SEI、LAM 和
SEI resistivity 缩放系数均为 `1.0`，不得再次手工乘以0.50或0.35。

产热导出修正在参数配置单元设置：

```python
HEAT_EXPORT_SCALE = 1.0
HEAT_EXPORT_OFFSET_W = 0.0
```

计算公式为 `修正后产热 = 修正前总产热 × HEAT_EXPORT_SCALE + HEAT_EXPORT_OFFSET_W`。
例如整体放大20%设置为 `1.2, 0.0`；整体减去0.5 W设置为 `1.0, -0.5`。
修正仅作用于中文汇总、修正后总产热列和产热图，容量、DCR及原始产热分项不修正。

新版首次执行时，因为旧检查点没有SOH状态下的1C-30s DCR结果，会重新运行生命周期。
生成 `*_capacity_dcr_actual.csv` 后，参数指纹一致的后续运行可以直接复用。

## 固定参数后期寿命版本

`params/paramsMIC.py` 已写入固定参数后期寿命标定：

- LAM比例常数：`2.058e-7 * t_factor`。
- SEI kinetic系数：`2.16e-14 * k_sei * t_factor`。
- EC diffusivity系数：`1.575e-22 * D_sei * t_factor`。
- Paris裂纹参数保持原值。

Notebook参数指纹版本为 `lam2p94_sei0p9_af50_15k`，因此旧生命周期检查点不会被误用。
该版本使用同一套固定参数覆盖全寿命，不包含基于圈数或SOH的参数切换。

运行中间结果写入：

`BatteryProject/output/runs/mic_unified_lifecycle_heat/20260730_calibrated_capacity_dcr_v1`

验证完成后，将该 run 发布或复制到本任务的 `04_输出结果/标定后全生命周期结果`。

## 重新标定

```powershell
python "02_模型/MIC_25C_容量_DCR参数标定.py" --mode scan --run-id <新的run_id>
```

标定原始输出写入 `BatteryProject/output/runs/mic_lifecycle_calibration/<run_id>`。
当前有效结果已正式发布到 `04_输出结果/20260730_scan_v2`。

## 文件归档规则

- 实验输入：任务包 `03_输入数据`。
- 任务模型：任务包 `02_模型`。
- 未验证运行：`BatteryProject/output/runs/<workflow>/<run_id>`。
- 验证结果：任务包 `04_输出结果`。
- 报告结论：任务包 `01_仿真报告`。
- 不使用 `.codex`、Codex scratch 或聊天临时目录作为交付路径。
