# 2026-05-22 工作区整理 Inventory

## 说明
- 仅统计主工作树，排除 `.claude/worktrees`
- 本清单用于指定 canonical 位置与后续处理策略，不在本阶段直接删除研究数据

## 1. 参数 CSV 重复分布

### canonical
- `params/` 作为材料曲线与参数 CSV 的唯一来源

### 重复候选目录
- `314/314电芯构网对标notebook/params/`
- `studies/314Ah/notebooks/可靠性对标notebook/params/`（原 `314/可靠性对标notebook/params/`）
- `314/diff_rate/params/`
- `工具/探索/params/`

### 处理建议
- `314/diff_rate/params/` 中 `E_DL_int1.csv`、`E_sigma.csv`、`E_transpNm.csv`、`Gr_charge.csv`、`LFP.csv` 已核验与 `params/` 一致，已替换为指向 canonical 文件的硬链接
- `314/diff_rate/params/Gr_discharge.csv` 与 `params/` 不一致，保留为本地研究快照
- `314/314电芯构网对标notebook/params/` 与 `studies/314Ah/notebooks/可靠性对标notebook/params/` 的 `E_DL_int1.csv`、`E_sigma.csv`、`E_transpNm.csv`、`LFP.csv` 彼此一致，但整体与 `params/` 不一致
- 上述两个 314 study-local params 目录中的 `Gr_charge.csv` 与 `Gr_discharge.csv` 也与 `params/` 分叉，暂不回收
- `工具/探索/params/` 与上述 314 study-local 快照也不一致，保留为独立历史快照
- `comsol_ocv.csv`、`Exp_CP.csv`、`Exp_DP.csv`、`Sim_CC.csv`、`Sim_CP.csv`、`Sim_DP.csv` 先视为 study-local 数据，不并入 `params/`

## 2. 314 对标 Rate 数据

### 目录
- `studies/314Ah/notebooks/可靠性对标notebook/Rate/`（原 `314/可靠性对标notebook/Rate/`）
- `工具/探索/Rate/`

### 已核验事实
- 公共文件名至少包含 10 个电压/温度 `.dat`
- `工具/探索/Rate/` 额外包含 `*_t_实际电流.dat`
- 抽样哈希确认：`0.25_实际电压.dat` 两处一致
- 抽样哈希确认：`1_电池平均温度.dat` 两处一致

### canonical
- 后续统一汇总到 `data_raw/314Ah/benchmark_rate/`

### 处理建议
- 先迁移两处目录到统一 raw 位置
- 迁移后保留带 `*_t_实际电流.dat` 的完整集合
- 旧目录只在所有引用切换后删除

## 3. 587 原始 Excel 副本

### 路径
- `587/Exp/欧盟电池法仿真数据/587Ah-cell performance.xlsx`
- `BatteryProject/data/587Ah-cell performance.xlsx`

### 已核验事实
- 两处文件 SHA256 完全一致

### canonical
- 原始大文件归档到 `data_raw/587Ah/`
- `BatteryProject/data/` 后续只保留小样例或派生数据

## 4. AI 虚拟电芯 benchmark 副本

### 目录
- `AI虚拟电芯/Exp/bench_mark/`
- `AI虚拟电芯/Exp/bench_mark2/`

### 已核验事实
- `bench_mark2/` 是较小的同名子集目录
- 抽样哈希确认：`A组_0.dat` 在两处一致

### canonical
- 优先保留 `AI虚拟电芯/Exp/bench_mark/` 作为完整源

### 处理建议
- `bench_mark2/` 先标记为待回收副本
- 在引用核对完成前不直接删除

## 5. MIC processed_curves 双格式输出

### 目录
- `MIC/数据分析/processed_curves/`

### 已核验事实
- 大量文件以相同 basename 同时存在 `.csv` 与 `.dat`

### canonical
- 后续统一收敛到 `data_processed/MIC_1175Ah/processed_curves/`

### 处理建议
- 在下轮迁移中优先保留 `.csv`
- `.dat` 先视为历史兼容输出，待 Notebook 引用核对后再回收

## 6. Notebook 副本归档

### 已执行归档
- `314/调频_10s_0.5C_25年 copy.ipynb` → `archive/old_notebooks/314/`
- `314/diff_temperature/thermal/thermal_hithium copy 2.ipynb` → `archive/old_notebooks/314/diff_temperature/thermal/`
- `314/竞品分析/314 CS01 copy.ipynb` → `archive/old_notebooks/314/竞品分析/`
- `314/竞品分析/314 CS06 copy.ipynb` → `archive/old_notebooks/314/竞品分析/`
- `MIC/宫工-徐恒-不同CW/MIC_欧盟_legacy.ipynb` → `archive/old_notebooks/MIC/宫工-徐恒-不同CW/`
- `工具/探索/Hithium_DFN_280.ipynb` → `archive/old_notebooks/工具/探索/`
- `工具/探索/Hithium_MPM_280.ipynb` → `archive/old_notebooks/工具/探索/`
- `工具/探索/Hithium_MPM_314.ipynb` → `archive/old_notebooks/工具/探索/`
- `工具/探索/hysteresis.ipynb` → `archive/old_notebooks/工具/探索/`
- `工具/探索/MIC_heat.ipynb` → `archive/old_notebooks/工具/探索/`

### 第二批归档依据
- `MIC_欧盟_legacy.ipynb` 在 `MIC/README.md` 中被显式标注为 legacy notebook
- `工具/探索/` 目录中的相关脚本已被 AGENTS.md 认定为早期原型/legacy，且以上 5 个 Notebook 无明文引用命中

### 剩余高风险候选
- 无。该批次已完成路径依赖盘点并迁移。

### 第三批整组迁移
- `MIC/宫工-徐恒-不同CW/` 剩余 Notebook 与同目录数据文件已整体迁入 `archive/old_notebooks/MIC/宫工-徐恒-不同CW/`
- 为兼容历史导入，已在新目录补 `Fun_HZ.py` 兼容入口，并补 `Fun_NC.py` 本地硬链接
- `314/可靠性对标notebook/` 已整体迁入 `studies/314Ah/notebooks/可靠性对标notebook/`
- 为兼容历史导入，已在新目录补 `model.py` 本地硬链接与 `plot.py` 兼容入口

### 处理建议
- 后续若再迁移其它 Notebook 目录，优先采用“整组目录 + 最小兼容入口”方式，避免只挪 `.ipynb` 导致相对路径整体失效