# CW501 Load Cycle 扫描收敛诊断 2

本目录是对源模型的只读诊断记录。没有修改或保存源 `.mph`，也没有执行新的生产求解。

主要产物：

- `audit_solver_result.json` / `audit_sweep_result.json`：已保存模型的求解器和扫描审计。
- `solver_node_properties.json`：完整求解器子节点、Load Cycle 和 Events 属性。
- `error_report.txt`：原因判断与最小受控修复顺序。
- `metrics.csv`：多次失败时刻的 `t*C` 归一化对比。

