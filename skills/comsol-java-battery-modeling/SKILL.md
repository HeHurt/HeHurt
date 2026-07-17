---
name: comsol-java-battery-modeling
description: Use this skill whenever working with COMSOL Multiphysics 6.4 battery models exported as .java files. Two delivery modes supported - Snippet Mode for read+modify (AI generates Java code snippets), and Autonomous Mode for full closed-loop simulation (AI writes complete .java, compiles via comsolcompile.exe, runs via comsolbatch.exe, auto-debugs until acceptance criteria pass, then generates .mph file plus a Word simulation report). Also supports Hybrid tool routing with sim-cli/sim-plugin-comsol and configured COMSOL MCP tools for .mph inspection, shared Desktop workflows, structured model queries, boundary/dataset/result extraction, and ad-hoc postprocessing. Trigger on any mention of COMSOL Java files (.java), Li-ion battery models in COMSOL, liion physics interface, P2D models, electrochemical-thermal coupling (liion + ht), 1D-3D multiscale battery models, CC or CP operating conditions, COMSOL parameter sweeps, MATLAB LiveLink, automated COMSOL simulation, COMSOL batch execution, comsolbatch, comsolcompile, auto-debugging COMSOL models, sim-cli, sim-plugin-comsol, COMSOL_Multiphysics_MCP, or generating simulation reports. Use especially when the original .mph file is encrypted and the user is working with .java exports.
---

# COMSOL Java电池建模 v3.1 — Java主链 + Hybrid工具层

本skill用于读取、理解、修改 COMSOL Multiphysics 6.4 导出的电池模型 `.java` 文件,**并可选地自主编译/求解/debug/生成报告**。Java/comsolcompile/comsolbatch 仍是可复现交付主链; sim-cli/sim-plugin-comsol 与 COMSOL MCP 作为 Hybrid 工具层,只在需要检查环境、查看 `.mph` 内部状态、共享 Desktop、结构化读取结果或做 ad-hoc 后处理时接入。

| 配置项 | 值 |
|---|---|
| COMSOL版本 | **6.4** |
| 化学体系 | **LFP / 石墨** |
| 几何 | **1D P2D** 或 **1D P2D + 3D热耦合** |
| 工况 | **CC恒流** + **CP恒功率** (储能场景) |
| 老化建模 | 不涉及 |

---

# 两种交付模式 + Hybrid工具层

本 skill 有两种工作模式,**任务开始时必须明确用户处于哪种模式**:

| 维度 | Snippet Mode (片段模式) | Autonomous Mode (自主模式) |
|---|---|---|
| **AI输出** | 代码片段 (粘贴用) | 完整 .java + 编译执行 + .mph + 报告 |
| **执行权限** | 不需要 (只输出文本) | 需要命令行工具 (跑 comsolcompile.exe/comsolbatch.exe) |
| **适用工具** | Claude.ai / Copilot Chat / Cursor | Claude Code / Copilot Agent / Cursor Composer |
| **适用阶段** | 探索、试错、教学 | 项目交付、批量任务、自动化报告 |
| **用户参与度** | 高 (粘贴、编译、验证) | 低 (定义目标 + 验收,等结果) |
| **典型耗时** | 几分钟出片段 | 几十分钟到几小时(含debug循环) |

Hybrid 工具层不是第三种交付模式,而是给以上两种模式补充观察和操作能力:

| 工具层 | 定位 | 何时启用 |
|---|---|---|
| Java/comsolcompile/comsolbatch | 可复现执行底座 | 默认主链路:从零建模、改 `.java`、批量重跑、交付 `.mph/.java/report` |
| sim-cli + sim-plugin-comsol | COMSOL 运行时入口 | 检查环境/license、`.mph` inspect、本地文档搜索、shared Desktop、人机协作盯模型 |
| COMSOL MCP tools | 结构化查询/小步操作接口 | 列参数/边界/数据集、读取结果表达式、导出图/数据、临时后处理、快速诊断 |

