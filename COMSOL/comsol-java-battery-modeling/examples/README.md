# Examples: 即拿即用的工具和配置

本目录提供**复制粘贴就能用**的配置和工具脚本。

## 目录结构

```
examples/
├── github_instructions/
│   └── comsol.instructions.md          ← 复制到 .github/instructions/
├── github_prompts/
│   ├── cp-sweep.prompt.md              Snippet模式: CP工况扫描
│   ├── c-rate-sweep.prompt.md          Snippet模式: C倍率扫描
│   ├── diff-models.prompt.md           Snippet模式: 两个.java对比
│   └── autonomous-sim.prompt.md     ★ v3.0 Autonomous模式触发
└── scripts/
    ├── analyze_java_size.py            诊断 .java 体积
    ├── strip_java_for_ai.py            生成AI阅读专用版
    ├── comsol_batch_runner.py       ★ v3.0 主执行管线 (编译+求解+验收)
    ├── parse_comsol_errors.py       ★ v3.0 错误日志解析器
    └── generate_report.py           ★ v3.0 .docx 报告生成器
```

---

## 1. GitHub Copilot 配置

```bash
mkdir -p .github/instructions .github/prompts
cp <skill-path>/examples/github_instructions/*.md .github/instructions/
cp <skill-path>/examples/github_prompts/*.md .github/prompts/
```

详见 `references/copilot_setup.md`。

### Prompt 命令

| 命令 | 模式 | 作用 |
|---|---|---|
| `/cp-sweep` | Snippet | 加 CP 恒功率工况 + 功率扫描 |
| `/c-rate-sweep` | Snippet | C 倍率扫描 + CSV 导出 |
| `/diff-models` | Snippet | 对比两个 .java 模型 |
| `/autonomous-sim` | **Autonomous** | 全自动化仿真 (需 Agent Mode) |

---

## 2. `.java` 瘦身脚本 (v2.1)

```bash
# 诊断
python examples/scripts/analyze_java_size.py model.java

# 生成 AI 专用版
python examples/scripts/strip_java_for_ai.py model.java for_ai.java [--aggressive]
```

完整说明见 `references/java_export_slimming.md`。

---

## 3. Autonomous Mode 脚本 (v3.0) ⚡

### 3.1 整体流程

```
用户描述任务
    │
    ▼
AI生成 GeneratedModel.java (含 main + study.run + save + metrics导出)
    │
    ▼
┌─────────────────────────────────────────┐
│ comsol_batch_runner.py                  │
│   - compile (comsolcompile)              │
│   - solve (comsolbatch)                  │
│   - check acceptance.yaml                │
│   - 输出 cycle_result.json               │
└─────────────────────────────────────────┘
    │
    ├──→ success: 进入 generate_report.py
    ├──→ compile_failed: AI 读 debug_history,改 .java,重跑
    ├──→ solve_failed:    AI 调求解器配置,重跑
    └──→ acceptance_failed: AI 物理调参,重跑
    
    最终:
    ▼
┌─────────────────────────────────────────┐
│ generate_report.py                       │
│   - 提取 .java 参数/物理场                │
│   - 渲染 metrics.csv 关键指标             │
│   - 嵌入电压/温度曲线                     │
│   - 渲染 debug 过程                       │
│   - 输出 simulation_report.docx           │
└─────────────────────────────────────────┘
```

### 3.2 comsol_batch_runner.py 用法

```bash
python examples/scripts/comsol_batch_runner.py \
    --java GeneratedModel.java \
    --criteria acceptance.yaml \
    --paths paths.json \
    --workdir D:/models/auto_sim_001 \
    --max-iter 8 \
    --max-wall-clock 7200
```

`paths.json`:
```json
{
  "comsolcompile": "D:/Program Files/COMSOL/COMSOL64/Multiphysics/bin/win64/comsolcompile.exe",
  "comsolbatch": "D:/Program Files/COMSOL/COMSOL64/Multiphysics/bin/win64/comsolbatch.exe"
}
```

返回 `<workdir>/cycle_result.json`,包含 `{success, reason, iteration, metrics, ...}`。

### 3.3 parse_comsol_errors.py 用法

独立解析 stderr 或 run.log:

```bash
# 编译错误
python examples/scripts/parse_comsol_errors.py --type compile --input compile.log

# 求解错误
python examples/scripts/parse_comsol_errors.py --type solve --input run.log

# 从 stdin
comsolcompile.exe model.java 2>&1 | \
    python examples/scripts/parse_comsol_errors.py --type compile --stdin
```

退出码:
- `0`: 无错误
- `1`: 有可修复错误
- `2`: blocking 错误 (如 License),不应自动重试

### 3.4 generate_report.py 用法

```bash
python examples/scripts/generate_report.py \
    --java GeneratedModel.java \
    --metrics metrics.csv \
    --criteria acceptance.yaml \
    --debug-log debug_history.json \
    --workdir D:/models/auto_sim_001 \
    --voltage-csv voltage_vs_time.csv \
    --temp-csv temperature_vs_time.csv \
    --exp-csv experiments/dchg_1C.csv \
    --out simulation_report.docx
```

输出 5-8 页 .docx,自动渲染:
- 7 章节标准结构
- 参数表 (从 .java 提取)
- 关键指标表
- 电压/温度曲线 (matplotlib)
- 实验对比图
- Debug 迭代历史
- 验收逐项对标表

---

## 4. Python 依赖

| 脚本 | 依赖 |
|---|---|
| analyze_java_size.py | 仅标准库 |
| strip_java_for_ai.py | 仅标准库 |
| comsol_batch_runner.py | `pyyaml`, `pandas`, `numpy` |
| parse_comsol_errors.py | 仅标准库 |
| generate_report.py | `pyyaml`, `pandas`, `numpy`, `matplotlib`, `python-docx` |

```bash
pip install pyyaml pandas numpy matplotlib python-docx
```

---

## 5. 典型 acceptance.yaml 模板

放在工作目录,定义 Autonomous Mode 的验收条件:

```yaml
meta:
  task: "LFP 280Ah 1C 放电基线"
  max_iterations: 8

numeric_criteria:
  - id: capacity
    description: "1C 放电容量"
    expr: "capacity_Ah"
    bound: ">= 270"
    unit: Ah
    severity: hard
  - id: min_voltage
    expr: "min_voltage_V"
    bound: ">= 2.5"
    unit: V
    severity: hard
  - id: max_temp
    expr: "max_temp_C"
    bound: "<= 60"
    unit: degC
    severity: hard

experimental_reference:
  enabled: false  # 设 true 时填以下
  references:
    - id: dchg_1C
      file: experiments/dchg_1C.csv
      file_columns: [time_s, voltage_V]
      sim_columns: [time, "liion.E_cell"]
      sim_export: voltage_vs_time.csv
      metric: RMSE
      threshold: 0.05
      unit: V
      severity: hard
```

完整字段说明 → `references/acceptance_criteria.md`。
