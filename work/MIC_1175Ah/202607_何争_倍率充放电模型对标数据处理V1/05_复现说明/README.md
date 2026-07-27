# 复现说明

## 运行入口

```powershell
.\02_模型\extract_rate_curves.ps1 `
  -InputPaths @("<电芯29原始xlsx>", "<电芯30原始xlsx>") `
  -OutputDir "<新的运行目录>"
```

原始工作簿受 DLP 保护，脚本通过本机 Excel 只读接口提取；不会修改源文件。

## 输出文件

- `rate_summary.csv/json`：每个充放电工步的容量、能量、电压及质量检查汇总。
- `charge_curves_long.csv/jsonl`：充电曲线长表。
- `discharge_curves_long.csv/jsonl`：放电曲线长表。
- `MIC1175Ah_倍率充放电模型对标数据.xlsx`：汇总与两类曲线的可视化工作簿。

## 模型对标筛选

主倍率对标默认筛选：

```python
df = df[df["segment_role"].eq("main")]
```

推荐使用 `capacity_Ah` 或 `elapsed_time_s` 作为横坐标，`voltage_V` 作为纵坐标；按 `cell_id`、`rate_label`、`cycle_index`、`step_index` 分组。