核心原则: **不要把三套工具机械串联**。先判断当前缺的是"生成能力"、"运行时能力"还是"观察能力",再选择最小工具集合。

## 何时进入 Autonomous Mode

满足**全部**以下条件时进入自主模式:
1. ✅ 工具有命令行执行能力(Claude Code / Copilot Agent / Cursor Composer 等)
2. ✅ 本地有 COMSOL 6.4 安装,可访问 `comsolcompile.exe` 和 `comsolbatch.exe`
3. ✅ 用户明确要求"自己跑完"、"出 .mph"、"出报告"或类似闭环表述
4. ✅ 用户提供了验收条件(数值指标 或 实验对标CSV)

否则默认 Snippet Mode。**有疑问时主动问用户**。

---

# DLP/TSD 加密文件读取桥 (Hithium 本机规则)

当 COMSOL `.java` 文件头出现 `%TSD-Header-###%`、PowerShell/Python/`javac.exe` 读到乱码,但 VS Code 可以正常打开源码时,**优先使用 VS Code 的 `Code.exe` 作为读取桥**。

本机已验证可用路径:

```powershell
$env:ELECTRON_RUN_AS_NODE='1'
& 'D:\软件安装\Microsoft VS Code\Code.exe' -e "const fs=require('fs'); const p='<java-file>'; const s=fs.readFileSync(p,'utf8'); console.log(s.slice(0,80));"
```

执行规则:
- 先用 `Code.exe` 读取前 80 个字符,确认不是 `%TSD-Header-###%`。
- 如果 `Code.exe` 读取后普通 Python/PowerShell 也能读到明文,后续可按正常工作流分析和 patch。
- 如果 `Code.exe` 写出的工作副本仍被 DLP 重新加密,不要修改密文字节;改为在已明文可读的原文件上操作。
- 自动迭代时仍以 `comsolcompile.exe` 为默认编译入口;不要用 `java.exe` 直接编译 `.java`。

---

# 自动仿真路径选择与外部工具边界

当用户提到 `COMSOL_Multiphysics_MCP`、`sim-cli`、`sim-plugin-comsol`、`shared-desktop`、"自动改模型代码自动仿真迭代"、"检查 mph 模型树"时,先做路径选择,不要直接开新工作流:

## 路由决策表

| 目标 | 首选路径 | 可选增强 | 不覆盖内容 |
|---|---|---|---|
| 从零建模并交付 `.java/.mph/report` | Autonomous Mode + `comsolcompile.exe`/`comsolbatch.exe` | sim-cli 做环境检查; MCP 做结果抽查 | 不把完整复杂电池建模强塞进 MCP 小工具 |
| 修改/理解 COMSOL 导出的 `.java` | Snippet Mode 或 Autonomous Mode | MCP/文档检索核对 API 名称 | 不直接操作 `.mph` 内部树 |
| 已有 `.mph`,不知道模型里有什么 | **DLP 加密**(头含 `%TSD-Header-###%`): sim-cli `exec` + `ModelUtil.load`(后端 `comsolmphserver` 能读密文); **未加密**: COMSOL MCP `model_inspect` | 必要时导出 compact Java 再读 | MCP standalone 读加密 `.mph` 必失败(报"文件已损坏或无效");详见下文「读 DLP 加密 .mph 的已验证路径」 |
| 需要人盯着 COMSOL Desktop 看模型 | sim-plugin-comsol shared Desktop / live session | Java API 分步执行小脚本 | 不把 GUI 点击流程写进 Java snippet |
| 求解后临时读取指标/图/数据 | COMSOL MCP `datasets_list`/`results_evaluate`/`results_export_*` | Java 导出固定验收 CSV | 不为了一个临时指标重编译整个模型 |
| 稳定批量重跑或参数扫描 | `comsolbatch.exe` 或 sim-cli 调度 batch | MCP 做状态/结果 spot check | 不用 Desktop GUI 承担批量生产 |
| DLP/权限判断 | 先跑读取探针,再给 IT 证据包 | sim-cli doctor 辅助记录环境 | 不反复猜编码、不修改密文字节 |

