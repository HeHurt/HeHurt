# LDS CW501 膨胀力老化对标 — 复现说明

## 环境

- Python：`C:\HithiumSSD\hithium\BatteryProject\.venv\Scripts\python.exe`（pybamm 26.4.2，matplotlib science 样式）
- 体系参数：`C:\HithiumSSD\hithium\params\paramsLDSCW501.py`

## 快速查看

直接打开 `02_模型/LDS_CW501_膨胀力老化对标.ipynb`（VSCode，内核选 BatteryProject venv），
默认加载 `04_输出结果/final_calibration.json` 秒开；将 `RERUN_SIM=True` 可重跑仿真。

## 复现仿真（全流程）

```bash
cd 02_模型
# 冒烟测试（2 圈）
python lds_force_core.py --smoke
# 最终标定（双工况，各 8 圈 x t_factor=50，每工况约 40s）
python run_final.py
```

产物：`04_输出结果/final_calibration.png` + `final_calibration.json`。

## 扫描复现（可选）

```bash
python scan_aging.py --c-rate 0.125 --k-eff 3.0e6 --preload 296   # 老化机制扫描
python scan_force.py --c-rate 0.25 --combos F1:3e6:310,F2:6e6:310  # 力学扫描
```

## 输入数据说明

`03_输入数据/*.json` 由 `E:\Downloads\膨胀力数据整理.xlsx` 提取：
- `cycle_force_comparison.json`：5 组逐圈 SOH/F_max/F_min
- `single_cycle_*.json`：单圈剖面（cls1/100/200/300；组间空 2 列，序号按行序，时间列为 datetime 已转字符串）
