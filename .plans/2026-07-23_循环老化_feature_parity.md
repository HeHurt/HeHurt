# 循环老化 Canonical Feature Parity

基准：原 `examples/循环老化.ipynb` 17 个单元。新入口：
`BatteryProject/examples/workflows/循环老化.ipynb`。

| 原能力 | 新位置 | 公共实现 | 验证 |
|---|---|---|---|
| 电芯、温度、倍率、循环规模配置 | 顶部唯一 `CONFIG` | `CycleWorkflowSpec` | spec 单测通过 |
| conditioning + aging 主循环 | 第 3 章 | `run_cycle_workflow` / `run_pulse_lifecycle_scenarios` | 587Ah 单工况 smoke 通过 |
| 容量/SOH 指标与 Excel | 第 4 章 | `export_cycle_metrics_report` | smoke 导出通过 |
| Sim vs Exp 容量/效率/膨胀对标 | 第 5 章 | `compare_all` | lifecycle dat 与 cycling folder registry loader 单测通过 |
| 独立膨胀/力对标 | 第 6 章 | `compare_swelling` | 入口保留；真实力数据工况未在 smoke 运行 |
| 效率与逐工况深度分析 | 第 7 章 | `plot_efficiency_vs_cycle` / `plot_analysis` | smoke 通过 |
| 充放电热分解 | 第 8 章 | `process_sol_list_for_all_heat_components` | smoke 通过 |
| 标准 run 与 artifact 目录 | 第 3-4 章 | `create_run_context` | config、metrics、Excel 已生成 |

## 结论

功能入口已按旧版能力并集保留，Notebook 内不再定义核心函数。长周期 study、真实实验对标和
含力信号的膨胀对标属于数据/算力工况，保留入口但不纳入最小 smoke。
