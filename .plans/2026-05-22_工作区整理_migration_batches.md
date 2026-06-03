# 2026-05-22 工作区整理 Migration Batches

## Batch A: 587 原始 Excel
- 从 `587/Exp/欧盟电池法仿真数据/` 迁入 `data_raw/587Ah/`
- `BatteryProject/data/` 改为仅保留样例或处理后数据
- 验证: Notebook 与脚本不再依赖旧路径

## Batch B: 314 benchmark_rate
- 合并 `314/可靠性对标notebook/Rate/` 与 `工具/探索/Rate/`
- 目标目录: `data_raw/314Ah/benchmark_rate/`
- 验证: 电压、温度、电流文件集合完整

## Batch C: study-local params 快照
- 盘点 `314/*/params/` 与 `工具/探索/params/` 对 `params/` 的引用关系
- 仅将与 `params/` 哈希完全一致的材料曲线统一到 canonical
- 当前已完成: `314/diff_rate/params/` 中 `E_DL_int1.csv`、`E_sigma.csv`、`E_transpNm.csv`、`Gr_charge.csv`、`LFP.csv` 改为硬链接
- 当前保留: `Gr_discharge.csv` 及其它 study-local params 快照，原因是内容分叉
- 验证: 本地相对路径不变，且一致文件已实现单源存储

## Batch D: MIC processed_curves
- 将 `MIC/数据分析/processed_curves/` 迁入 `data_processed/MIC_1175Ah/processed_curves/`
- 首选保留 `.csv`，`.dat` 暂缓删除
- 验证: 至少抽查 2 个 Notebook 的数据读取路径

## Batch E: Notebook 归档
- 受保护 Notebook 不做清输出
- 除 `BatteryProject/examples/` 外，其余按电芯与任务迁入 `studies/*/notebooks/` 或 `archive/old_notebooks/`
- 当前已完成: 4 个 `copy` Notebook 迁入 `archive/old_notebooks/314/` 对应子目录
- 当前已完成: `MIC/宫工-徐恒-不同CW/MIC_欧盟_legacy.ipynb` 迁入 `archive/old_notebooks/MIC/宫工-徐恒-不同CW/`
- 当前已完成: `工具/探索/` 下 5 个探索型 Notebook 迁入 `archive/old_notebooks/工具/探索/`
- 当前已完成: `MIC/宫工-徐恒-不同CW/` 剩余 Notebook 与同目录数据整体迁入 `archive/old_notebooks/MIC/宫工-徐恒-不同CW/`
- 当前已完成: `314/可靠性对标notebook/` 整体迁入 `studies/314Ah/notebooks/可靠性对标notebook/`
- 当前已完成: 为上述两组补最小兼容入口，包含 `Fun_HZ.py`、`Fun_NC.py`、`model.py`、`plot.py`
- 后续批次: 若继续迁移其它 Notebook 目录，优先先盘点相对路径，再整组移动
- 验证: 仅移动文件，不修改 notebook 内容

## Batch F: 顶层目录收口
- 已将 `280/`、`314/`、`587/`、`MIC/`、`AI虚拟电芯/` 的剩余内容分流到 `data_raw/`、`data_processed/`、`studies/`、`archive/`
- 已将 `工具/` 分流为 `tools/`、`archive/old_notebooks/工具/`、`archive/oneoff_tools/工具/`
- 已将 `account/` 与 `算例/` 收入 `archive/oneoff_tools/`
- 已删除迁空后的旧顶层目录
- 顶层保留 `COMSOL/` 作为独立活跃域