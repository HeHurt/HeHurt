# 复现说明

## 模型与脚本

- `02_模型/paramsLDSCW368.py`：CW368-1300Ah、213.5 mm几何参数。
- `02_模型/cw368_1300_multirate.py`：10个恒功率DFN算例、结果汇总及三张图的生成入口。

## 运行命令

```powershell
$env:PYTHONIOENCODING='utf-8'
python "D:\Users\hez\Desktop\hithium\work\MIC_LDS\202609_何争_CW368-1300Ah多倍率容量电压与能效V1\02_模型\cw368_1300_multirate.py"
```

## 计算设置

- 求解器：IDAKLUSolver，`rtol=1e-6`，`atol=1e-8`。
- 网格：`x_n/x_s/x_p=5`，`r_n/r_p=20`。
- 输出周期：30 s。
- 每个工况重新建立 `ParameterValues("OKane2022")` 并加载CW368参数，避免参数污染。

## 结果位置

- 原始run：`BatteryProject/output/runs/cw368_1300_multirate/20260904_144254_CW368_1300Ah_25C_multirate/`。
- 正式发布结果：`04_输出结果/20260904_144254_CW368_1300Ah_25C_multirate/`。
- 发布文件及SHA-256见 `run_manifest.json`。
