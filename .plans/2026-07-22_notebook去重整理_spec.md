# 2026-07-22 Notebook 去重整理 Spec

## 目标

在不丢失历史工况、实验路径和 DLP 保护级别的前提下，收敛已确认的重复脚本与高相似 Notebook；每类流程保留一个 canonical Notebook，其余版本进入时间戳归档。

## 输入

- 审查报告：`docs/reviews/BatteryProject_Notebook_Review_All.md`
- 去重候选：`docs/reviews/BatteryProject_Notebook_Dedupe_and_Org.md`
- 当前工作区：`work/314Ah`、`work/587Ah`、`work/MIC_1175Ah`、`work/AI_virtual_cell`
- 公共实现：`BatteryProject/src/`

## 预期输出

- 两组完全重复 Python 脚本只保留一个权威副本。
- 587 常规循环、587 生命周期产热、LC 专项、峰值电流、BOL thermal、PSD 各自收敛到 canonical 入口。
- 被替代 Notebook 现保存在 `D:\Users\hez\Desktop\hithium-外移\cold-archive\notebook_dedupe_20260722\`，不直接永久删除。
- 新增迁移清单，记录原路径、canonical 路径、处理方式和验证结果。

## 约束

- 修改前对目标文件做字节级备份并校验 SHA-256。
- 不覆盖成功运行结果，不删除 `results/`、`outputs/` 或实验数据。
- Notebook 通过 VS Code/Node 白名单读取、写入和 JSON 解析验证。
- 每批最多修改 7 个文件；不得改动当前 worktree 中无关的用户修改。
- 本轮只做结构收敛和配置提取，不执行长周期全量仿真。