## Hybrid Mode 启用规则

只有出现以下任一情况,才启用 sim-cli/sim-plugin-comsol 或 MCP:

1. **运行时不确定**: 不知道 COMSOL 版本、license、`comsolcompile.exe`/`comsolbatch.exe`、Desktop attach 是否可用。
2. **模型不可见**: 输入是 `.mph`,需要检查 physics、parameters、mesh、study、result、dataset、boundary id。
3. **迭代需要观察**: 编译能过但求解/后处理异常,需要结构化读取模型状态或结果变量。
4. **人机协作**: 工程师希望打开可见 COMSOL Desktop,边看边让 Agent 分步建模。
5. **ad-hoc 后处理**: 需要临时计算 `max(T)`、boundary flux、参数扫描结果或额外导出图片/CSV。

未触发以上条件时,不要引入额外工具层;继续走 Java/batch 主链路。

## sim-cli + sim-plugin-comsol 使用边界

sim-cli 的角色是本地 CAE runtime,不是 COMSOL 建模知识库。使用前先按当前项目 README/官方仓库说明确认安装命令;若项目尚未安装,优先使用 project-local uv 环境:

```powershell
uv add sim-cli-core sim-plugin-comsol
uv run sim plugin sync-skills --target .agents/skills --copy
uv run sim plugin list
uv run sim check comsol
uv run sim plugin doctor comsol --deep
```

执行规则:
- 默认同机运行,**不要加 `--host`**,除非用户明确指定远程 solver 主机。
- 不要把 `sim serve` 暴露到公共网络;远程模式必须是受控内网/实验机。
- sim-cli 适合做 check/connect/inspect/exec/verify/artifact/checkpoint discipline;复杂电池模型的可复现源码仍写入 `.java`。
- 如果 shared Desktop 中用户手动改了模型,Agent 必须重新 inspect live state 后再继续,不能沿用旧假设。

需要可见 Desktop 协作时,按 plugin README 的 live session 路径启动并确认绑定:

```powershell
uv run sim connect --solver comsol --ui-mode gui --driver-option visual_mode=shared-desktop
uv run sim inspect session.health
uv run sim exec --file step.py
```

继续操作前,`session.health` 中应显示 live model binding 可用;否则不要假定 GUI 中看到的模型就是 Agent 正在修改的模型。

## 读 DLP 加密 .mph 的已验证路径 (Hithium 本机, 2026-06 实测)

本机 `.mph` 多被 DLP 加密(文件头 `%TSD-Header-###%`)。读取结论:
- **COMSOL MCP standalone 读不了**: `model_load` 报 "COMSOL Multiphysics 模型文件已损坏或无效"(后端进程读到密文)。
- **sim-cli + sim-plugin-comsol 能读**: 其后端 `comsolmphserver.exe` 可正常 load 加密 `.mph`(已实测读出 1GB 加密产热模型)。手开的 Desktop 是 `ComsolUI.exe`(DLP 白名单),二者是不同 exe——所以不能简单断定"COMSOL 都读不了加密文件"。

已验证只读工作流(uv 环境, `sim` 非全局命令,在项目根 `D:\Users\hez\Desktop\hithium` 下):

```powershell
uv run sim --no-interactive connect --solver comsol --ui-mode no_gui   # 记下 session_id
$env:SIM_SESSION='<id>'
uv run sim --no-interactive exec "model = ModelUtil.load('m1', r'<路径.mph>')"   # 1GB 约 20s
# ... 多次 exec 读参数/结果 ...
uv run sim --no-interactive disconnect
```

