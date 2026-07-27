# BatteryProject Notebook 重复检测与文件整理方案

> 检测方法：用白名单 VS Code 作为 Node 批量读取 DLP 密文 `.ipynb` 明文，对每个 notebook 提取「自定义函数/类 + 非公共导入」结构指纹与代码 token 集合，计算两两 Jaccard 相似度（重合度）。
> 阈值：**token 重合 ≥ 0.85 = 严格重复（基本同一份代码）**；0.70–0.85 = 同源衍生家族。
> 共扫描 94 个 notebook（1 个损坏文件 `自动提取数据.ipynb` 跳过）。

---

## 一、明显重复 / 基本重复（建议合并，每簇只保留 1 个）

共 12 个严格重复簇，覆盖约 30 个 notebook。每簇给出「保留谁、其余怎么处理」。

| # | 簇成员（基本同一份代码，重合度见括号） | 保留 / 处理建议 |
|---|--------------------------------------|----------------|
| 1 | `3145+3峰值电流/314 10s`(1.00) `·30s`(1.00) `·60s`；`MIC 长时储能峰值电流/cw363-10s`(0.86) `·3s`(1.00) `·5s`(1.00) | **合并为 1 个「峰值电流」参数化 notebook**（顶部 config cell 设 `CELL`/`DURATION`），删 6 留 1 |
| 2 | `LC专项/314 2+1非PCS`·`314 base 1+1非PCS`·`314 fake`(0.96)·`314 安全方案`(0.96) | **4 合 1**；`314 fake` 是占位草稿直接删；其余是同一 LC（负载工况）模板的复制 |
| 3 | `314常规循环`(0.98) `·587常规循环`(0.98) `·587欧盟电池法`(0.98) | 实为同一「常规循环」模板跨电芯套用；`587欧盟电池法` 命名错配（实为 587 拟合）。**合并为 1 个参数化 `常规循环` 模板**（cell 作 config）；修 `314常规循环` 的目录错配（它跑的是 1175Ah 参数） |
| 4 | `diff_temperature/海辰280 欧盟`·`液冷1.0-修正设计参数`(0.96)·`液冷2.0`(0.90) | **3 合 1** 为「液冷/热设计参数」模板；差异仅为设计参数，应进 config |
| 5 | `examples/调频`(0.89) `·587调频中车负载工况-过载工况`（带人名） | 保留 `examples/调频` 作模板；work 那份是「中车负载/过载」具体工况，**参数化进同一模板的 config**（去掉文件名里的人名） |
| 6 | `314Ah_0p5P_BOL_thermal_heat_diagnosis`(0.95) `·587Ah_0p5P_BOL_thermal_heat_diagnosis` | 跨电芯同方法；**合并为 1 个参数化模板**（cell 作 config） |
| 7 | `diff_temperature/314 base 1P cycle`(0.89) `·竞品分析/314 CS06` | 同源 legacy 框架；**2 合 1**，`314 CS06` 归并 |
| 8 | `587Ah_0p25P_lifecycle_heat_generation`(0.98) `·587Ah_0p5P_lifecycle_heat_generation` | 仅倍率(0.25P/0.5P)不同；**参数化合并为 1 个**（倍率进 config） |
| 9 | `AI_virtual_cell/314短期性能A1`(0.88) `·314短期性能A2` | **2 合 1** |
| 10 | `AI_virtual_cell/PSD_histogram_generator`(0.94) `·粒径分布激光粒度仪数据转换` | 都是 PSD/粒径数据转换；**2 合 1** |
| 11 | `MIC_1175Ah/段安冉-自放电率/MICCW500`(0.89) `·MIC冻结体系CW363` | 同源 Fun_HZ 自放电分析；**2 合 1**；目录名带人名，整理时去掉 |
| 12 | `MIC 长时储能峰值电流/cw500-10s`(0.95) `·cw600-10s` | 峰值电流变体；并入簇 1 的参数化模板 |

> 注：簇 1 内最低重合 0.78（因含 cw363-10s），但整体为同一峰值电流方法族，参数化后 1 个文件即可覆盖。

---

## 二、同源家族（token 0.70–0.85，建议「参数化/归档」而非简单删除）

这些是同一大框架（多为 `BatteryModelPack` / `Fun_HZ` legacy）的衍生，代码高度同源但不完全相同：

