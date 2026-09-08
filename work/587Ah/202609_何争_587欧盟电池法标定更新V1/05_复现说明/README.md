# 复现说明

## 任务性质

本任务为**结论汇报页的落盘版**，不重新跑仿真；所有数字均直接来自前置任务 `202608_何争_587欧盟电池法循环DCR实测复核V1` 的最终 run：

```
source_run_id = 20260831_587eu_final_sched_3_1p3_1p2_13000
```

源截图：`04_输出结果/RE_HC587Base_E212_587电池循环与DCR标定更新_20260902.png`
结构化结果：`04_输出结果/results_summary.json`

## 与 V1 的衔接

- 本任务**复用** V1 的全部标定参数（`t_factor = 50`、`capacity_scale = 1.0106`、`early_ec_schedule = 3.0, 1.3, 1.2`）。
- 本任务**未写回** `params/params587.py`；当前工作区参数基线（含接触电阻 `0.056276e-3 → 0.061291e-3 Ω` 的未提交差异）与 V1 一致。
- 仿真结果中 1732 圈以内为实测覆盖、1732 圈以外为模型外推。

## 复现命令（沿用 V1）

完整复现见 `202608_何争_587欧盟电池法循环DCR实测复核V1/05_复现说明/README.md`。两条核心命令：

```powershell
# 1800 圈实测验证
python work/587Ah/202608_何争_587欧盟电池法循环DCR实测复核V1/02_模型/run_587_eu_validation.py --run-id 20260831_587eu_final_sched_3_1p3_1p2_1800 --mode validate --total-real-cycles 1800 --interval-real-cycles 100 --capacity-scale 1.0106 --early-ec-schedule 3.0,1.3,1.2

# 13000 圈条件外推
python work/587Ah/202608_何争_587欧盟电池法循环DCR实测复核V1/02_模型/run_587_eu_validation.py --run-id 20260831_587eu_final_sched_3_1p3_1p2_13000 --mode projection --total-real-cycles 13000 --interval-real-cycles 100 --capacity-scale 1.0106 --early-ec-schedule 3.0,1.3,1.2
```

## 复现验收

- `results_summary.json` 中 `all_accepted = true`，全部 6 项主验收通过。
- `capacity_metrics` 中 `前300圈 MAE = 0.263 pp`、`全区段 MAE = 0.153 pp`、`容量 RRMSE = 0.953%`。
- `dcr_metrics` 中 `放电 MAPE = 2.51%`、`平均 MAPE = 4.54%`、`充电 MAPE = 6.91%`（充电侧单列观察）。
- `retention` 中 1000 圈仿真 93.91% / 实测 94.01%；10000 圈外推 74.86%；13000 圈外推 67.96%。

## 后续动作

1. 用新批次前 300 圈容量数据做外部验证，判断早期 EC 调度的可迁移性。
2. 结合 RPT、SOC 分段 HPPC/DCR 与机理量测，校核充电侧 DCR 略低估。
3. 验证稳定后，再考虑升级任务版本并将 EC 调度固化进 `params587.py`。