exec namespace 暴露 `model` 和 `ModelUtil`(**不是** `session`);用 `print(...)` 回显 stdout。常用 COMSOL Java API:
- 参数数值: `model.param().evaluate('name')`;原始表达式: `model.param().get('name')`
- 结果时序: `ne=model.result().numerical().create('g','EvalGlobal'); ne.set('data','dset1'); ne.set('expr',['Q1/3600','vol']); ne.getReal()`(返回 `[expr][time]`)
- 全局方程(累积容量/能量)变量名: `model.physics('ge').feature(...).getString('name')`/`getString('equation')`(可能叫 Q1/Q2,不固定,逐文件确认)
- OCP 数据表: `model.material('matX').propertyGroup('ElectrodePotential').func('intN').getStringMatrix('table')`
- 内置 SOC 节点: `model.physics('liion').feature('socicd1')` 的 `Ecell_0SOC`/`Ecell_100SOC`(注意默认占位值 3V/4V 常与真实窗口不符)
- 物理树遍历: 递归 `feature().tags()`;study 辅助扫描: `model.study('std1').feature('param').getStringArray('pname')`/`getStringArray('plistarr')`

注意:
- 多个 1GB 模型别同时驻留;load 新模型前先 `ModelUtil.remove('<tag>')` 释放内存。
- 复杂 python(含 lambda 的 `x:`、引号、`*`)走 `exec --file <script.py>`,**不要内联**——PowerShell 会把 `x:` 误判成盘符报 "Remove-Item on system path 'x:' is blocked"。脚本里可 `import numpy as np`。
- 这是只读 inspect / 数据反解用途;可复现交付仍走 Java/batch 主链。

## COMSOL MCP 使用边界

COMSOL MCP 的角色是结构化查询和小步操作接口,不是完整替代 Java 导出链。优先使用已经配置好的 `mcp_servers.comsol` 工具;不要在本 skill 内重复实现 MCP server。

适合调用 MCP 的任务:
- `model_inspect` / `param_list` / `physics_list` / `geometry_list_features`
- `geometry_get_boundaries` 辅助识别边界编号
- `datasets_list` / `results_evaluate` / `results_global_evaluate`
- `study_solve_async` + `study_get_progress` 用于可取消的长求解
- `results_export_data` / `results_export_image` 生成报告素材

不适合优先用 MCP 的任务:
- 大型 `liion + ht` 电池模型从零完整搭建
- 需要完整版本追溯和 diff 的复杂模型修改
- 需要交付可复现实验链的批量参数扫描
- MCP 未连接、工具面缺失或错误恢复不稳定时的生产任务

## Hybrid smoke test 顺序

在真正接入复杂电池模型前,先做最小闭环:

1. `uv run sim check comsol` 确认本机 COMSOL 可发现。
2. `uv run sim plugin doctor comsol --deep` 确认 plugin wiring 与本地 solver detection。
3. 调 `mcp_servers.comsol` 状态检查;若未连接,先启动/连接 COMSOL session。
4. 用一个最小热模型或现有小 `.mph` 做 inspect + solve + export,不要一开始跑 P2D/3D 电热耦合大模型。
5. 记录 artifact: Java、mph、log、metrics、plots、debug_history。

## DLP / IT 证据包最小探针

遇到 "VS Code/Copilot 能读,COMSOL/Python/Java 读不到" 时,输出一份可交给 IT 的证据包:

1. 文件路径与文件类型: `.java` / `.mph` / 数据文件。
2. 读取矩阵: VS Code、PowerShell、Python、`Code.exe` bridge、COMSOL 自带 `java.exe`、`comsolcompile.exe`、`comsolbatch.exe` 分别能否读到明文。
3. 每个进程的完整路径,尤其是:
   - `D:\软件安装\Microsoft VS Code\Code.exe`
   - `D:\Program Files\COMSOL\COMSOL64\Multiphysics\java\win64\jre\bin\java.exe`
   - `D:\Program Files\COMSOL\COMSOL64\Multiphysics\bin\win64\comsolcompile.exe`
   - `D:\Program Files\COMSOL\COMSOL64\Multiphysics\bin\win64\comsolbatch.exe`
4. 最小复现命令和错误原文。
5. 结论: 需要放行的是文件读取、Java runtime、COMSOL batch/compile,还是工作区编辑器通道。

如果只是要证明链路能跑,先做 smoke run: 小模型、短时间、少参数,能编译/求解/导出即可;不要一开始跑完整电热耦合和大倍率矩阵。

