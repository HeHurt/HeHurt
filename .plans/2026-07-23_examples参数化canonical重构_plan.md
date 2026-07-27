# Examples 参数化 Canonical 重构 Plan

## 基于 Spec

`.plans/2026-07-23_examples参数化canonical重构_spec.md`

## 步骤分解

1. [x] Batch 1：补齐 registry 查询与 curate CLI，建立 canonical 配置契约。
2. [x] Batch 2：合并常规循环家族为 `循环老化.ipynb`，迁出 MIC 特定实例；保留容量/SOH、实测对标、膨胀、深度分析和产热完整章节，parity 见 `2026-07-23_循环老化_feature_parity.md`。
3. [ ] Batch 3：待 Batch 2 完成功能 parity 后，合并三份生命周期产热为 `全生命周期产热.ipynb`，抽取 workflow 与 reporting。
4. [ ] Batch 4：参数化 EIS、脉冲、调频、峰值电流、欧盟DCR和BOL热诊断。
5. [ ] Batch 5：整合 PSD 与 regional parallel；抽取干涸/膨胀/DOD 共用老化骨架。
6. [ ] Batch 6：迁移 API demo 和脚本，移动特定案例，更新 catalog/README/任务模板引用。
7. [ ] Batch 7：归档旧入口，运行静态校验、flake8、pytest和各 workflow smoke。

## 变更约束

- 每批不同时修改超过 7 个文件。
- DLP Notebook 使用 Code.exe/VS Code bridge 读写并在写回后验证 JSON。
- 旧 Notebook 通过哈希和迁移清单归档，不直接永久删除。
- 不覆盖当前 `work/` 任务实例或成功 run。

## 验证标准

- Batch 1：registry query/curate 单元测试通过。
- Batch 2-5：每个 canonical 配置矩阵和 smoke 通过。
- Batch 6：README 与 catalog 无失效路径。
- Batch 7：全套验证通过并记录未运行的长周期工况。
