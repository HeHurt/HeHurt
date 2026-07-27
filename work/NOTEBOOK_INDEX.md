# Notebook 权威入口索引

本表只登记 2026-07-22 已完成去重、并核对过差异的主题。未列出的 Notebook 不代表可删除或已废弃。

| 主题 | 权威入口 | 配置方式 | 本次处理 |
|---|---|---|---|
| 常规循环 | `BatteryProject/examples/workflows/循环老化.ipynb` | 顶部 `CONFIG` 统一配置电芯、工况、运行规模与实验数据查询 | 作为新任务模板；MIC 专用版本已固化为任务包，其他历史研究实例继续保留 |
| 全生命周期产热 | `BatteryProject/examples/workflows/全生命周期产热.ipynb` | 顶部 `CONFIG` 统一配置电芯、倍率、SOH 诊断、接触电阻和熵热校准 | 保留 314/587/MIC 历史能力，旧模板已归档到外移 cold-archive |
| 314Ah LC 非 PCS | `BatteryProject/examples/314Ah_LC_non_PCS.ipynb` | `LC_CASE_KEY` 选择 `base_1p1_non_pcs`、`two_1_non_pcs` 或 `safety` | 三个有效方案合并；内容错配的 `314 fake.ipynb` 只归档、不并入参数表 |
| 峰值电流 | `BatteryProject/examples/峰值电流.ipynb` | `CASE_KEY` 选择 314 5+3 或 MIC CW363/CW500/CW600 的时长方案 | 8 个参数变体收敛到已有示例入口 |
| 阻抗分析 | `BatteryProject/examples/workflows/阻抗分析.ipynb` | 顶部 `CONFIG` 统一配置快速 EIS、SOC/温度扫描和寿命-EIS | EIS 保持独立 workflow，不与脉冲或调频合并 |
| 插入脉冲 | `BatteryProject/examples/workflows/插入脉冲.ipynb` | 顶部 `CONFIG` 统一配置基础循环、脉冲场景、容量校正和数据查询 | 保留插入脉冲能力，独立于调频 workflow |
| 调频 | `BatteryProject/examples/workflows/调频.ipynb` | 顶部 `CONFIG` 统一配置 FR 波形、RPT、summary 和实验数据查询 | 保留调频能力，独立于插入脉冲 workflow |
| 粒径分布 | `BatteryProject/examples/workflows/粒径分布.ipynb` | 顶部 `CONFIG` 统一配置 PSD 拟合、材料对比、仿真和 COMSOL histogram 输出 | 合并 `PSD_to_COMSOL` 的转换能力，PSD 独立于耦合老化 |
| 区域并联耦合老化 | `BatteryProject/examples/workflows/区域并联耦合老化.ipynb` | 顶部 `CONFIG` 统一配置 OCV+R、区域 DFN、孔隙率、生命周期和负极电位诊断 | 区域并联/耦合老化保持独立 workflow |

## 归档与恢复

- 2026-07-22 去重批次保存在 `D:\Users\hez\Desktop\hithium-外移\cold-archive\notebook_dedupe_20260722\`，内部保留原相对目录。
- 2026-07-23 workflow canonical 批次保存在 `D:\Users\hez\Desktop\hithium-外移\cold-archive\examples-canonical-20260723\workflow-family\`，含 `manifest.json`。
- 操作前字节备份和 SHA-256 清单位于 `.codex_scratch/backups/notebook_dedupe_20260722/`；该目录用于本机恢复，不作为项目正式入口。
- `tools/0_preprocess_data.py` 与 `archive/old_notebooks/MIC/宫工-徐恒-不同CW/Fun_NC.py` 是完全重复副本，已删除；保留版本分别是 `tools/0_preprocess_data_power.py` 和 `archive/legacy_scripts/MIC/宫工-徐恒-不同CW/Fun_NC.py`。

## 使用规则

1. 本索引中的 canonical Notebook 是模板入口；单次任务先用 `tools/task_delivery.py new-task --template ...`
   复制到 `work/<cell>/<YYYYMM_何争_任务名称Vn>/02_模型/`，不要直接修改模板。
2. 新增同流程的电芯、倍率或时长时，优先扩展 canonical Notebook 顶部配置，不再创建新的模板副本。
3. 新分析类型才新增 canonical Notebook，并在验证后补充本索引。
4. 原始 run 写 `BatteryProject/output/runs/`，确认结果通过 `publish-task` 固化到任务包。
5. 归档文件只用于追溯，不继续增加功能。
