# 复现说明

## 环境与输入

- 工作目录：`D:\Users\hez\Desktop\hithium`
- 推荐 Notebook：`02_模型/587Ah_欧盟电池法循环DCR实测复核.ipynb`。已更新为 587Ah、0.5P、1C-30s DCR、`t_factor=50` 和早期 EC 调度的完整版本；默认读取已验收 run，可直接重跑全部后处理。
- Python 入口：`work/587Ah/202608_何争_587欧盟电池法循环DCR实测复核V1/02_模型/run_587_eu_validation.py`
- 参数文件：`params/params587.py`，本任务未写回；复现应保留当前工作区接触电阻值。
- 输入数据：`03_输入数据/capacity_25c_0p5p_20260828.csv`、`03_输入数据/dcr_50soc_1c30s_20260828.csv`。

## 1800 圈实测验证

```powershell
python work/587Ah/202608_何争_587欧盟电池法循环DCR实测复核V1/02_模型/run_587_eu_validation.py --run-id 20260831_587eu_final_sched_3_1p3_1p2_1800 --mode validate --total-real-cycles 1800 --interval-real-cycles 100 --capacity-scale 1.0106 --early-ec-schedule 3.0,1.3,1.2
```

原始运行目录：`BatteryProject/output/runs/eu_battery_regulation/20260831_587eu_final_sched_3_1p3_1p2_1800`

## 13000 圈条件外推

```powershell
python work/587Ah/202608_何争_587欧盟电池法循环DCR实测复核V1/02_模型/run_587_eu_validation.py --run-id 20260831_587eu_final_sched_3_1p3_1p2_13000 --mode projection --total-real-cycles 13000 --interval-real-cycles 100 --capacity-scale 1.0106 --early-ec-schedule 3.0,1.3,1.2
```

原始运行目录：`BatteryProject/output/runs/eu_battery_regulation/20260831_587eu_final_sched_3_1p3_1p2_13000`

## 复现验收

- `config.json` 中 `acceleration_factor=50`、`capacity_scale=1.0106`、`early_ec_schedule="3.0,1.3,1.2"`。
- `validation_summary.json` 中 `early_accept=true`、`capacity_accept=true`、`dcr_accept=true`、`overall_accept=true`。
- 前期保持率 MAE/最大误差约为 0.263/0.310 个百分点，全区间 MAE 约为 0.153 个百分点，容量 RRMSE 约为 0.953%。
- 放电/平均 DCR MAPE 约为 2.510%/4.543%。
- `model_checkpoints.csv` 的 13000 圈保持率约为 67.961%，且大于 1732 圈的结果按模型外推使用。
- Notebook 默认执行会在 `04_输出结果/notebook_postprocessing/` 生成7张后处理图和 `587Ah_欧盟电池法完整后处理.xlsx`；需要 SEI、LAM、孔隙率、析锂及充放电曲线时，将 `RUN_MECHANISM_RERUN=True` 后从机理重跑章节继续执行。

早期调度为任务内经验型覆盖，不写回 `params587.py`；若迁移到其他批次，应重新做前300圈独立验证。
