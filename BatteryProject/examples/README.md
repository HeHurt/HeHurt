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
| `循环老化.ipynb` | 常规循环老化（含原生 PyBaMM conditioning+aging 写法） | `export_cycle_metrics_report`、`compare_all` | 可选 EXP_CSV_FOLDER |
| `欧盟电池法.ipynb` | 循环老化 + 周期性 DCR 插入 + 功率/效率演化 | `run_dcr_and_power_test` | 可选 `data_raw/<型号>/data/*.dat` |
| `插入脉冲.ipynb` | 基础循环中插入客户定义功率脉冲的寿命对比 | `run_pulse_lifecycle_scenarios` | 无 |
| `调频.ipynb` | 调频（FR）秒级脉冲波形 + 等效压缩长寿命仿真 | `run_frequency_scenarios` | 无 |
| `粒径分布.ipynb` | PSD 拟合（单峰/双峰 lognormal）+ 多材料对比仿真 | `psd_workflow.*` | notebook 内贴 PSD 数据 |
| `峰值电流.ipynb` | 各 SOC 下 10s 峰值电流/功率 map | `run_peak_current` | 无 |

## 三、案例研究（特定问题的完整分析）

| Notebook | 问题 | 主要 src 入口 |
|---|---|---|
| `MIC_1175Ah_0p25P_循环老化对标.ipynb` | 原始 Excel → lifecycle .dat → 25/45°C 0.25P 仿真 vs 实测均值 | `export_cycle_life_dat`、`run_pulse_lifecycle_scenarios` |
| `EIS.ipynb` | 快速 EIS（SOC/温度扫）+ 寿命-EIS 联合研究与阻抗分解 | `pybamm.EISSimulation`、`run_lifecycle_eis_study` |
| `干涸.ipynb` | 电解液干涸耦合循环老化（Li2024 物理模型） | `DryoutTracker`、`run_aging_with_dryout` |
| `swelling_cycling_demo.ipynb` | 膨胀力-孔隙率双向耦合（路线 A），耦合开/关对照 | `SwellingCoupler`、`plot_swelling_coupling` |
| `不同循环深度的容量保持率对比.ipynb` | 10% vs 100% DOD 等 Ah 通量下的衰减对比（含满放对标机制） | `run_aging_with_dryout`、`build_power_step` |

### 脚本

| 脚本 | 用途 |
|---|---|
| `aging_identification_demo.py` | 老化参数辨识：合成数据 → 优化反演，真实数据拟合的可运行模板 |
| `mechanism_discrimination_fig4.py` | 机理判别 MVP：容量+DCR 双信号区分 SEI vs SEI+LAM（复现交底书图4） |

## 约定

- 仿真输出统一写 `BatteryProject/output/<OUTPUT_NAME>/`（已 gitignore）。
- 实验数据选择先查根目录 `datasets.json` / `src.data_registry`，再只读 `data_raw/`（原始）
  与 `data_processed/`（清洗后）；Notebook 不落地中间数据到 examples/。
- 换温度必须重建 `pybamm.ParameterValues("OKane2022")` 再 `update()`，防参数污染（见各模板写法）。
- 绘图中如存在手动校正系数，必须提升为 cell 顶部大写命名常量并注释来源，禁止内联在 `plot()` 调用里。
