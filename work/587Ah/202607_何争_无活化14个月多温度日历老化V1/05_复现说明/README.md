# 复现说明

## 环境

- 工作区：`C:\HithiumSSD\hithium`
- Python：3.11
- PyBaMM：26.4.2
- 参数：`params/params587calander.py`（registry别名：`587calander`）
- 老化加速因子：1

## Smoke

在工作区根目录执行：

```powershell
python "work\587Ah\202607_何争_无活化14个月多温度日历老化V1\02_模型\calendar_aging_587_matrix.py" `
  --mode smoke `
  --run-id "<新的smoke run id>"
```

smoke计算0、25、50°C各1个月，共3个独立算例。

本次验证run：`20260727_587calander_50SOC_smoke_v1_retry1`。

## 全量计算

```powershell
python "work\587Ah\202607_何争_无活化14个月多温度日历老化V1\02_模型\calendar_aging_587_matrix.py" `
  --mode full `
  --run-id "<新的full run id>"
```

全量计算11个温度×14个月，共154个独立算例。每完成一个算例，脚本都会更新：

- `artifacts/calendar_aging_587Ah_50SOC_matrix.csv`
- `artifacts/run_status.csv`

每次全量计算会先在25°C完成一次0.5P充放电得到公共基准容量C0，并精确充入
`0.5×C0`后作为所有算例的50% SOC初始状态。存储期结束后切换至25°C，静置1h，
再依次完成保持容量放电和恢复容量充放电测试。

本次正式run：`20260727_587calander_50SOC_full_v1`。

若同名算例已有完整metrics，脚本会直接复用；若只有失败的半成品run，则自动创建 `_retryN` 新run，不覆盖旧记录。

## 参数敏感性与实测标定

快速整理已接受案例，不重新仿真：

```powershell
python BatteryProject/examples/calendar_aging_calibration_587.py --mode accepted
```

从实测数据开始，运行协议校验、OAT敏感性、共线性过滤、自动优化和留出验证：

```powershell
python BatteryProject/examples/calendar_aging_calibration_587.py --mode full
```

详细说明：

`BatteryProject/examples/calendar_aging_calibration_587.md`

## Notebook

也可以打开 `02_模型/587Ah_0至50C_无活化14个月日历老化.ipynb`：

1. 先设置 `RUN_MODE = "smoke"`验证环境。
2. 再改为 `RUN_MODE = "full"`。
3. 需要续跑时，把 `RUN_ID`设置为原batch id。

## 验证命令

```powershell
python -m flake8 BatteryProject/src/ --max-line-length=120 --ignore=E501,W503
python -m pytest BatteryProject/tests/ -q
```
