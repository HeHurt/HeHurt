# examples/ 索引

按用途分三类。所有 Notebook 从仓库任意位置启动均可运行（首个代码 cell 自动向上定位
BatteryProject 根目录并调用 `configure_notebook_environment`，把 `src/` 与 `params/`
加入 `sys.path`）。长耗时模板均提供 `RUN_MODE = "smoke" | "study"` 或 `QUICK_DEMO`
开关，先跑 smoke 再放大。

## 一、模块使用 Demo（学 src API，分钟级，无外部数据）

| Notebook | 演示内容 |
|---|---|
| `exp_loader_demo.ipynb` | `src.exp_loader` / `src.data_cleaning`：CSV 加载、文件名解析温度倍率、中英文列名对齐 |
| `analysis_demo.ipynb` | `src.analysis` 5 个核心函数：`calc_rrmse`、`get_discharge_capacity`、热分解等 |
| `plotting_demo.ipynb` | `BatteryPlotter`：注入数据、Sim/Exp 对比图、关键词筛选、共享颜色 |
| `compare_demo.ipynb` | `compare_all` 一站式对标：温度+倍率模糊匹配，retention/efficiency/swelling 三图 |

## 二、可复用工况模板（改配置 cell 即可复用到 280/314/587/MIC）

| Notebook | 工况 | 主要 src 入口 | 数据依赖 |
|---|---|---|---|
| `workflows/循环老化.ipynb` | 常规循环老化；电芯、温度、倍率、循环数及实验数据查询均由顶部 `CONFIG` 驱动 | `src.workflows.cycle.run_cycle_workflow` | 可选 `datasets.json` 查询 |
| `workflows/日历老化.ipynb` | 日历存储老化；支持每月容量检查的 activated 模式，以及 1、2、3……20 年独立终点算例叠加的 unactivated 模式 | `src.workflows.calendar_aging.run_calendar_aging_workflow` | 无 |
| `workflows/全生命周期产热.ipynb` | 全生命周期 SOH 诊断产热；电芯、倍率、接触电阻、熵热校准和外推均由顶部 `CONFIG` 驱动 | `src.workflows.lifecycle_heat.run_lifecycle_heat_workflow` | 可选熵热系数/实验 registry |
| `欧盟电池法.ipynb` | 循环老化 + 周期性 DCR 插入 + 功率/效率演化 | `run_dcr_and_power_test` | 可选 `data_raw/<型号>/data/*.dat` |
| `workflows/阻抗分析.ipynb` | 快速 EIS、SOC/温度扫、寿命-EIS 联合研究和阻抗分解 | `src.workflows.eis.run_eis_workflow` | 可选 `datasets.json` 查询 |
| `workflows/插入脉冲.ipynb` | 基础循环中插入客户定义功率脉冲的寿命对比 | `src.workflows.pulse.run_pulse_workflow` | 可选 `datasets.json` 查询 |
| `workflows/调频.ipynb` | 调频（FR）秒级脉冲波形 + 等效压缩长寿命仿真 | `src.workflows.frequency.run_frequency_workflow` | 可选 `datasets.json` 查询 |
| `workflows/粒径分布.ipynb` | PSD 拟合、材料对比仿真、COMSOL histogram/Java snippet 转换 | `src.workflows.psd.run_psd_workflow` | 可选 `datasets.json` 查询或 cell 内数据 |
| `workflows/区域并联耦合老化.ipynb` | OCV+R、区域 DFN、孔隙率、生命周期与负极电位诊断 | `src.workflows.regional_coupled_aging.run_regional_coupled_aging_workflow` | 可选 `datasets.json` 查询 |
| `峰值电流.ipynb` | 314 5+3 与 MIC CW363/CW500/CW600 的多时长峰值电流/功率 map | `run_peak_current` | 无 |

## 三、案例研究（特定问题的完整分析）

