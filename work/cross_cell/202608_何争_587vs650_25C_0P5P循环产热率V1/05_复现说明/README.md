# 复现说明

## 任务
587 vs 650 电芯 25°C 0.5P 循环全生命周期产热率仿真（含 0.25P 诊断）：
- 主循环 0.5P 恒功率驱动老化，每 50 等效圈一个 0.5P 产热率点
- 每 5% SOH 点位额外跑一次 0.25P 循环，记录该 SOH 下的 0.25P 产热率
- 跑到 65% SOH 自动停止

## 环境
- Python 3.11（系统解释器 `C:\Users\hez\AppData\Local\Programs\Python\Python311\python.exe`，DLP 白名单）
- PyBaMM 26.4.2；依赖 numpy/pandas/scipy/openpyxl/matplotlib + scienceplots
- 工作区：`C:\HithiumSSD\hithium`（= `D:\Users\hez\Desktop\hithium`）

## 快速查看结果
- `04_输出结果/<run_id>/587vs650_每5pctSOH产热率.xlsx`：5 sheet（587/650 0.5P 采样 + 0.5P 对比 + 587/650 0.25P 诊断）
- `04_输出结果/<run_id>/图表/587vs650_全生命周期产热对比.png`：0.5P 4 子图
- `04_输出结果/<run_id>/图表/587vs650_0P25P产热率vsSOH.png`：0.25P 诊断 2 子图
- `04_输出结果/<run_id>/{587,650}_heat_lifecycle.csv`：0.5P 全生命周期逐点明细
- `04_输出结果/<run_id>/{587,650}_diag_0p25P_heat.csv`：0.25P 诊断产热率明细

## 复现方式（二选一）

### A. Notebook（推荐，含求解+后处理全流程说明）
打开 `02_模型/587vs650_25C_0P5P_循环产热率仿真.ipynb`，逐 cell 运行：
1. cell 1-3：导入环境与工况配置（`RUN_MODE` 可选 `smoke` / `study`，`RUN_CELLS` 可选 `["587","650"]`）
2. cell 4-5：双模型生命周期仿真（587 → 939.2W，650 → 1040W 0.5P 老化路径 + 每 5% SOH 0.25P 诊断）
3. cell 6-7：0.5P 每 5% SOH 产热率采样
4. cell 8-9：0.25P 诊断产热率 vs SOH（8 个真实诊断点）
5. cell 10-11：0.5P 对比表与对比图
6. cell 12-13：Excel 导出
7. cell 14-15：结论要点

### B. Headless 脚本（命令行一键运行）
```bash
cd C:\HithiumSSD\hithium
# 快速验证（150 等效圈）
python "work/cross_cell/202608_何争_587vs650_25C_0P5P循环产热率V1/02_模型/run_587_650_heat.py" --mode smoke
# 正式仿真（跑到 65% SOH 自动停止，约 25 分钟）
python "work/cross_cell/202608_何争_587vs650_25C_0P5P循环产热率V1/02_模型/run_587_650_heat.py" --mode study
# 可选：只跑单电芯
python "work/cross_cell/202608_何争_587vs650_25C_0P5P循环产热率V1/02_模型/run_587_650_heat.py" --mode study --cells 587
```

## 数据说明
- 参数：587 用 `params/params587.py`；650 用 `params/params650.py`（基于 587 替换 650 310mm 宽度设计参数）
- 熵热先验：`data_raw/AI_virtual_cell/Exp/熵热系数测试数据/analysis_output/entropy_coefficient_fits_by_branch.csv`（SOH95% 充放电支路）
- 模型口径：等温 + 完整老化（SEI/plating/particle mechanics/SEI on cracks/LAM）
- 0.5P 主循环产热链 + 0.25P 诊断产热链（同一套）
- 650 的滞后权重与熵热曲线沿用 587 同一基准（无 650 专属标定，临时先验）
- 停止逻辑：`stop_at_lowest_diagnostic_soh=True` + `diagnostic_soh_targets_pct=[100,95,...,65]` + `diagnostic_p_rates=[0.25]`
- 容量检查间隔 250 圈（保证诊断贴近目标 SOH 触发）
- 占位 cycle 过滤：`len(steps) >= 2` 才提取产热（避免 rest 单 step 占位 cycle 引发计算错误）
- 650 的 65% SOH 诊断点因容量悬崖实际在 48.45% 处测量（详见报告）

## 输出约定
- 原始运行写入 `04_输出结果/run_<mode>_<时间戳>/`（任务级交付包内，未用 publish-task 二次发布）
- 每次正式运行生成新的时间戳目录，不覆盖旧结果