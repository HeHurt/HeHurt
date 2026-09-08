# CW501 Load Cycle 收敛跟进审计

本目录记录在将非线性容差因子改回 1、开启 BDF 非线性控制器、将 BDF 最高阶数改为 1 之后的只读跟进诊断。

- `audit_result.json`：当前保存模型的 Load Cycle 属性、扫描列表和已保存解。
- `error_report.txt`：最新失败 Case 与下一轮最小变量验证顺序。
- `metrics.csv`：最新 COMSOL 日志中的失败时刻。

源 `.mph` 没有被修改，本轮没有执行新求解。

