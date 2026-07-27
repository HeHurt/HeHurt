# 2026-07-22 Notebook 去重整理 Plan

## 基于 Spec

- `2026-07-22_notebook去重整理_spec.md`

## 步骤分解

1. [x] 冻结目标清单，创建 DLP 字节备份与哈希清单。
2. [x] Batch A：删除两组完全重复 Python 副本，保留权威路径。
3. [x] Batch B：合并 587 常规循环与 587 生命周期产热 Notebook。
4. [x] Batch C：合并 314Ah LC 专项 Notebook。
5. [x] Batch D：收敛 314Ah/MIC 峰值电流参数变体。
6. [x] Batch E：收敛 BOL thermal 与 PSD 重复实现。
7. [x] 更新 Notebook 索引和迁移报告。
8. [x] 验证保留/归档 Notebook 的 JSON、DLP、引用和 Git 状态。

## 验证标准

- 所有备份与原文件的 SHA-256 一致。
- 保留和归档的 `.ipynb` 均能由 VS Code/Node 解析，原损坏的零字节 Notebook 除外。
- canonical Notebook 的配置区覆盖原版本的电芯、倍率或时长差异。
- 不新增 Notebook 内联核心仿真函数。
- `BatteryProject/src/` 若有修改，必须通过 flake8、完整 pytest 与最小 smoke test。

## 变更记录

- 2026-07-22：用户批准执行上一轮审计中的“可以优先处理”项目。
- 2026-07-22：6 个保留入口和 19 个归档 Notebook 均通过 JSON 与 code-cell AST 校验；相关定向测试 17 项通过，峰值电流最小真实仿真通过。
