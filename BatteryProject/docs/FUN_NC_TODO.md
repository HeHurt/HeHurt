# Fun_NC.py 未迁入能力 — 待办清单

原文件：`MIC/宫工-徐恒-不同CW/Fun_NC.py`（约 1312 行，已标记 `[LEGACY - PARTIAL]`）

电解液干涸主链已在 `src/electrolyte_dryout.py` 中完整工程化。
以下能力**尚未迁入**，请按优先级评估后逐项拆分。

---

## 高优先级（核心分析，未来仿真复用可能性高）

### 1. `Get_SOH_LLI_LAM` → `src/analysis.py` 或 `src/aging_metrics.py`

```python
def Get_SOH_LLI_LAM(my_dict_RPT, model_options, DryOut, mdic_dry, cap_0):
```

- 功能：从 RPT 结果字典中分解 SOH / LLI（锂损失）/ LAM（活性材料损失）占比。
- 建议目标：`src/analysis.py` 的新函数 `decompose_soh_lli_lam()`，与 `extract_all_metrics_from_sol` 整合。
- 迁移难度：⭐⭐（需处理 DryOut 分支逻辑）

### 2. `Run_Breakin` → `src/experiment_utils.py` 或 `src/simulation.py`

```python
def Run_Breakin(model, params, solver, var_pts, ...):
```

- 功能：化成循环控制（按设定工步激活 SEI，初始化电芯状态）。
- 建议目标：`src/simulation.py` 新函数 `run_breakin()`，返回初始化后的 `sol`。
- 迁移难度：⭐⭐（需抽象工步参数，去掉硬编码路径）

---

## 中优先级（绘图，与 plotting.py 体系整合）

### 3. `Plot_Cyc_RPT_4` → `src/plotting.py`

- 功能：多温度/多工况老化容量 + DCR + 功率 RPT 四格子图。
- 建议：封装为 `BatteryPlotter.plot_rpt_summary()` 或独立函数。
- 迁移难度：⭐⭐⭐（图形布局复杂，需适配 BatteryPlotter 数据结构）

### 4. `Plot_DMA_Dec` / `Plot_HalfCell_V` → `src/plotting.py`

- `Plot_DMA_Dec`：DMA 衰减分解条形图。
- `Plot_HalfCell_V`：半电池电压对标图。
- 迁移难度：⭐⭐

---

## 低优先级（参数扫描，与 parameter_identification.py 概念重叠）

### 5. `Get_Scan_files` / `Get_Scan_Orth_Latin` → `src/parameter_identification.py`

- 功能：
  - `Get_Scan_files`：笛卡尔积参数组合，分包写 CSV。
  - `Get_Scan_Orth_Latin`：拉丁超立方采样（LHS，依赖 `pyDOE`）。
- 建议：`src/parameter_identification.py` 新增 `build_scan_grid()` / `build_lhs_grid()`。
- 迁移难度：⭐⭐（`pyDOE` 依赖需加入 requirements.txt）

### 6. `Write_Dict_to_Excel` / `Run_P2_Excel` → `src/utils.py`

- 功能：批量把仿真结果字典写入格式化 Excel（多 sheet、条件格式）。
- `src/analysis.py` 中 `export_cycle_metrics_report` 已有类似能力，评估是否合并。
- 迁移难度：⭐⭐

---

## 评估后可忽略的函数

| 函数名 | 原因 |
|---|---|
| `handle_signal` / `TimeoutFunc` | 与 `func_timeout` 绑定，Python 3.11+ 推荐用 `concurrent.futures` 替代 |
| `generate_combinations` / `save_rows_to_csv` | 工具函数，可被 pandas + itertools 一行替代 |
| `recursive_scan` | 仅用于 `Get_Scan_files` 内部，迁移时一起迁 |
| `Check_concave_convex` | 调试用，当前无明确复用场景 |
| `Copy_png` | 文件拷贝工具，不属于仿真逻辑 |

---

## 迁移守则

1. 迁移一个函数 → 同步在 `easy_imports.py` 导出 → 在 `BatteryProject/tests/` 新增 smoke test。
2. 迁移后在 Fun_NC.py 对应函数上方加注释 `# [MIGRATED → src/xxx.py:function_name]`。
3. 每次迁移不超过 3 个函数，保持可回滚粒度。
