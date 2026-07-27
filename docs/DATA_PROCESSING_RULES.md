# Hithium 实验数据处理与模型对标规则（AI 自动处理规范）

> 用途：把"原始实验数据 → 登记 → 清洗 → 提取 → 仿真对标校验"的全链路规则固化为一份
> 可机器消费的规范。目标符合项目北极星：**AI 可调用（headless 入口）、可校验（机器可判验收）、
> 可检索（registry 而非散落文件）**。
> 后续让 AI 处理数据或编写自动处理脚本时，直接把本文档作为上下文喂给 AI 即可。
> 真源来自 `BatteryProject/src/{data_registry,exp_loader,data_cleaning,compare,analysis}.py`、
> `params/AGENTS.md`、根 `AGENTS.md` 与 `.plans/` 规约。

---

## 0. 适用范围

覆盖以下环节的硬性规则：

1. 原始实验数据落盘（data_raw）与登记（datasets.json）
2. 清洗/派生（data_processed）
3. 加载与提取供仿真对标（exp_loader / data_cleaning）
4. 仿真-实验对标校验（compare / analysis，指标含 RRMSE）
5. 电芯参数关联（params）

不涉及：COMSOL/MATLAB 闭环、Studio 前端、任务交付包（见根 AGENTS.md 对应章节）。

---

## 1. 数据分层与落点（Storage Tiers）—— 禁止合并三层

| 目录 | 角色 | 规则 |
|------|------|------|
| `data_raw/<电芯>/<测试类型>/<工况>/` | 原始只读真源 | 不可逆；csv/xlsx/xls/xlsm/dat/txt/parquet 才登记；**不覆盖原始** |
| `data_processed/<电芯>/` | 清洗/派生结果 | 原始格式无法直接加载时由预处理器生成；**绝不回写原始文件** |
| `work/<电芯>/` | 任务交付区 | 命名 `YYYYMM_何争_任务名称Vn`；首版必须 V1 |
| `archive/` | 旧物归档 | 不再用的 notebook/脚本整体迁入，不删 |
| `runs/`、`output/` | COMSOL/仿真运行 | 带时间戳子目录，不覆盖 baseline |

- 三层语义不同，**不要合并 data_raw / data_processed / work**——`data_registry`、`datasets.json`、`exp_loader` 都按路径名依赖。
- 原始实验文件只读保存到 `data_raw/<电芯>/<测试类型>/<工况>/`（见 `.plans/2026-07-23_examples参数化canonical重构_spec.md`）。
- `datasets.json` 只存索引与元数据，**不嵌入实验数据**。

---

## 2. 数据登记（Registry）—— 先查 registry，别翻 data_raw 猜文件名

入口：`python BatteryProject/src/data_registry.py <scan|ls|curate|summary>`（仓库根目录执行）。

### 2.1 条目字段（datasets.json 每条）

`id`(sha1(path)[:10])、`path`(相对根、posix)、`cell`、`kind`(raw|processed)、`format`、
`size_bytes`、`mtime`、`group`、`temperature_C`、`rate`、`test_type`、`soh_pct`、`sample_id`、
`signals`、`source`、`quality`、`notes`、`status`。

### 2.2 机器推断规则（build_entry，正则）

- 推断顺序：**文件名优先，其次由深到浅的目录名**。
- 温度 `infer_temperature`：
  - 强模式 `-?\d+(?:\.\d+)?\s*(℃|°\s*C|度)`
  - 弱模式 `(?<![\d.pP])(-?\d{1,3})\s*C(?![A-Za-z0-9])`，且值须在 **-40~80** 才采纳
- 倍率 `infer_rate`：
  - compact `(\d+)p(\d+)P` → `"X.Y P"`（如 `0p25P`→`0.25P`）
  - `(\d+(?:\.\d+)?)\s*([CD]?P)` → `"X P"` / `"X C"`
  - `(\d+\.\d+)\s*C` → `"X C"`
- 测试类型 `infer_test_type`（关键词优先级，对 relpath 小写全文匹配）：
  倍率充电 > 倍率放电 > cycle life/cycling/循环/cycle > dcr > mapping/脉冲/pulse > ocv > eis > 能效 > 日历/存储 > 容量 > 倍率
