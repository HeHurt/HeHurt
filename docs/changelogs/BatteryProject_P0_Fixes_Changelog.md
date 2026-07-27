# BatteryProject P0/高危修复变更说明

**日期**：2026-07-21
**范围**：代码审查报告中标记为 P0/高危的非 Notebook 问题
**验证基线**：flake8 0 错误 ｜ pytest 196 passed / 1 skipped（零回归）

---

## 修复清单

### 1. data_registry.py — 原子写 + 损坏兜底（P0 / 高危）

**问题**：`save_registry` 直接 `open(..., "w")` 写 `datasets.json`，进程中断/磁盘满会产生截断 JSON；`load_registry` 无损坏兜底，单个坏文件使所有 `ls`/`summary`/`scan` 命令连锁崩溃。

**修复**：
- `save_registry` 改为先写 `<path>.tmp` 再 `Path.replace` 原子替换，保证不会写出半截 JSON。
- `load_registry` 捕获 `json.JSONDecodeError`，将损坏文件备份为 `<name>.corrupt.<timestamp>` 并返回空 registry，命令链不中断。

**文件**：`BatteryProject/src/data_registry.py`

---

### 2. analysis.py — calc_rrmse NaN 对齐与零均值保护（P0 / 高危）

**问题**：实验侧 `y_exp` 与仿真侧 mask 独立 dropna，长度可能不一致导致越界；`mean(y_true)==0` 时 `rrmse` 为 inf 无保护。

**修复**：
- 输入转 `float` 数组；长度不一致时截断到较短者并 `logger.warning`。
- 用 `np.isfinite(diff)` 统一 mask 掉 NaN/inf；全无效时返回 `(nan, nan)`。
- `mean(y_true)` 为 0 或无效时 `rrmse` 返回 `nan` 并告警，不再除零。

**文件**：`BatteryProject/src/analysis.py`

---

### 3. analysis.py — calculate_rrmse_from_sol 充放电切分（P0 / 高危）

**问题**：用 `voltage.argmax()` 切分充放电，假设"先充后放、峰值即切换点"。CC-CV 充电末端平台、多台阶/脉冲工况下 argmax 定位不准，RMSE 被错误切分污染。

**修复**：
- 弃用 `voltage.argmax()`，改用电流符号切分：`current < 0` = 充电段，`current > 0` = 放电段（与 `compute_cycle_energies`/`get_discharge_capacity` 口径一致）。
- 实验侧 `x_exp`/`y_exp` 改为 `df[[x_col, y_col]].dropna()` 按行同时 dropna，保证长度一致。
- 容量对齐到段起点；仿真段点数 <2 时跳过插值并告警，返回 `(nan, nan)`。
- 无可用电流信号时回退整段并 `logger.warning`。

**文件**：`BatteryProject/src/analysis.py`

---

### 4. jobs.py — 状态文件多写者竞争（P0 / 中危）

**问题**：`heartbeat` 线程每 1s 调用 `update_status`（读-改-写 `status.json`），worker 主线程同时调用 `log_status`，无锁的 read-modify-write 会互相覆盖，丢失日志/进度。

**修复**：
- 新增模块级 `_status_lock = threading.Lock()`。
- `update_status` 与 `log_status` 的读-改-写临界区用 `with _status_lock:` 保护。
- 每个 job 运行在独立 spawn 子进程，进程内一把锁即可覆盖同 job 的并发写。

**文件**：`BatteryProject/api/jobs.py`

---

## 验证结果

| 验证项 | 命令 | 结果 |
|--------|------|------|
| 语法编译 | `py_compile` × 3 文件 | 全部 OK |
| Lint | `flake8 ... --max-line-length=120 --ignore=E501,W503` | 0 错误 |
| 单元测试 | `pytest tests/ -q` | 196 passed / 1 skipped（与修改前一致） |

## 实施方式（DLP 适配）

三个 `.py` 文件受 Trend Micro DLP 加密，直接 Edit 会失败。采用「受管 Python 读取明文 → scratch/patches 写 old/new 片段 → apply_patches.py 精确单次替换并 Python 写回（DLP 自动重新加密）」流程。patch 片段留存在 `scratch/patches/` 供回滚/审查参考。

## 未处理项（按用户要求排除 / 非 P0）

- Notebook 体系（90/93 被 DLP 加密，属流程问题非代码修复）。
- P1/P2 问题（路径遍历校验、孤儿进程 reaper、并发上限、reporting NaN 处理、类型注解补齐等）见审查报告第三节路线图。