---

# Snippet Mode 工作流 (v2.x 原工作流,默认)

## Pre-Step 1 — 检查 `.java` 体积

| 体积 | 状态 | 行动 |
|---|---|---|
| <500 KB | ✅ 健康 | 进入 Step 2 |
| 500 KB - 1 MB | ◐ 略大 | 可用但建议瘦身 |
| 1 MB - 5 MB | ⚠️ 偏大 | 建议瘦身后再读 |
| >5 MB | ❌ 必须瘦身 | AI 读一次就吃掉大量context |

详见 `references/java_export_slimming.md`。

## Step 1 → Step 5

1. **用户导出 .java** (COMSOL Desktop, 开 Compact history)
2. **AI 建心智地图** (grep 11 个关键节点)
3. **AI 计划修改** (改/留/加/副作用 4清单,用户确认)
4. **AI 生成代码片段** (四段header + 六铁律)
5. **用户编译验证 + 回写**

(完整 Snippet Mode 工作流细节同 v2.1,见下方 "Snippet Mode 详细约定")

---

# Autonomous Mode 工作流 (v3.0 新增)

## 总览

```
用户提供:
  ① 参考 .java (现有模型,可选) 或 全新建模需求
  ② 验收条件 (数值指标 + 可选实验CSV)
  ③ COMSOL 安装路径

         │
         ▼
┌────────────────────────────────────────────────────┐
│  STEP A: 理解需求 + 验收条件 (与用户确认)            │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│  STEP B: 生成完整 .java (从参考改,或从模板新建)     │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│  STEP C: 用 comsolcompile.exe 编译 → .class         │
│  错误 → 解析 → 修改 .java → 重试 (最多 N 次)        │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│  STEP D: 用 comsolbatch 求解 → .mph                 │
│  收敛失败 → 调参 → 重试                              │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│  STEP E: 提取结果 → 对照验收条件                     │
│  不达标 → 物理分析 → 调参 → 回 STEP C/D              │
└────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│  STEP F: 生成 .docx 仿真报告                         │
└────────────────────────────────────────────────────┘
         │
         ▼
   交付: cell.java + cell.mph + report.docx
```

## Autonomous Mode 6 步详解

### STEP A — 需求 + 验收对齐 (强制确认环节)

AI **必须先与用户确认** 4 项,缺一不可:

1. **任务类型**: 改既有模型 / 全新建模 / 参数扫描 / 优化反演
2. **验收条件**: 数值指标 + 可选实验数据CSV (格式见 `references/acceptance_criteria.md`)
3. **路径配置**:
   - `comsolcompile.exe` 路径 (典型: `D:\Program Files\COMSOL\COMSOL64\Multiphysics\bin\win64\comsolcompile.exe`)
   - `comsolbatch.exe` 路径 (典型: `D:\Program Files\COMSOL\COMSOL64\Multiphysics\bin\win64\comsolbatch.exe`)
   - `java.exe`/`javac.exe` 路径 (可选,仅用于诊断或用户明确要求的直接编译)
   - 工作目录 (放 .java / .mph / 报告)
4. **资源边界**: max debug iterations (默认 8), max wall-clock (默认 2 小时), 是否允许调整物理参数 (default: yes,但记录在报告)

未对齐 → 不进入 STEP B,继续问。

如果任务需要 Hybrid 工具层,STEP A 还要补充确认:
- sim-cli/sim-plugin-comsol 是否已安装,以及是否只在本机运行。
- COMSOL MCP 是否已连接到可用 COMSOL session。
- 是否需要 shared Desktop 让工程师实时查看/介入。
- 输入是 `.java`、`.mph`、还是二者都有;`.mph inspect` 是否是 hard requirement。

Hybrid 缺失不自动阻塞 Java/batch 主链。只有当当前任务依赖 `.mph inspect`、shared Desktop、MCP 读取结果或 live model state 时,才停下让用户先配置工具。