- SOH `infer_soh`：`SOH\s*(\d+(?:\.\d+)?)\s*%`
- 样本号 `infer_sample_id`：`No\.?\s*(\d+)\s*#` → `No<数字>#`

### 2.3 status 生命周期（scan 合并规则）

- `auto`：机器推断；重扫会按当前规则**重推**工况字段。
- `curated`：人工核实；重扫**只刷新 size/mtime**，工况字段与人工字段（signals/source/quality/notes）**永远保留不覆盖**。
- `ignore`：无效/垃圾文件；保留条目，不删。
- `missing`：文件已消失；保留人工信息不丢。
- 人工字段 `MANUAL_FIELDS = (signals, source, quality, notes)` 在重扫时始终保留。

### 2.4 操作命令

- 登记/更新：`python BatteryProject/src/data_registry.py scan`（新数据放入 data_raw 后必须跑一次）
- 查询：`... ls --cell MIC --temp 25 --test 倍率充电`（支持 --cell/--temp/--rate/--test/--kind/--format/--status/--path）
- 校准：`... curate --id <id>|--path <path> --temp 25 --rate 0.5P --test 循环 --status curated --signals voltage,current --quality good`
  - **用 curate 改，不要手改 datasets.json**；允许字段：cell/temperature_C/rate/test_type/soh_pct/sample_id/signals/source/quality/notes/status
- 概览：`... summary`（按电芯×测试类型计数 + 温度识别率）
- 程序内查询：`query_datasets(cell=, temp=, rate=, test=, kind=, fmt=, status=, path_contains=, require_unique=, include_inactive=)`

### 2.5 健壮性

- `datasets.json`：UTF-8、按 `path` 排序、`ensure_ascii=False`、原子写（先写 `.tmp` 再 `os.replace`）。
- 损坏时自动备份为 `.corrupt.<时间戳>` 并重建空 registry，不连锁崩溃。
- git 跟踪；`.gitattributes` 配 `dlp` clean filter 存明文（详见根 AGENTS.md「共享基础设施」）。

---

## 3. 原始数据加载（exp_loader）

入口函数（优先用这些，不要自己写解析）：

- `load_cycling_csv(path, channel=0, label=None, encoding="utf-8-sig")` → 统一 dict
- `load_cycling_folder(folder, pattern="*.csv", channel=0, sort_by="label")` → `list[dict]`
- `load_cycling_csv_from_peak(path, reset_cycle=True)` → 以放电容量峰值作 BOL 的对标友好格式
- 解析标签：`parse_condition_from_filename`（支持 `25℃-0.5P.csv`、`45°C_1P.csv`、`0.25P_25C.csv`）

### 3.1 标准列键（COLUMN_ALIASES，按优先级别名映射）

| 标准键 | 候选列名（中英，按优先级） |
|--------|---------------------------|
| `cycle` | 循环圈数 / Cycle Index / Cycle / cycle / Cyc# / 圈数 |
| `discharge_capacity` | 放电容量(Ah) / 放电容量 / Discharge Capacity(Ah) / Discharge Capacity / DChg_C(Ah) |
| `charge_capacity` | 充电容量(Ah) / 充电容量 / Charge Capacity(Ah) / Charge Capacity / Chg_C(Ah) |
| `retention` | 容量保持率 / Capacity Retention / Retention |
| `efficiency` | 能量效率 / Energy Efficiency / Efficiency / 能效 |
| `max_force` | 最大膨胀力 / Max Force / Max Swelling Force |
| `min_force` | 最小膨胀力 / Min Force / Min Swelling Force |
| `discharge_energy` | 放电能量(Wh) / 放电能量 / Discharge Energy(Wh) |
| `charge_energy` | 充电能量(Wh) / 充电能量 / Charge Energy(Wh) |
| `temperature` | 放电最大温度T1(℃) / Temperature / Temp(℃) / T1(℃) |

- 多通道：pandas 自动加 `.1/.2` 后缀；用 `channel` 参数选组（0→无后缀）。
- `retention` 特殊处理：多列时优先 `.1`；**均值 > 2 视为百分制，统一除以 100 到 0–1 小数**（`normalize_retention_scale`）。
- 以 `cycle` 列为基准去除 NaN 行（各数组同步截断）。

