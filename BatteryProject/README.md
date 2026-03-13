# BatteryProject

本项目已按标准 Python 工程结构拆分，核心功能从单一脚本中拆到多个模块，便于维护、复用与测试。

## 目录结构

- data/：实验数据（Excel/CSV）
- output/：图片与结果输出
- src/：源代码包
  - config.py：配置与材料参数
  - simulation.py：PyBaMM 仿真与实验工况
  - analysis.py：数据提取与指标计算
  - plotting.py：绘图与结果注入
  - utils.py：IO、Excel 解析与导出
  - data_cleaning.py：实验数据清洗/记录层提取
  - parameter_identification.py：老化参数辨识与优化
  - easy_imports.py：Notebook 快捷导入
- main.py：轻量入口（只做装配）

## 核心模块说明

- analysis.py：RRMSE 计算、容量提取、产热分量、膨胀力估算
- simulation.py：DCR 与峰值电流测试、分块循环仿真
- plotting.py：BatteryPlotter 与产热/容量注入
- utils.py：Excel 读取、数据导出、仿真结果注入
- config.py：路径/默认参数/材料参数与熵系数加载
- data_cleaning.py：曲线清洗、record layer 数据提取、实验数据配置化加载
- parameter_identification.py：loss 计算（cycle_line/cycle_line_v2/record）、目标函数构建、BO/GO/MO/DA/BH 优化

## 详细 API 目录

详见 [docs/API.md](docs/API.md)（包含函数清单、参数说明与 Notebook 简化示例）。

Fun_HZ 拆解迁移对照见 [docs/FUN_HZ_MIGRATION.md](docs/FUN_HZ_MIGRATION.md)。

## 与旧版单文件相比的改进

1. **职责清晰**：仿真、分析、绘图、IO 分离，降低耦合。
2. **可复用性强**：功能模块化，可在 Notebook/脚本自由组合。
3. **可维护性更高**：避免重复定义与冲突，修复多处重复代码残留。
4. **稳定性增强**：统一入口、统一配置，减少全局变量污染。

## 快速开始

> 在 Notebook 中推荐使用：

```python
from src.easy_imports import *
```

## Notebook 简化示例（MIC多温度拟合）

已在 docs/API.md 中提供最小替换示例，用于将重复的 Excel 解析与曲线注入逻辑替换为统一 API。
示例 Notebook：[../MIC/不同温度倍率循环/MIC多温度拟合.ipynb](../MIC/不同温度倍率循环/MIC多温度拟合.ipynb)

> 使用主入口的轻量自检：

```python
python main.py
```

## 老化参数辨识示例

已提供可直接运行的示例脚本（基于合成数据闭环验证）：

```python
python examples/aging_identification_demo.py --cycles 3 --n-iter 2 --init-points 1
```

脚本路径：`examples/aging_identification_demo.py`

说明：
- 默认先用模型生成 synthetic 实验数据，再执行 BO 参数辨识。
- 你可将 `make_synthetic_experiment_data` 替换为真实数据读取（结合 `src/data_cleaning.py`）。

## 备注

- data/ 中请放置实验数据文件
- output/ 会存放绘图与导出结果
