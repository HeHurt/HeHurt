# Migration Notes

本文件汇总历史脚本迁移入口。详细拆解仍保留在原文档中。

## Fun_HZ

原文件：

- `工具/Fun_HZ.py`

状态：

- 已归档为 `[LEGACY]`。
- 核心能力已迁入 `BatteryProject/src/`。

详细说明：

- [FUN_HZ_MIGRATION.md](FUN_HZ_MIGRATION.md)

新代码推荐：

```python
from src.notebook import setup_notebook, load_params
from src.notebook_api import run_dcr_and_power_test, run_peak_current
```

旧 notebook 若仍使用 `from src.easy_imports import *`，可以继续运行，但新 notebook 不再推荐星号导入。

## Fun_NC

原文件：

- `MIC/宫工-徐恒-不同CW/Fun_NC.py`

状态：

- 已归档为 `[LEGACY-PARTIAL]`。
- 电解液干涸主链已迁入 `src/electrolyte_dryout.py`。
- 未迁能力清单见 [FUN_NC_TODO.md](FUN_NC_TODO.md)。

新代码推荐：

```python
from src.electrolyte_dryout import DryoutTracker, run_aging_with_dryout
```

## 迁移原则

- 新功能不要写回 legacy 文件。
- 仿真核心函数放入 `src/` 对应模块。
- notebook 顶部只保留路径、参数和任务配置。
- 长尾函数按任务精确导入，不再扩大 `easy_imports`。
- 修改 `BatteryProject/src/` 后运行：

```bash
python -m flake8 BatteryProject/src/ --max-line-length=120 --ignore=E501,W503
python -m pytest BatteryProject/tests/ -q
```