### 3.2 BOL 对齐（对标必用）

`load_cycling_csv_from_peak`：
- 以放电容量**首次达到最大值**的位置为寿命起点（BOL），删除前期爬坡圈；
- `retention` 以峰值容量重归一（BOL 处 = 1.0），覆盖设备自带保持率列；
- `reset_cycle=True` 时把 BOL 圈号平移到 0；
- 附加 `q_bol`（峰值放电容量 Ah）。

---

## 4. 清洗（data_cleaning）

- `clean_xy_curve(x, y, sort_by_x=True, drop_duplicates=True, smooth_window=None, smooth_polyorder=2)`：
  转数值 → 去无效（x,y 均有限）→ 可选按 x 去重(keep last) → 可选按 x 排序 → 可选 Savitzky-Golay 平滑（window 取奇数且 ≥5，否则跳过）。
- `load_curve_file(path, x_col=0, y_col=1, sep=None, header=None, smooth_window=None)`：
  txt/csv/dat 两列曲线；`sep` 默认 csv 用逗号、否则 `\s+`（engine="python"）。
- `load_record_layer_csv(path, cycle_col="cycle", t_col="t", v_col="V")`：
  按 cycle 分组返回 `[[t, v], ...]`，每组 t 平移到 0。
- `load_experiment_data(spec_dict)`：从配置 dict 加载，支持三种形态：
  - 字符串路径 → `[x, y]` 线曲线
  - dict 含 `line`/`cycle_line`/`cycle_line_v2` → `[x, y]`
  - dict 含 `record` → `[[t, v], ...]`

---

## 5. 指标与仿真-实验对标校验（analysis + compare）

### 5.1 关键指标（analysis）

- `get_discharge_capacity(sol)` → 每圈放电容量（Ah），累计每圈内放电步容量绝对增量。
- `retention_from_capacity(caps)` → `caps / caps[0]`，保持率 0–1（首圈为 0 则返回全 0）。
- `compute_cycle_energies(sol)` → 每圈 `efficiency`、cycle_index 等。
- `calculate_cycle_swelling(sol, params, omega_n, omega_p, k_stiffness, preload_force, method, reference)` → 每圈最大/最小膨胀力（N）。
- `calc_rrmse(y_true, y_pred)` → `(rmse, rrmse)`，**rrmse = rmse / mean(y_true)**（相对 RMSE）；
  长度不一致截断到较短；`mean(y_true)` 为 0 或无效时 rrmse 置 nan 并告警。
- `calculate_rrmse_from_sol(df, x_cols, y_cols, sol_list, labels, charge_or_discharge)`：
  电压曲线误差；**按电流符号切充放电段**（current>0 放电、<0 充电，不用 voltage.argmax 避免 CC-CV 切错）；
  仿真侧插值到实验 x 后算 RRMSE。

### 5.2 一站式对标入口（compare.compare_all）

```python
compare_all(
    sol_list,                 # PyBaMM 仿真解列表
    sim_labels,              # 仿真标签，如 ['25°C 0.25P','25°C 0.5P']
    exp_folder=...,          # 实验 CSV 文件夹（与 exp_data_list 二选一）
    exp_data_list=None,      # 已加载列表（来自 load_cycling_folder）
    params=None,             # 膨胀力对标必需
    acceleration_factor=50,  # 仿真加速倍率：圈号 × 因子 对齐实验
    channel=0,
    metrics=['retention','efficiency','swelling'],
    filter_conditions=None, # 如 "25°C" / "0.5P" / ["25°C","0.5P"]
    sim_bias=0.0, exp_bias=0.0,  # float 统一偏移 或 dict 按指标，直接叠加到 y
    method="engineering", reference="parameter_initial",
    omega_n=0.1*3.1e-6, omega_p=0, k_stiffness=1.0e9, preload_force=300.0,
)
```

