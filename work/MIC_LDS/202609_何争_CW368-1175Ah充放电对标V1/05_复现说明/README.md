# 复现说明

## 运行环境

- Python 3.10+
- PyBaMM（本次运行使用本机当前环境）
- 求解器：IDAKLUSolver，`rtol=1e-6`，`atol=1e-8`
- 网格：`x_n/x_s/x_p=5`，`r_n/r_p=20`

## 运行命令

在项目根目录执行：

```powershell
$env:PYTHONIOENCODING='utf-8'
python -c "import sys; from pathlib import Path; p=Path(r'D:\Users\hez\Desktop\hithium\work\MIC_LDS\202609_何争_CW368-1175Ah充放电对标V1\02_模型'); sys.path.insert(0,str(p)); import cw368_dfn_benchmark as b; b.run_benchmark()"
```

## 输入与输出

- `03_输入数据/`：00029和00030原始提取曲线，文件内容不做修改；脚本仅把源标签0.125/0.25映射为物理工况0.167/0.333。
- `02_模型/paramsLDSCW368.py`：1175 Ah、195.5 mm物理几何参数。
- `02_模型/cw368_dfn_benchmark.py`：恒功率求解、按容量对齐、误差统计和作图。
- `04_输出结果/20260904_100448_CW368_1175Ah_25C/plots/`：正式对标图。
- `04_输出结果/20260904_100448_CW368_1175Ah_25C/结果汇总.xlsx`：参数、功率口径、平均指标及逐曲线指标。
- 原始run位于 `BatteryProject/output/runs/cw368_1175_benchmark/20260904_100448_CW368_1175Ah_25C/`；发布清单与SHA-256见本目录 `run_manifest.json`。

## 校准/验证边界

00029标记为calibration、00030标记为validation。本次物理基线已直接满足验收标准，因此没有使用00029继续拟合参数；该标记仅固定未来若需校准时的数据边界。
