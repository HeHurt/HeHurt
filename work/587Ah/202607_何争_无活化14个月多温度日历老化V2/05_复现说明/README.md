# 复现说明(V2, 27% SOC)

## 环境

- 工作区：`C:\HithiumSSD\hithium`
- Python：3.11
- PyBaMM：26.4.2
- 参数：`params/params587calander.py`（registry 别名：`587calander`，标定后 SEI 主导参数）
- SEI 生长活化能：39000 J/mol（2026-08-07 由 40000 微调，45°C 对标 RMSE 0.714→0.707 pp）
- 老化加速因子：1

## 与 V1 的差异

- **存储 SOC：50% → 27%**（V2 主题差异）
- SEI 生长活化能：40000 → 39000 J/mol（对 25°C 无影响，45°C 对标微改善）
- 其余工况（温度、月份、检测倍率、电压窗口、期末 25°C 测试）与 V1 完全一致

## Smoke

```powershell
python "work\587Ah\202607_何争_无活化14个月多温度日历老化V2\02_模型\calendar_aging_587_matrix_27soc.py" `
  --mode smoke --run-id "<新的smoke run id>"
```

smoke 计算 0、25、50°C 各 1 个月，共 3 个独立算例。

## 全量计算

```powershell
python "work\587Ah\202607_何争_无活化14个月多温度日历老化V2\02_模型\calendar_aging_587_matrix_27soc.py" `
  --mode full --run-id "<新的full run id>"
```

全量计算 11 个温度 × 14 个月，共 154 个独立算例。每完成一个算例，脚本都会更新：

- `artifacts/calendar_aging_587Ah_27SOC_matrix.csv`
- `artifacts/run_status.csv`

流程：25°C 0.5P 充放得到 C0 → 精确充入 0.27×C0 → 27% SOC 静置 30–420 天 →
回 25°C 静置 1h → 保持容量放电（分母 0.27×C0）→ 恢复容量充放电（分母 C0）。

## 关键文件

- 矩阵脚本：`02_模型/calendar_aging_587_matrix_27soc.py`（由 V1 脚本参数化 SOC 得到）
- 共享 workflow：`BatteryProject/src/workflows/calendar_aging_half_soc.py`（2026-08-07 参数化
  `storage_soc_pct`，默认 50.0 兼容 V1；备份 `calendar_aging_half_soc.py.bak_20260807`）
- 参数文件：`params/params587calander.py`（Ea=39000）
