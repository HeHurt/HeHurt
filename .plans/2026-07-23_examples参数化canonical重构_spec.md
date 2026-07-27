# Examples 参数化 Canonical 重构 Spec

## 目标

把 `BatteryProject/examples/` 收敛为“每种分析类型一个 canonical Notebook”，所有用户可变参数只从顶部 `CONFIG` cell 输入；特定电芯和任务实例迁入 `work/`，公共逻辑进入 `BatteryProject/src/`。

## 命名

- Notebook 使用中文业务名，例如 `循环老化.ipynb`、`全生命周期产热.ipynb`。
- Python 模块、函数、配置键保持英文。
- API 教学 Notebook 与 workflow canonical 分目录保存。

## 数据输入

- 原始实验文件只读保存到 `data_raw/<电芯>/<测试类型>/<工况>/`。
- `datasets.json` 只存索引和元数据，不嵌入实验数据。
- `data_registry scan` 自动登记；`curate` 命令负责人工作校准，不要求人工编辑 JSON。
- Canonical Notebook 通过结构化 query 查询数据；原始格式无法直接加载时，由预处理器生成 `data_processed/`，不覆盖原始文件。

## Canonical 契约

每个 workflow Notebook 固定为：

1. 标题和适用范围。
2. 顶部、带 `parameters` tag 的唯一 `CONFIG` cell。
3. 配置校验和数据查询。
4. 调用 headless workflow runner。
5. 保留该分析类型原有的全部结果章节、图表、实验对标、诊断和导出入口；每章改为调用公共 API。
6. 结果概览和 artifact 链接。

Notebook 不定义电芯参数函数、核心仿真函数、checkpoint、实验解析或 Excel 导出实现。

## 功能保全

- 合并前逐文件建立 feature parity 矩阵，取全部旧文件能力的并集，不以最简版本为基准。
- 只允许减少参数副本和重复实现，不允许删减分析能力、图表、导出、实验对标或诊断入口。
- 独有能力应参数化或下沉到 `src`，并在唯一 canonical 中保留分章节调用和展示。
- parity 未验证通过前，旧文件只能哈希归档，不能把该 workflow 标记为重构完成。

## 输出

- 原始运行：`BatteryProject/output/runs/<workflow>/<run_id>/`。
- 任务交付：通过 `tools/task_delivery.py publish-task` 固化到版本化任务包。
- 每个 run 至少包含 config、状态、metrics 和 artifact 清单。

## 验收

- 同一 workflow_id 只有一个 canonical Notebook。
- 所有 canonical 均有唯一顶部 `parameters` cell。
- 无绝对数据路径、无 Notebook 内 `get_hithium_params` 或核心 runner。
- 数据 query 无歧义；多匹配时显式报错或由配置允许批量。
- `flake8`、完整 `BatteryProject/tests` 通过。
- 每个 workflow 至少一个最小 smoke；合并簇关键指标与旧版本在定义容差内一致。
- feature parity 矩阵全部勾选，且 canonical 中仍可见原有业务分析章节。