| Notebook | 问题 | 主要 src 入口 |
|---|---|---|
| `work/MIC_1175Ah/202607_何争_0p25P循环老化对标历史实例V1/02_模型/MIC_1175Ah_0p25P_循环老化对标.ipynb` | 已固化的历史任务实例，不作为新任务模板 | `export_cycle_life_dat`、`run_pulse_lifecycle_scenarios` |
| `干涸.ipynb` | 电解液干涸耦合循环老化（Li2024 物理模型） | `DryoutTracker`、`run_aging_with_dryout` |
| `swelling_cycling_demo.ipynb` | 膨胀力-孔隙率双向耦合（路线 A），耦合开/关对照 | `SwellingCoupler`、`plot_swelling_coupling` |
| `不同循环深度的容量保持率对比.ipynb` | 10% vs 100% DOD 等 Ah 通量下的衰减对比（含满放对标机制） | `run_aging_with_dryout`、`build_power_step` |
| `314Ah_LC_non_PCS.ipynb` | 314Ah 1+1、2+1 和安全方案 LC 非 PCS 对比 | PyBaMM DFN 与参数方案配置 |

### 脚本

| 脚本 | 用途 |
|---|---|
| `aging_identification_demo.py` | 老化参数辨识：合成数据 → 优化反演，真实数据拟合的可运行模板 |
| `mechanism_discrimination_fig4.py` | 机理判别 MVP：容量+DCR 双信号区分 SEI vs SEI+LAM（复现交底书图4） |

## 实验数据登记

`datasets.json` 是索引，不存放实验数据本体，也不应手工编辑。默认流程：

```powershell
# 1. 原始文件原样放入 data_raw；文件夹名尽量包含电芯、测试类型和工况
New-Item -ItemType Directory -Force "data_raw/587Ah/循环/25C_0.25P"
Copy-Item "<原始文件.xlsx>" "data_raw/587Ah/循环/25C_0.25P/"

# 2. 自动扫描并登记
python BatteryProject/src/data_registry.py scan

# 3. 查询检查
python BatteryProject/src/data_registry.py ls --cell 587Ah --temp 25 --rate 0.25P --test 循环

# 4. 自动推断不完整时再人工校准元数据，不改 JSON
python BatteryProject/src/data_registry.py curate --id <数据ID> `
  --cell 587Ah --temp 25 --rate 0.25P --test 循环 `
  --signals voltage,current,capacity --source "实验室原始导出" --quality checked
```

登记不要求预先清洗。标准 CSV/XLSX 由 workflow loader 直接读取；只有多行表头、特殊设备格式或
需要聚合的文件才自动转换到 `data_processed/`。转换结果重新登记，`data_raw/` 原文件始终只读保留。

## 从模板开始新任务

`examples/` 是 canonical 模板区，不直接针对单次任务修改。先创建任务包并复制模板：

```powershell
python tools/task_delivery.py new-task `
  --cell 587Ah `
  --name "全生命周期产热0p5P" `
  --template "BatteryProject/examples/workflows/全生命周期产热.ipynb"
```

此后只修改 `work/<cell>/<YYYYMM_何争_任务名称Vn>/02_模型/` 中的任务副本。完整流程见
`docs/TASK_DELIVERY_WORKFLOW.md`。

## 约定

- 新仿真输出统一写 `BatteryProject/output/runs/<workflow>/<run_id>/`（已 gitignore），验证后使用
  `publish-task` 固化到任务包；不要在 Notebook 旁边新建 `output/`。
- 实验数据选择先查根目录 `datasets.json` / `src.data_registry`，再只读 `data_raw/`（原始）
  与 `data_processed/`（清洗后）；Notebook 不落地中间数据到 examples/。
- 换温度必须重建 `pybamm.ParameterValues("OKane2022")` 再 `update()`，防参数污染（见各模板写法）。
- 绘图中如存在手动校正系数，必须提升为 cell 顶部大写命名常量并注释来源，禁止内联在 `plot()` 调用里。
- 被 `workflows/` canonical 取代的旧模板已归档到
  `D:\Users\hez\Desktop\hithium-外移\cold-archive\examples-canonical-20260723\workflow-family\`。