- **314Ah `diff_temperature` 整组**（`314 base 0.5P/1P/孙雨晴/欧盟/欧盟_migrated/版调参 拐角` + `LC专项` 4 个 + `海辰280/液冷1.0/2.0`）：约 13 个 notebook 共享 `RecordLayer`/`BatteryModelPack` 框架。建议**只留 1 个 canonical「314 base cycle」模板 + 参数化 config**，其余迁 `archive/`。
- **`竞品分析/314 CS01`~`CS06`**(0.84)：竞品对标系列，合并为 1 个参数化对标模板。
- **`MIC_欧盟对标`~`MIC_欧盟对标_25C`**(0.78)：同模板不同温度，参数化合并。
- **`examples/循环老化` ~ `work/280Ah/cw254`**(0.75)：生命周期老化模板，examples 作官方版，cw254 为其 280Ah 实例。
- **`examples/统一老化路径_多倍率全生命周期产热` 两份**(0.79)：删除带冗余前缀的那份。

---

## 三、文件放置问题诊断

当前痛点：
1. **目录嵌套深且不一致**：`work/<电芯>/notebooks/<五花八门子目录>/`，子目录命名随意（`不同温度倍率循环/`、`长时储能峰值电流/`、`可靠性对标notebook/`、`竞品分析/`、`LC专项/`、`diff_temperature/`、`thermal/`、`reports/数据分析/`）。
2. **关注点混杂**：可复用模板、一次性分析、纯数据转换脚本(ETL)、对标输出全堆在 notebook 里。
3. **命名混乱**：中文 + 拼音(`_0p5P`) + 人名(`洪军强-邓述珍`/`段安冉`) + 电芯/工况不明，复制粘贴后命名与内容错配（`MIC_CW363对标`→314、`587欧盟电池法`→587拟合）。
4. **模板 vs 实例无区分**：examples 与 work 里大量「同一模板不同参数」的副本，找不到权威版。
5. **无索引**：想找某个分析的 canonical notebook 只能翻目录猜。

---

## 四、解决方案（建议落地）

### 方案 A：两分法 + 索引（最小改动，推荐先做）
```
BatteryProject/examples/          # 官方可运行模板（已评审良级），flat，<topic>.ipynb
work/<cell>/notebooks/            # 日常分析，命名 <task>_<condition>.ipynb，flat 不再嵌套子目录
work/<cell>/results/              # 导出的图/表（与 notebook 分离）
archive/notebooks/<cell>/         # 合并/淘汰下来的旧 notebook（保留可追溯，不删）
```
- 把现有 `<cell>/notebooks/<子目录>/` 拍平到 `<cell>/notebooks/`，用命名区分而非目录。
- 冗余副本移入 `archive/`（**不物理删除**，满足 DLP 与可追溯）。

### 方案 B：参数化模板（根治「参数变体副本」问题）
对每个分析类型，只维护 **1 个 canonical 模板**，顶部一个 `config` cell：
```python
CELL      = "314Ah"        # 电芯
CONDITION = "0.5P"         # 工况/倍率
TEMP_C    = 25             # 温度
DATA_ROOT = WORKSPACE_ROOT / "data_raw" / CELL   # 一律走根目录常量
```
这样簇 1/3/4/6/8/12 的「参数变体」从 N 个文件变成 1 个文件 + N 组 config，新增工况不改代码。

### 方案 C：命名规范（落地时强制执行）
- 文件名：`<cell>_<task>_<condition>.ipynb`，优先 ASCII；电芯用 `314Ah/587Ah/MIC1175` 等标准缩写。
- **禁止文件名带人名**（归属走 git history / notebook 内 metadata cell）。
- 修复已错配的 3 个文件名（见报告第五节）。

### 方案 D：Notebook 索引/注册表（对齐现有 datasets.json 模式）
新增 `work/NOTEBOOK_INDEX.md` 或 `notebooks.json`，字段：`topic / canonical_path / description / cell / status(canonical|deprecated) / depends_on`。用户找模板查表即可，不必翻目录。可与现有 `datasets.json` registry 机制同源。

### 方案 E：ETL 与数据分析分离
纯数据转换 notebook（`587数据转换`、`粒径分布激光粒度仪数据转换`、`LC专项/数据转换`）本质是可复用脚本，迁到 `tools/` 或 `scripts/` 作为 `.py`，不在分析目录里堆转换 notebook。

---

