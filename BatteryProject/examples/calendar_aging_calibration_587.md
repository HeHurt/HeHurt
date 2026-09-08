# 587Ah日历老化敏感性与自动标定案例

## 案例用途

本案例把本次人工调参过程固定为机器可重复流程：

1. 读取并聚合实测恢复容量。
2. 校验SOC、活化方式和数据字段，协议不匹配时直接终止。
3. 对所有候选参数分别运行低值和高值OAT算例。
4. 按预测曲线响应幅度排序。
5. 自动剔除低敏感参数，以及响应相关系数绝对值不小于0.95的重复参数。
6. 最多选择3个参数，调用 `parameter_identification.run_parameter_optimization`。
7. 用30~180天数据训练，用210~300天数据留出验证。
8. 缓存每组参数的仿真结果，重复执行时不重新计算。

## 快速查看已接受案例

不运行新仿真，只把本次已接受结果整理为标准案例：

```powershell
python BatteryProject/examples/calendar_aging_calibration_587.py --mode accepted
```

输出：

```text
BatteryProject/output/runs/tabular_calibration/
└─ 20260727_587_calendar_accepted_case/
   ├─ case_manifest.json
   ├─ experiment_train_validation.csv
   ├─ calibration_comparison.csv
   ├─ sensitivity_summary.csv
   └─ calibration_config.json
```

## 从头自动标定

```powershell
python BatteryProject/examples/calendar_aging_calibration_587.py --mode full
```

完整运行会生成：

- `sensitivity_ranking.csv`
- `response_correlation.csv`
- `evaluation_log.csv`
- `best_fit_comparison.csv`
- `calibration_summary.json`
- `cache/*.csv`

## 迁移到其他电芯或实验

1. 复制JSON配置，修改实验CSV、工况、训练/验证分割和参数范围。
2. 让仿真回调返回一张表，至少包含 `case_columns` 和预测值列。
3. 实测表中使用相同 `case_columns`，一行对应一个工况。
4. 首次运行保留较宽参数范围；检查敏感性和相关性后再决定是否扩大范围。
5. 只有在单点最优和留出验证通过后，才按需调用 `uq_calibration.py` 做MCMC。

## 与原有模块的分工

- `tabular_calibration.py`：协议闸门、表格对齐、缓存、OAT筛选、共线性过滤、训练/验证和报告。
- `parameter_identification.py`：提供BO、SLSQP、dual annealing等优化算法。
- `uq_calibration.py`：在确定参数集合和合理最优点后评估后验区间与不可辨识性。