### STEP B — 生成完整 .java

不再是片段,而是完整可编译文件。

**起点: 用 `references/complete_model_template.md` 的 golden 模板**,不要从零拼装。该文档提供节点顺序正确的端到端 .java(含最小可跑版 + 完整版)。

**强烈建议先用「最小可跑版」**(等温 liion)打通管线,确认能 编译→求解→导出 metrics.csv→验收,再切完整版(加 ht 电热耦合)。这符合 debug 哲学: 先让最简单的能跑,再加复杂度。

模板结构:

```java
/* ============================================================
 * Auto-generated COMSOL 6.4 battery model
 * Generated: <timestamp>
 * Task: <user's request summary>
 * Acceptance criteria:
 *   - <criterion 1>
 *   - <criterion 2>
 * ============================================================ */
import com.comsol.model.*;
import com.comsol.model.util.*;

public class GeneratedModel {
  public static Model run() {
    Model model = ModelUtil.create("Model");
    model.modelPath("<working-dir>");
    model.label("<model-name>.mph");

    // === Parameters ===
    // ... (按 LFP/Gr 典型参数,参考 references/liion_lfp_reference.md)

    // === Component / Geometry ===
    // ...

    // === Physics (liion + ht) ===
    // ...

    // === Mesh ===
    // ...

    // === Study ===
    // ...

    return model;
  }

  public static void main(String[] args) {
    Model model = run();
    // 求解
    model.study("std1").run();
    // 自动保存 .mph
    model.save("<working-dir>/<model-name>.mph");
  }
}
```

**关键**: `main()` 方法必须包含 `model.study(...).run()` 和 `model.save(...)`,否则只能编译不能跑。

### STEP C-E — Debug 循环 (由 Agent 驱动)

**重要: 循环的"大脑"是 AI Agent,不是 Python 脚本。** `comsol_batch_runner.py` 每次调用只执行**一轮** 编译→求解→验收,因为修正编译错误、调整物理参数需要 LLM 的智能判断,Python 脚本做不到。

循环模式:
```
iteration = 1
while iteration <= max_iter:
    1. Agent 调 comsol_batch_runner.py --iteration <N>
       (第1轮重置历史,之后累积到同一个 debug_history.json)
    2. 读 cycle_result.json 的 next_action:
       - "done"                  → 验收通过,进入 STEP F
       - "agent_adjust_and_rerun" → 看 acceptance.items_failed,调参,iteration+1
       - reason="compile_failed"  → 看 details.parsed_errors,改 .java,iteration+1
       - reason="solve_failed"    → 调求解器/收敛,iteration+1
       - reason="blocking_error"  → 立即停 (License),报告用户
    3. Agent 自己控制 max_iter 预算 (这是 Agent 的预算,不是脚本的)
```

`--max-iter` 不再是脚本参数(脚本不循环)。Agent 用 `--iteration N` 标记轮次,历史会累积,报告才能展示完整的多轮 debug 过程。

两条路径:

**路径1: COMSOL 官方 comsolcompile (推荐)**
```bash
"<comsol-bin>/comsolcompile.exe" GeneratedModel.java
# 输出 GeneratedModel.class
```

**路径2: COMSOL JRE javac.exe 直接编译 (不推荐,仅诊断/用户明确要求,需 classpath)**
```bash
"<comsol-java-bin>/javac.exe" -cp "<comsol-plugins>/*" GeneratedModel.java
```

**默认走路径1 (comsolcompile)**,它内置了所有 classpath 处理。

**错误处理循环**:
- 解析 stderr 中的编译错误
- 按 `references/autonomous_execution.md` 的错误模式库定位原因
- 修改 .java 对应位置
- 重新编译
- 计数: 每次失败 +1,达到 max_iterations 终止并报告

### STEP D — 求解 (comsolbatch)

```bash
"<comsolbatch>" -inputfile GeneratedModel.class \
                -outputfile result.mph \
                -batchlog run.log \
                -recover
```

**Recover** 选项关键: 求解出错时保留中间状态供调试。