## 五、建议执行顺序（需你确认后再动手）

1. **先做非破坏性项**：① 写 `work/NOTEBOOK_INDEX.md` 索引；② 把 ETL 类迁 `tools/`；③ 拍平子目录到 `<cell>/notebooks/`。
2. **再合并重复**（移 `archive/`，不删）：按第一、二节逐簇合并，每簇留 1 个 canonical。
3. **最后参数化**：把合并后的模板顶部加 `config` cell，覆盖原参数变体。
4. **修命名错配** 3 个 + 损坏文件 `自动提取数据.ipynb` 修复/恢复。

> ⚠️ 第 2、3、4 步涉及移动/重命名 DLP 加密的工作 notebook，属不可逆操作。请确认是否执行、以及「归档(archive)」还是「直接删除」偏好，我再动手。

---

## 附：canonical 模板具体实现（答疑）

### 1. 什么是 canonical + config cell

- **canonical（权威模板）**：每种「分析类型」（如常规循环、峰值电流、热诊断）只保留 **1 个** notebook 作为标准版，其余同名/同源副本归档。
- **config cell（配置格）**：放在 notebook 最顶部、唯一的 1 个 code cell，里面**只写会变的东西**——电芯、温度、倍率、数据路径——全部用变量表示。它下面的所有 cell 都引用这些变量，**不出现任何字面量**（`"314Ah"`、`298.15`、`r"D:/..."` 这类一律抽上去）。

> 为什么要这么做：之前 314/587/MIC 三份「常规循环」代码 98% 相同，差异只是 `from params314 import *` / `from params587 import *` 和几处硬编码路径。把这些差异收敛到 1 个 config cell，3 份就变 1 份。

### 2. 能不能把「同流程不同电芯/工况」合并？——能，而且项目 API 已经支持

项目 `src/notebook.py` 暴露的真实入口：

```python
setup_notebook(*, cell: str | None = None, style=...)   # 按电芯初始化环境
load_params(cell: str, *, reload_module=False)           # 按电芯加载参数集
```

`cell` 参数就是切换电芯的总开关。所以「314 / 587 / MIC1175 常规循环」本质是同一个流程，`CELL="314Ah"` 还是 `"587Ah"` 而已——**合并成 1 个模板，靠改 `CELL` 变量即可覆盖全部电芯**。

### 3. 三种实现粒度（由简到强，按需选）

**方案 A：手动切换 config cell（最简单，零新依赖）**
顶部 config cell 定义变量；要跑另一个电芯/工况，改这个 cell 的值 → Restart & Run All。
- ✅ 改动最小，和现在的工作习惯一致。
- ❌ 一次只出一个变体，要手动存结果。

**方案 B：config 列表 + 循环（一次出全部变体，最实用）**
顶部定义 `CONFIGS = [dict(cell=..., temp=..., rate=...), ...]`，下面一个 for 循环跑每个配置、结果收进 dict，最后统一画图/导出。
- ✅ N 份 notebook → 1 份 + N 行配置；一键出全对比图。
- 这是推荐的主力方式。

**方案 C：papermill 参数化执行（工程化 / CI 友好）**
模板里标一个 `parameters` tag 的 cell；用 `papermill tpl.ipynb out_314.ipynb -p CELL 314Ah` 注入参数批量生成成品 notebook。
- ✅ 每种工况产出独立 notebook，适合自动化/评审留痕。
- ❌ 多一个依赖，心智成本略高。

### 4. 具体示例：常规循环对标（before → after）

**Before（典型坏味道：314 / 587 两份几乎一样，只差导入和硬编码路径）**

```python
# 314常规循环.ipynb
from params314 import *                      # ← 电芯写死
setup_notebook(cell="314Ah")
params = load_params("314Ah")
TEMP = 298.15                                # ← 字面量
RATE = 0.5
data = pd.read_csv(r"D:/Users/hez/Downloads/不同温度倍率测试.xlsx")  # ← 绝对路径
```

**After（canonical 模板：唯一会变的东西全在顶部 config cell）**