- 指标：`retention`（容量保持率）、`efficiency`（能量效率）、`swelling`（最大/最小膨胀力）。
- 自动匹配 `_auto_match`：**标签中温度与倍率同时命中即配对**（得分制，1:1 独占，不重复用）。
- `filter_conditions`：含 `°C/℃` 的项为温度关键词，其余为倍率关键词；**同类 OR、异类 AND**；`None` 全过。
- `sim_bias`/`exp_bias`：手动偏移，float 对所有指标统一，或 dict 按指标分别设（如 `{"retention":0.02,"efficiency":-0.01,"swelling":100}`）。
- 膨胀力需 `params`；`method`: engineering / pybamm_thickness；`reference`: cycle_start / solution_start / parameter_initial。
- 返回各指标 Axes；未匹配项会 warning（检查标签命名）。

---

## 6. 电芯参数关联（params）

- 入口：`from src.notebook import load_params` → `load_params("MIC"|"280"|"314"|"587"|...)`，
  或 `params/__init__.py` 的 `load_cell_params` registry。
- 每个 `params<电芯名>.py` 导出 `get_hithium_params(t_factor=1, temperature=298.15[K])` → 参数字典；
  必须含 `"Nominal cell capacity [A.h]"`。
- **防参数污染（最重要）**：每次换温度都重新 `pybamm.ParameterValues("OKane2022")` + `.update(...)`，
  不要在循环外创建、循环内只 update（残留参数会污染）。
- 参数字典键不得重复（Python 静默以最后一个为准，曾因此出过 bug）；参数函数纯计算，不得 import matplotlib。

---

## 7. 机器可校验的验收判据（Acceptance）

- 数据侧：`scan` 后温度识别率合理；`curated` 条目工况重扫不被覆盖；`ignore`/`missing` 不丢人工信息。
- 对标侧：关键指标的 RRMSE 在定义容差内；合并簇指标与旧版本在容差内一致（feature parity 矩阵全勾）。
- 代码侧：`flake8`（max-line-length=120，忽略 E501/W503）+ `pytest BatteryProject/tests/` 全过。
- canonical Notebook：无绝对数据路径、无内联 `get_hithium_params` 或核心 runner；数据 query 无歧义（多匹配显式报错或配置允许批量）。
- 交付：每个 run 至少含 config / status / metrics / artifact 清单（见 `.plans/2026-07-23...spec.md`）。

---

## 8. AI 自动处理脚本骨架（照此写）

```
1) 登记：python BatteryProject/src/data_registry.py scan
2) 取数：query_datasets(cell="MIC", temp=25, test="循环", status="curated")
         → 拿到 absolute_path 列表
3) 加载：from src.exp_loader import load_cycling_folder
         exp = load_cycling_folder(folder, channel=0)   # 或 load_cycling_csv_from_peak 做 BOL 对齐
4) 清洗：from src.data_cleaning import clean_xy_curve / load_curve_file（按需）
5) 仿真：run_peak_current / run_dcr_and_power_test / workflow runner（见 notebook_api）
6) 对标：from src.compare import compare_all
         compare_all(sol_list, sim_labels, exp_data_list=exp, params=get_hithium_params(...),
                     acceleration_factor=50, metrics=["retention","efficiency","swelling"],
                     filter_conditions=["25°C","0.5P"])
7) 验收：calc_rrmse 输出 RRMSE；对照 §7 容差判定
8) 产出：图 + metrics 落 BatteryProject/output/runs/<workflow>/<run_id>/
```

---

## 9. 红线 / 禁止事项

- 不手改 `datasets.json`（用 `curate`）；移动文件即换 id 生成新条目，移动前想清楚。
- 不覆盖 `data_raw` 原始文件；派生一律走 `data_processed`。
- 不合并 `data_raw` / `data_processed` / `work` 三层。
- 参数函数纯计算，禁止 import matplotlib；字典字面量禁止重复键。
- 受 DLP（Trend Micro）保护的 `.py`/`.ipynb` 在 shell 里是密文（`%TSD-Header-###%`）；
  读用白名单 `python -c "print(open(p, encoding='utf-8').read())"`，**勿用 head/cat/Get-Content 反复排查编码**。
- 改 `src/` 后 Notebook 需 `importlib.reload()` 并重新绑定函数符号；单次任务改超 7 个文件先拆小。
