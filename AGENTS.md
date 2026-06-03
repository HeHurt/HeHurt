# Hithium 电池仿真项目 — Agent Harness

## 项目概述
基于 PyBaMM 的电池电化学仿真平台，用于 Hithium 电芯的性能预测、老化建模与实验对标。

## 架构与技术栈
- **仿真引擎**: PyBaMM (DFN 模型为主)
- **求解器**: IDAKLUSolver (首选)，fallback CasadiSolver
- **老化模型**: SEI + LAM + 裂纹 + 锂析出 (OKane2022 基础)
- **绘图**: matplotlib + scienceplots (`plt.style.use("science")`)
- **字体**: Calibri + Microsoft YaHei
- **数据导出**: openpyxl (带条件格式色阶)
- **语言**: Python 3.10+，中文交流，技术术语保留英文

---

## Harness 分域指导表

子目录 AGENTS.md 提供分域指导。在该区域工作前，先阅读对应文件。

| 区域 | Harness 文件 | 要点 |
|------|-------------|------|
| 核心仿真代码 | `BatteryProject/src/AGENTS.md` | 函数签名规范、测试要求、模块导出 |
| 参数文件 | `params/AGENTS.md` | 参数文件结构、温度依赖函数、防污染规则 |
| Notebook 工作区 | `studies/MIC_1175Ah/AGENTS.md` (各电芯目录同构) | Notebook 模板、importlib.reload、作图规范 |
| 计划与规格 | `.plans/AGENTS.md` | spec/plan 沉淀流程、任务分解模板 |

---

## 项目结构

### 核心模块 (`BatteryProject/src/`)
- `simulation.py` — 仿真核心：`run_peak_current`、`perform_dcr_test`、`run_dcr_and_power_test`
- `easy_imports.py` — 便捷导入接口
- `experiment_utils.py` — 实验工具：`build_power_step`
- `plotting.py` / `analysis.py` / `exp_loader.py` — 绘图、分析、数据加载
- `parameter_identification.py` — 参数辨识
- `electrolyte_dryout.py` — 电解液干涸模型

### 参数文件 (`params/`)
- 每个文件导出 `get_hithium_params(t_factor, temperature)` 函数
- `paramsMIC.py` (1175Ah) / `params280.py` / `params587.py` / `params314.py`

### Notebook 工作区
| 目录 | 电芯型号 | 主要内容 |
|------|---------|---------|
| `studies/MIC_1175Ah/` | MIC 1175Ah | 峰值电流、CW363对标、欧盟循环、电解液干涸 |
| `studies/314Ah/` | 314Ah | 老化建模、竞品分析、可靠性对标、不同温度/倍率 |
| `studies/280Ah/` | 280Ah | CW254 对标 |
| `studies/587Ah/` | 587Ah | 常规循环、脉冲插入 |
| `studies/cylindrical/` | 50方壳/64150 | 圆柱电芯 fade 建模 |
| `studies/AI_virtual_cell/` | — | 定容能效、COMSOL迁移 |

---

## Legacy 文件归档状态（2026-05-06 整理）

| 文件 | 状态 | 说明 |
|---|---|---|
| `工具/Fun_HZ.py` | ✅ `[LEGACY]` 已归档 | 全量迁入 `BatteryProject/src/`；参考 `docs/FUN_HZ_MIGRATION.md` |
| `MIC/宫工-徐恒-不同CW/Fun_NC.py` | ⚠️ `[LEGACY-PARTIAL]` | 干涸主链已迁入 `src/electrolyte_dryout.py`；**待迁**清单见 `docs/FUN_NC_TODO.md` |
| `工具/探索/model.py` | ✅ `[LEGACY]` 已归档 | 早期 280Ah 原型；已由 `params/params280.py` + `src/` 取代 |
| `工具/探索/model_params.py` | ✅ `[LEGACY]` 已归档 | 同上 |
| `工具/探索/run_aging.py` | ✅ `[LEGACY]` 已归档 | 概念已由 `src/parameter_identification.py` 取代 |

> **规则**：以上文件禁止添加新功能；新代码一律放在 `BatteryProject/src/` 下对应模块。

---

## 常用工作流
1. **OCV 对标**: 0.005C 充放电仿真 vs 实验数据
2. **峰值电流**: `run_peak_current()` 多温度扫描 → Excel map 导出
3. **倍率对标**: 多倍率充放电仿真 vs 实验，计算 RRMSE
4. **老化预测**: 长循环仿真 + DCR/容量/功率 fade 曲线
5. **DCR 测试**: `perform_dcr_test()` 脉冲 DCR 与功率

---

## Pre-Commit 验证协议

修改 `BatteryProject/src/` 下的代码后，必须按顺序完成：

1. **Lint**: `python -m flake8 BatteryProject/src/ --max-line-length=120 --ignore=E501,W503` — 必须通过
2. **单元测试**: `python -m pytest BatteryProject/tests/ -q` — 必须全部通过
3. **烟雾测试** (涉及仿真逻辑时): 在 Notebook 中用最小配置验证（单温度、单SOC、1个循环）

修改 `params/` 参数文件后：
1. 确认 `get_hithium_params(1, 298.15)` 可正常调用
2. 确认返回字典包含 `"Nominal cell capacity [A.h]"` 键

**如果任何验证失败，先修复再继续。不要跳过。**

---

## 反馈协议

当 Agent 犯错被纠正时：

1. 判断错误类型：
   - **harness 空白** → 更新对应的 AGENTS.md 文件填补规则
   - **一次性失误** → 当场修正即可
   - **反复出现的模式** → 加入对应 AGENTS.md 的「禁止事项」段落
2. 更新 `.github/copilot-instructions.md` 记录该规则
3. 确保后续会话能读取到更新后的指导

这形成棘轮效应：harness 在每次 review 后只会变得更好。

---

## 关键规则（全局）
- 每次换温度必须重新 `pybamm.ParameterValues("OKane2022")` + `params.update()`，防止参数污染
- 修改 src 后 Notebook 需 `importlib.reload()` 并重新绑定函数符号
- `var_pts` 标准配置: `{"x_n": 5, "x_s": 5, "x_p": 5, "r_n": 20, "r_p": 20}`
- 本机工作区文件可能受加密软件保护；如果 PowerShell/`Get-Content`/`cmd type` 看到 `%TSD-Header-###%` 或乱码，不要反复排查编码，改用 Python 读取/解析文件内容。
- 在编写代码前先描述方案并等待批准；需求不明确时先提问
- 单次任务修改超过 7 个文件时，先分解为更小任务