```python
# === config cell（顶部，唯一会改变的地方）===
CELL    = "314Ah"      # 切换电芯只改这里: "314Ah" / "587Ah" / "MIC1175" / "280Ah"
TEMP_C  = 25
RATE    = 0.5
EXP_CSV = None         # 无实验数据则跳过对标（容错）
# WORKSPACE_ROOT 沿用 configure_notebook_environment / setup_notebook 已提供的常量

# === 以下所有 cell 都用上面的变量，不再出现字面量 ===
setup_notebook(cell=CELL)
params = load_params(CELL)
TEMP = TEMP_C + 273.15
data = (pd.read_csv(WORKSPACE_ROOT / "data_raw" / CELL / "xxx.csv")
        if EXP_CSV else None)
```

**方案 B 循环版（一份模板出全部电芯对比）**

```python
CONFIGS = [
    dict(cell="314Ah",   temp_c=25, rate=0.5),
    dict(cell="587Ah",   temp_c=25, rate=0.5),
    dict(cell="MIC1175", temp_c=25, rate=0.25),
]
results = {}
for cfg in CONFIGS:
    setup_notebook(cell=cfg["cell"])
    params = load_params(cfg["cell"])
    sol = run_cycle(params, temp=cfg["temp_c"] + 273.15, rate=cfg["rate"])
    results[cfg["cell"]] = sol
# 统一画图对比
plot_capacity_curves(results)
```

### 5. 哪些能合并、哪些不能

- **能合并（差异=参数）**：同流程的不同电芯 / 温度 / 倍率 / 工况。例：峰值电流(314/587/MIC)、常规循环(314/587/MIC)、热诊断(314Ah/587Ah)、液冷(1.0/2.0)、老化(0.25P/0.5P)。
- **不能合并（保持各自 1 个 canonical）**：分析类型本身不同——EIS、DCR、脉冲插入、老化、机理判别、PSD、调频。它们流程不同，彼此不合并。
- **陷阱提醒**：`314常规循环` 实际 `from paramsMIC` 跑 1175Ah 参数是 **BUG 不是合法变体**，合并前要修正，否则 canonical 会继承错误。

### 6. 落地顺序建议

1. 先挑参数变体最集中的 3 个簇（峰值电流、常规循环、热诊断），各做 1 个 canonical 模板（方案 B 循环版）。
2. 跑通验证（用项目既有 pytest/flake8 基线）。
3. 把被替代的副本移入 `archive/`（不删）。
4. 其余同源家族（diff_temperature 整组）照此推广。

---

## 七、2026-07-22 实际执行结果

本轮只处理了逐项核对过代码差异、且能安全参数化的优先组，没有执行全目录拍平、批量 ETL 迁移或依据相似度直接删除。

已完成：

1. 两组完全重复 Python 文件保留单一权威副本：
   - 保留 `tools/0_preprocess_data_power.py`，删除 `tools/0_preprocess_data.py`；
   - 保留 `archive/legacy_scripts/MIC/宫工-徐恒-不同CW/Fun_NC.py`，删除 `archive/old_notebooks/MIC/宫工-徐恒-不同CW/Fun_NC.py`。
2. 形成 5 个配置化 canonical Notebook：587Ah 生命周期产热、314Ah LC 非 PCS、PSD 转 COMSOL、峰值电流、BOL thermal；其中峰值电流复用并更新已有 examples 入口。
3. 保留 `work/587Ah/notebooks/587常规循环.ipynb`，将名称与内容错配的 `587欧盟电池法.ipynb` 归档。
4. 19 个被替代或错配的 Notebook 已移到 `D:\Users\hez\Desktop\hithium-外移\cold-archive\notebook_dedupe_20260722\`，原相对目录保留。
5. 新增 `work/NOTEBOOK_INDEX.md` 作为本批权威入口索引。

纠偏说明：

- `314 fake.ipynb` 不是可直接并入 LC 参数表的合法变体，其内容混入 587Ah 分析，因此只归档。
- MIC CW600 的 legacy 定制参数尚未进入 `params` registry；canonical 峰值 Notebook 保留该 case 的入口与明确提示，但不能宣称与旧副本数值完全等价。
- BOL thermal 仍依赖原 Notebook 中配置的外部 ARC 报告路径；这属于数据依赖，不在本次目录清理中擅自迁移。
- 全生命周期仿真耗时很长，本轮验收以 Notebook JSON、代码单元语法、参数 registry 和最小烟雾测试为主，不重跑完整研究工况。

恢复路径：操作前字节备份和 SHA-256 清单已迁至 `D:\Users\hez\Desktop\hithium-外移\workspace-archive\codex-backups\backups\notebook_dedupe_20260722\`。
