---
mode: agent
description: 触发 COMSOL Autonomous Mode 完全自动化仿真流程 (写完整.java → 编译 → 求解 → debug → .mph + 报告)
---

# Autonomous COMSOL Simulation

执行 **Autonomous Mode** 全流程闭环仿真。

⚠️ **前提条件检查** (开始前必须确认):
- 本地已安装 COMSOL 6.4
- 当前工作环境是 agent 模式 (有 bash 终端访问)
- 已安装 Python 依赖: `pyyaml pandas matplotlib python-docx`

## 输入参数

请向用户收集以下信息 (按顺序逐个问,不要一次性灌输):

1. **任务描述**: ${input:task:简述任务,例如"LFP 280Ah 电芯 1C CC 放电仿真"}
2. **参考 .java 文件路径** (可选,如有现成模型作为模板): ${input:reference_java}
3. **工作目录** (放生成的所有文件): ${input:workdir}
4. **COMSOL 路径**:
   - `comsolcompile.exe`: ${input:comsolcompile_path:D:/Program Files/COMSOL/COMSOL64/Multiphysics/bin/win64/comsolcompile.exe}
   - `comsolbatch.exe`: ${input:comsolbatch_path:D:/Program Files/COMSOL/COMSOL64/Multiphysics/bin/win64/comsolbatch.exe}
5. **验收条件**: 引导用户列出关键指标,生成 `acceptance.yaml`
6. **实验对标 CSV** (可选): ${input:experiment_csv}

## 执行流程

按 `SKILL.md` 中 Autonomous Mode 的 6 步执行,严格遵守红线。

### STEP A — 对齐 (必须人工确认才能继续)

向用户呈现完整的执行计划:
- 工作目录
- 路径配置 (检查是否真实存在)
- acceptance.yaml 内容 (逐项确认每个验收指标)
- 预算: `max_iterations` (建议 8), `max_wall_clock` (建议 7200s)

**用户确认后才能进入 STEP B**。

### STEP B — 生成完整 .java

按 `references/liion_lfp_reference.md` 的 LFP/Gr 参数,生成 **完整可编译** 的 .java:
- 包含 `import com.comsol.model.*`
- `main(String[] args)` 含 `model.study(...).run()` + `model.save(...)`
- 末尾加 metrics 导出 (见 `references/autonomous_execution.md` 第 4.1 节)

保存为 `<workdir>/GeneratedModel.java`。

### STEP C-E — Debug 循环

调用 `scripts/comsol_batch_runner.py`:

```bash
python <skill>/scripts/comsol_batch_runner.py \
    --java <workdir>/GeneratedModel.java \
    --criteria <workdir>/acceptance.yaml \
    --paths <workdir>/paths.json \
    --workdir <workdir> \
    --max-iter 8
```

读 `<workdir>/cycle_result.json` 判断:

- `success: true` → 进入 STEP F
- `success: false, reason: compile_failed` → 读 `debug_history.json` 末条错误,按 `references/autonomous_execution.md` 第 2.3 节修复 .java,重跑
- `success: false, reason: solve_failed` → 同上,按第 3.2-3.3 节调收敛
- `success: false, reason: acceptance_failed` → 物理调参,按第 5.2 节调参映射,重跑
- `success: false, reason: blocking_error` → **立即停止**,告诉用户检查 license
- `success: false, reason: max_iter_exceeded` → 停止,进入 STEP F (生成失败报告)

### STEP F — 报告

```bash
python <skill>/scripts/generate_report.py \
    --java <workdir>/GeneratedModel.java \
    --metrics <workdir>/metrics.csv \
    --criteria <workdir>/acceptance.yaml \
    --debug-log <workdir>/debug_history.json \
    --workdir <workdir> \
    --voltage-csv <workdir>/voltage_vs_time.csv \
    --temp-csv <workdir>/temperature_vs_time.csv \
    --exp-csv <experiment_csv> \
    --out <workdir>/simulation_report.docx
```

## 交付物

完成后向用户呈现工作目录树:

```
workdir/
├── GeneratedModel.java          ← 最终版完整.java
├── result.mph                   ← ★ COMSOL 验收用
├── simulation_report.docx       ← ★ 报告
├── metrics.csv                  ← 关键指标
├── debug_history.json           ← debug 全过程
├── plots/                       ← 报告引用的图
└── ...
```

## 红线 (严格遵守)

- ❌ 未与用户确认验收条件前编译/求解
- ❌ debug 超过 max_iterations 还在继续
- ❌ 修改物理场结构 (只能调数值参数)
- ❌ 覆盖用户提供的参考 .java
- ❌ License 错误时反复重试
- ✅ 每次调参写入 debug_history.json
- ✅ 失败时也要生成报告 (包含完整失败记录)