**收敛失败的典型处理**:
- `Newton method did not converge` → 减小时间步长 / 降低 reltol / 改 segregated solver
- `License timeout` → 等待并重试
- `Out of memory` → 减少网格密度 / 减少扫描点

详见 `references/autonomous_execution.md` 的"求解失败模式库"。

### STEP E — 验证 (对照验收条件)

求解完成后,AI 从 `.mph` 中提取关键指标:
```bash
"<comsolbatch>" -inputfile result.mph \
                -methodcall extractMetrics \
                -outputfile metrics.json
```

或者求解时直接用 `model.result().table().create(...)` + `export().run()` 导出 CSV。

Hybrid 可选路径:
- 固定验收指标优先写进 Java 导出逻辑或 `extractMetrics` 方法,保证可复现。
- 临时排障/探索性指标可用 MCP `results_evaluate` / `results_global_evaluate` 读取。
- 报告素材可用 MCP `results_export_data` / `results_export_image`,但最终报告必须记录这些导出节点和表达式。
- 如果 MCP dataset/variable 不存在,不要直接改验收指标;先回到 `.java`/`.mph` 检查结果节点是否生成。

逐项对照 `acceptance_criteria.yaml`:
- 数值指标: 比较计算值与阈值
- 实验对标: 读 reference CSV → 计算 RMSE/MAE/相关系数 → 与阈值比较

**任一项不满足 → 物理分析 → 调参 → 回 STEP D**:
- 容量低 → 可能是颗粒扩散太慢 → `Ds_pos` 调高一档
- 温度过高 → 可能是对流不足 → `h_amb` 调高
- 电压平台与实验不符 → 可能是 OCV 函数有偏差 → 校准 OCV 系数
- 等等 (完整调参映射见 autonomous_execution.md)

**重要**: 每次调参都要写进 changelog,报告里会列出"AI 调了哪些参数,为什么"。

### STEP F — 生成 .docx 报告

调 `examples/scripts/generate_report.py`:
```bash
python generate_report.py \
  --java GeneratedModel.java \
  --mph result.mph \
  --metrics metrics.json \
  --criteria acceptance.yaml \
  --debug-log debug_history.json \
  --out simulation_report.docx
```

报告标准结构 (5-8 页,见 `references/simulation_report_template.md`):
1. 摘要 (1页)
2. 模型描述 (1-2页)
3. 参数表 (0.5页)
4. 仿真结果 (2-3页,含曲线)
5. Debug 过程 (1页, 列出迭代历史)
6. 验收对标 (1页)
7. 结论与建议 (0.5页)

## 交付物清单

Autonomous Mode 完成后,工作目录应有:

```
working-dir/
├── GeneratedModel.java          # 完整可编译 .java
├── GeneratedModel.class         # 编译产物
├── result.mph                   # ★ 用户验收用
├── metrics.json                 # 提取的关键指标
├── debug_history.json           # 完整 debug 日志
├── run.log                      # COMSOL 运行日志
├── simulation_report.docx       # ★ 用户验收用
└── plots/                       # 报告引用的图
    ├── voltage_vs_time.png
    ├── temperature_profile.png
    └── ...
```

---

# Autonomous Mode 红线 (绝对禁止)

❌ **未与用户确认验收条件前编译/求解** — STEP A 是 hard gate
❌ **debug 超过 max_iterations 还在继续** — 必须停下报告
❌ **不记录 debug 历史** — 报告里"AI改了什么参数"是核心交付
❌ **修改超出"调参范围"的内容** — 不能为了通过验收偷偷改物理场结构
❌ **License 错误时反复重试** — 立即停,告诉用户检查 license
❌ **覆盖用户提供的参考 .java** — 永远生成新文件
❌ **为了用 MCP 而跳过 Java artifact** — Autonomous 交付必须保留可复现 `.java/.mph/log/metrics`
❌ **把 sim-cli 远程入口暴露到公共网络** — 只允许受控本机/内网试验

