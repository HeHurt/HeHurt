# Notebook 工作区 Harness (MIC / 314 / 280 / 587 通用)

## 这个区域是什么
Jupyter Notebook 是仿真的最终执行环境。每个 Notebook 完成一项具体的仿真或对标任务。

## Notebook 初始化模板（第一个单元格）
```python
%load_ext autoreload
%autoreload 2
import importlib
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pybamm

PROJECT_ROOT = Path(r"D:\Users\hez\Desktop\hithium\BatteryProject")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
PARAMS_ROOT = Path(r"D:\Users\hez\Desktop\hithium\params")
if str(PARAMS_ROOT) not in sys.path:
    sys.path.append(str(PARAMS_ROOT))

# 选择对应电芯的参数模块
import src.simulation as simulation_module
import paramsMIC as params_module  # ← 按电芯改

importlib.reload(simulation_module)
importlib.reload(params_module)

run_peak_current = simulation_module.run_peak_current
get_hithium_params = params_module.get_hithium_params

plt.style.use("science")
plt.rcParams["font.family"] = "Calibri, Microsoft YaHei"
```

## 模块刷新规则（极重要）
修改 `BatteryProject/src/` 代码后，在 Notebook 中**必须**：
1. `importlib.reload(simulation_module)`
2. 重新绑定函数：`run_peak_current = simulation_module.run_peak_current`

**症状**：Notebook 重跑后行为未变化 → 99% 是函数对象还绑到旧模块实现。

## 标准模型配置（第二个单元格）
```python
model = pybamm.lithium_ion.DFN({
    "calculate discharge energy": "true",
    "contact resistance": "true",
    "open-circuit potential": ("current sigmoid", "current sigmoid"),
})
var_pts = {"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}
solver = pybamm.IDAKLUSolver()
```

## 作图规范
- 使用 `plt.style.use("science")`
- 实验数据用虚线 `ls='--'`，仿真数据用实线 `ls='-'`
- 同一物理量的实验 vs 仿真用相同颜色
- 图标题使用英文
- 图例标注: `{倍率/温度} Exp` / `{倍率/温度} Sim`

## Excel 导出规范
- 使用 `openpyxl` 引擎
- 色阶条件格式: 绿(`63BE7B`) → 黄(`FFEB84`) → 红(`F8696B`)
- 居中对齐、薄边框、标题行灰色填充
- 冻结窗格: 通常 `'B3'`

## 禁止事项
- 不得在 Notebook 单元格中定义仿真核心函数 — 放到 `src/` 模块中
- 不得在不同温度计算之间复用同一个 `params` 对象
- 不得硬编码绝对路径在函数参数里（路径放在 Notebook 顶部常量中）