✅ **允许**: 自主调整数值参数 (Ds, k, h_amb, 网格密度, 时间步), 自主调整求解器配置
✅ **允许**: 在 debug 失败时主动检索官方文档 (见 `references/comsol_official_docs.md`)
✅ **允许**: 用 sim-plugin-comsol/MCP 做 inspect、shared Desktop、ad-hoc 结果读取和报告素材导出

---

# Snippet Mode 详细约定 (与 v2.1 保持一致)

## Step 2 — 建立心智地图 (grep 顺序)

| 步骤 | grep | 提取信息 |
|---|---|---|
| 1 | `Model model = ModelUtil.create` | 模型变量名 |
| 2 | `model.component(` | comp1,可能 comp2 |
| 3 | `.geom(` | geom1, 可选 geom2 |
| 4 | `model.param().set` | 参数命名习惯 |
| 5 | `physics().create` | liion + ht |
| 6 | `multiphysics().create` | ElectrochemicalHeating |
| 7 | `extrudedim` / `genext` / `aveop` | 多尺度耦合 |
| 8 | `model.study(.*).create` | 已有 Study |
| 9 | `feature("param")` | 已有扫描 |
| 10 | `ge1` / `GlobalEquations` | CP 模式标志 |
| 11 | `result().numerical/export` | 后处理风格 |

## Step 4 — 强制四段 header

```
**插入位置**: <section / 行号区间>
**新建tags**: <本片段会 create 的新 tag>
**依赖项**: <假设源文件已存在的 tag/参数>
**风险点**: <冲突, 单位, 6.4 API 差异>

```java
// 代码片段
```

**粘贴说明**: <如何插入>
```

## 六铁律

1. 不发明 tag (grep 现有再决定)
2. 保持依赖顺序 (参数→几何→物理场→Study)
3. 不删原注释
4. 单位用方括号 ([A]/[K]/[W])
5. 属性名不猜 (参照源文件)
6. 沿用代码风格

## 共同的硬约束 (两种模式都遵守)

❌ **永远不用 `ElectromagneticHeating`** 做电池电热耦合 → 用 `ElectrochemicalHeating`
❌ **永远不用 `model.batch()` API** 做参数扫描 → 用 `model.study("std1").feature("param")`
❌ **不用文本工具 / MCP standalone 读 DLP 加密 .mph** → 文本必乱码、MCP 报"文件已损坏";但 **sim-cli `exec`+`ModelUtil.load` 可读**(见上文已验证路径)
❌ **不猜 COMSOL API 方法名** → 必须从当前 .java 或官方文档找

---

# 引用的深度参考

| 需求 | 文件 |
|---|---|
| `.java`文件过大,AI读不动 ⚡ | `references/java_export_slimming.md` |
| `.java`整体结构 + grep定位法 | `references/comsol_java_anatomy.md` |
| LFP/Gr参数、节点tag、CP实现、LumpedBattery/SPM | `references/liion_lfp_reference.md` |
| 1D-3D多尺度耦合 | `references/multiscale_1d_3d_coupling.md` |
| 参数扫描5种模式 + CSV导出 + diff | `references/parameter_sweep_patterns.md` |
| MATLAB LiveLink驱动 + 优化器集成 | `references/matlab_livelink_patterns.md` |
| COMSOL 6.4特定API变化 | `references/comsol_64_api_notes.md` |
| Git/仓库结构 + 命名规范 + diff | `references/team_workflow.md` |
| GitHub Copilot `.github/instructions/` 配置 | `references/copilot_setup.md` |
| **★ 完整可编译 .java golden 模板 (Autonomous 起点)** | `references/complete_model_template.md` |
| **★ 自主执行管线 + 错误模式库 + debug 循环** | `references/autonomous_execution.md` |
| **★ 验收条件 YAML 框架 + 实验对标** | `references/acceptance_criteria.md` |
| **★ 官方文档检索 (ProgRefMan / Javadoc)** | `references/comsol_official_docs.md` |
| **★ 仿真报告 .docx 标准模板** | `references/simulation_report_template.md` |
