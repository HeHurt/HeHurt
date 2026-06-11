# GitHub Copilot `.github/instructions/` 详细配置

本文档面向**GitHub Copilot in VS Code**用户,提供把本skill集成到Copilot的多种配置方式,以及最佳实践。

> Cursor用户/JetBrains AI Assistant用户/Continue用户的配置思路类似,核心都是"把SKILL.md内容投放到AI上下文",细节有别。

---

## 1. 三种集成方式总览

GitHub Copilot 提供三种官方instruction机制 (来自GitHub Docs "Customize Copilot's responses"):

| 机制 | 文件路径 | 作用范围 | 适用场景 |
|---|---|---|---|
| **A. 仓库级总指令** | `.github/copilot-instructions.md` | 全仓库,所有Copilot Chat会话 | 整个仓库就是COMSOL项目时 |
| **B. 按文件类型** | `.github/instructions/*.instructions.md` + frontmatter `applyTo` | 匹配glob的文件 | 大仓库,只有部分文件是.java |
| **C. 可复用Prompt** | `.github/prompts/*.prompt.md` | 显式 `/prompt-name` 调用 | 高频重复任务(如"加CP工况"、"扫描C倍率") |

**推荐组合**: B + C。B提供"打开`.java`时自动加载的规范",C提供"按需调用的高频任务模板"。

---

## 2. 方式A: 仓库级总指令 (最简单)

**何时用**: 整个仓库就是COMSOL battery项目,所有目录都和电池仿真相关。

### 配置

在仓库根创建 `.github/copilot-instructions.md`:

```bash
mkdir -p .github
cat <<'EOF' > .github/copilot-instructions.md
<!-- 把 comsol-java-battery-modeling/SKILL.md 的全部内容粘贴到这里 -->
EOF
```

实操:

```bash
# 假设你已经把skill仓库克隆到 .skills/comsol-java-battery-modeling/
cp .skills/comsol-java-battery-modeling/SKILL.md .github/copilot-instructions.md
```

### 验证生效

- 打开任意`.java`文件
- 在Copilot Chat里问个简单问题: "这个模型用了什么物理场?"
- Chat回答的右上角应该看到一个**说明指令已加载**的指示(具体UI元素会随Copilot版本变化)
- 如果Copilot开始按skill的"先grep建立心智地图"流程操作,说明生效

### 缺点

- **全仓库生效** — 如果你的仓库还包含Python数据分析脚本、文档等,Copilot处理这些非COMSOL文件时也会加载这一大段COMSOL规则,**污染上下文**
- 单文件,所有内容都加载 — 即使你只想改一个简单参数,8K字的SKILL.md也全部进入context window

---

## 3. 方式B: 按文件类型作用域 (推荐)

**何时用**: 大仓库,COMSOL`.java`只是其中一部分。

### 配置

创建 `.github/instructions/comsol.instructions.md`:

```markdown
---
applyTo: "**/*.java"
---

<!-- 这里粘贴 SKILL.md 的内容 -->
```

或者更精确地匹配COMSOL`.java`目录:

```markdown
---
applyTo: "models/java/**/*.java"
---

<!-- SKILL.md 内容 -->
```

### `applyTo` glob语法常用模式

| 模式 | 匹配 |
|---|---|
| `**/*.java` | 所有.java文件 |
| `models/java/**/*.java` | 仅models/java下的.java |
| `**/cell_LFP_*.java` | 所有LFP电芯模型 |
| `{models/java,backups}/**/*.java` | 多个目录 |
| `**/*.{java,m}` | .java和MATLAB .m都生效 (适合LiveLink也用skill) |

### 多文件分工 (高级)

可以把skill拆分到多个`instructions`文件,各自`applyTo`不同范围:

```
.github/instructions/
├── comsol-java.instructions.md           applyTo: "**/*.java"
├── matlab-livelink.instructions.md       applyTo: "**/*.m"
└── batch-scripts.instructions.md         applyTo: "scripts/**/*"
```

每个文件粘贴skill里**相关的部分**。例:
- `comsol-java.instructions.md`: SKILL.md主体 + `liion_lfp_reference.md` + `comsol_64_api_notes.md`
- `matlab-livelink.instructions.md`: SKILL.md简化版 + `matlab_livelink_patterns.md`

这样Copilot处理`.java`时不加载LiveLink内容,处理`.m`时不加载Java API细节,**context更聚焦**。

### `comsol.instructions.md` 完整推荐模板

```markdown
---
applyTo: "**/*.java"
description: COMSOL Multiphysics 6.4 battery model Java workflow
---

# COMSOL Java Battery Modeling Instructions

You are helping with COMSOL 6.4 Li-ion battery models (LFP/Graphite). Each .java file
in this repo is exported from an encrypted .mph file. You CANNOT read the .mph; only
the .java is your source of truth.

## Mandatory Workflow

When asked to modify a model, execute these 5 steps **in order**. Do NOT skip Step 2-3.

### Step 1 (already done by user)
The user has exported .mph → .java via COMSOL Desktop.

### Step 2: Build mental map BEFORE coding
Use grep to locate:
- `Model model = ModelUtil.create` (model variable name)
- `model.component(` (components, usually comp1 [+ comp2 for 3D thermal])
- `model.param().set` (parameters and naming convention)
- `physics().create` (which physics interfaces exist; expect liion and ht)
- `multiphysics().create` (couplings; expect ElectrochemicalHeating)
- `extrudedim` / `genext` / `aveop` (multiscale 1D-3D coupling indicators)
- `model.study(.*).create` (existing studies)
- `feature("param")` (existing parameter sweeps)
- `ge1` / `GlobalEquations` (CP mode indicator)
- `result().numerical` (postprocessing conventions)

Summarize in 1-2 sentences what the model is.

### Step 3: Plan before generating code
List 4 things:
1. **What to change** — which tags
2. **What to preserve** — explicit list
3. **What to add** — new tag names (grep existing first, increment number)
4. **Side effects** — broken dependencies?

Ask user to confirm before Step 4.

### Step 4: Generate snippet (NOT full file)
Strict header format:
- **插入位置 (Insert location)**: section/line range
- **新建tags (New tags)**: list
- **依赖项 (Dependencies)**: tags assumed to exist
- **风险点 (Risks)**: potential conflicts

Then ```java code block```.

Then **粘贴说明 (Paste instructions)**.

### Step 5 (user does this)
User runs `comsolcompile` and verifies in COMSOL.

## Hard Rules

1. NEVER invent tags — grep source first
2. NEVER guess COMSOL API method names — reference existing usage in the file
3. ALWAYS use COMSOL 6.4 syntax (not 5.x):
   - `model.physics().create("liion", "LithiumIonBattery", ...)` (NOT "liionbattery")
   - `physics("liion").prop("ModelInputs").set(...)` (NOT direct set for model inputs)
   - `Eeq` (NOT `Ee` for equilibrium potential)
4. NEVER use `ElectromagneticHeating` for battery thermal coupling
   — use `ElectrochemicalHeating`
5. NEVER use `model.batch()` for parameter sweep
   — use `model.study("std1").feature("param").set("pname", ...)`
6. CP (constant power) is NOT a native feature: implement via Global Equations
7. All numeric values use bracket units: "280[A]", "298.15[K]", "560[W]"
8. Comment in Chinese OR English following the source file's existing style

## LFP/Graphite Parameter Sanity Check

Reject snippet if:
- V_max > 3.7V or V_min < 2.4V (LFP windows are tighter than NCM)
- Ds_pos > 1e-15 m²/s (LFP diffusion is 2-3 orders slower than NCM)
- rp_pos > 2e-6 m (LFP particles are smaller than NCM, typically 0.1-1µm)
- Suggested OCV uses polynomial — LFP needs interpolation or Sphan-Newman form

## When in Doubt

If you cannot confirm a tag/parameter exists in source, STOP and ask user to share
that section. Do not guess. A wrong tag fails compilation; an invented Java method
call fails immediately. The cost of asking is far less than the cost of guessing.

## References to Load on Demand

(For complex tasks, ask user to share the relevant reference doc:)
- liion_lfp_reference.md — LFP/Gr-specific parameters and CP Global Equation
- multiscale_1d_3d_coupling.md — for models with comp2 (3D thermal)
- parameter_sweep_patterns.md — for parameter sweeps and CSV export
- matlab_livelink_patterns.md — for MATLAB-driven workflows
- comsol_64_api_notes.md — for 6.4-specific API
- team_workflow.md — for git/repo conventions
```

---

## 4. 方式C: 可复用 Prompt 模板 (`.github/prompts/`)

**何时用**: 团队反复做同类修改(如"加CP工况"、"扫描C倍率"、"基线NCM转LFP")。

### 配置

创建 `.github/prompts/<task-name>.prompt.md`:

#### 示例1: `cp-sweep.prompt.md` — 加CP扫描

```markdown
---
mode: agent
description: 在现有CC模型上加CP恒功率工况 + 功率扫描
tools: ['codebase']
---

# Task: 加CP恒功率工况

请按 `comsol.instructions.md` 的5步工作流,在当前打开的 .java 文件上加CP工况:

## 用户输入
- 功率范围: ${input:powerRange:280 560 1120 [W]}
- 截止电压: ${input:vMax:3.65}V (上) / ${input:vMin:2.5}V (下)

## 执行步骤
1. grep 已有的 ecs1 / ge / GlobalEquations,确认源文件是否已有CP配置
2. 如果没有,生成3段代码片段:
   - **片段A**: 在 `model.param()` 段加 P_app, V_max, V_min参数
   - **片段B**: 在 physics段后加 Global Equations节点 `ge1` 求解 I_app_var
   - **片段C**: 修改 ecs1.I_el 引用 I_app_var,在 std1.time 加 Stop Condition
3. 在 std1 加 param sweep 扫 P_app
4. 每个片段必须有完整的"插入位置/新建tags/依赖项/风险点/粘贴说明"header

## 必读参考
请加载 `references/liion_lfp_reference.md` 的 "恒功率(CP)实现" 章节作为参照。
```

使用: 在Copilot Chat里输入 `/cp-sweep` 即可触发,Copilot会询问输入参数。

#### 示例2: `c-rate-sweep.prompt.md` — C倍率扫描

```markdown
---
mode: agent
description: 在现有Study上加C倍率参数扫描 + CSV导出
---

# Task: C倍率扫描

为当前 .java 加一组C倍率扫描:

## 用户输入
- C倍率列表: ${input:crateList:0.2 0.5 1 2 3}
- 输出指标: ${input:metrics:min(liion.E_cell), max(T), max(T)-min(T)}

## 执行步骤
1. 按 instructions.md 的Step 2 建立心智地图
2. 检查 std1 是否已有 feature("param") — 决定 .create 还是直接 .set
3. 生成片段:
   - **片段A**: param sweep 配置
   - **片段B**: 后处理 Global Evaluation + Table导出CSV
4. 给出粘贴位置

参考 `references/parameter_sweep_patterns.md` "模式1: 单参数 CC扫描"。
```

#### 示例3: `diff-models.prompt.md` — 对比两个模型

```markdown
---
mode: ask
description: 对比两个 .java 找差异,按物理意义解读
tools: ['codebase']
---

# Task: 对比两个 COMSOL .java 模型

## 用户输入
- v1文件: ${file:v1File:models/java/}
- v2文件: ${file:v2File:models/java/}

## 输出要求
按 `references/team_workflow.md` 的"对比两个 .java 找差异" 章节标准输出:

1. **参数变化** (`model.param().set`)
2. **物理场变化** (`physics()`)
3. **几何变化** (`geom()`)
4. **Study/Solver变化** (`study()` / `sol()`)
5. **后处理变化** (`result()`)
6. **物理意义解读** (推断,标注为AI推测)
```

#### 示例4: `convert-to-livelink.prompt.md` — 转LiveLink

```markdown
---
mode: agent
description: 把当前 .java 的Study改成等效的MATLAB LiveLink .m脚本
---

# Task: 转LiveLink

参考 `references/matlab_livelink_patterns.md`,把当前 .java 的Study逻辑改写成MATLAB脚本:

1. 读取 .java 找参数定义、Study类型、扫描配置(如有)
2. 生成 .m 脚本,包含:
   - `mphload` 加载 .mph
   - 参数循环
   - `model.study('std1').run()` 求解
   - `mpheval` 提取结果
   - 保存到 .mat 或 CSV
3. 处理异常的 try-catch 模式

输出完整 .m 文件,不是片段。
```

---

## 5. 在 VS Code Settings 中的辅助配置 (可选)

在 `.vscode/settings.json` 加补充指令,作用于代码生成的所有交互(包括内联自动补全,不只是Chat):

```json
{
  "github.copilot.chat.codeGeneration.instructions": [
    {
      "file": ".github/instructions/comsol.instructions.md"
    }
  ],
  "github.copilot.chat.testGeneration.instructions": [
    {
      "text": "Tests for COMSOL Java should be via comsolcompile syntax check + load in COMSOL Desktop verification, not JUnit."
    }
  ],
  "github.copilot.chat.commitMessageGeneration.instructions": [
    {
      "text": "Follow the commit message template from team_workflow.md: <model_name>: <one-line summary> + multi-line details + affected tags + COMSOL version."
    }
  ]
}
```

---

## 6. Copilot Chat 里临时引用 reference 文档

即使配置了 instructions,有时想让 Copilot 加载某个 reference 文档:

```
#file:references/liion_lfp_reference.md
请帮我把ecs1的I_el改成CP模式的I_app_var,并加上Global Equation
```

`#file:` 是 Copilot Chat 的官方语法,会把整个文件投放到context。可以一次引用多个:

```
#file:references/liion_lfp_reference.md
#file:references/parameter_sweep_patterns.md
#file:models/java/cell_LFP_280Ah_v2.java

请按 cell_LFP_280Ah_v2.java 的风格,生成一段在 1D+3D 模型上扫 P_app 的代码片段
```

---

## 7. 实际部署建议 (按团队成熟度)

### 阶段1: 个人试用 (1-2人)
- 方式A(仓库级instructions)直接铺
- 测试1-2周,记录Copilot经常做错的地方
- 把根因写进 instructions 的Hard Rules

### 阶段2: 小组推广 (3-10人)
- 切换到方式B(按文件类型)
- 加 `applyTo: "**/*.java"` 避免污染其他文件
- 把高频任务做成方式C(prompts)

### 阶段3: 团队标准 (10+人)
- skill仓库独立,作为submodule引入各个模型仓库
- CI检查 `.github/instructions/` 是否最新
- 月度回顾失败case,迭代instructions

---

## 8. 常见问题

### Copilot 没按 instructions 操作?

可能原因:
1. **文件路径不对**: 确认是 `.github/copilot-instructions.md` (注意是`.github`不是`.vscode`)
2. **Copilot版本太老**: VS Code Copilot extension版本需要支持custom instructions (一般2024年中后)
3. **被`applyTo`过滤掉了**: 检查当前文件是否匹配glob
4. **Context window被占满**: SKILL.md太长 + 当前文件太长 → 截断;考虑拆分instructions

### Instructions 怎么调试?

在Copilot Chat里直接问:
```
你当前加载了哪些指令文件?这些指令对.java文件有什么具体要求?
```

Copilot会回答它感知到的指令(粗略,不一定准),帮你判断是否生效。

### Prompts 和 Instructions 怎么配合?

- **Instructions**: 始终生效,定义"做事的方式"
- **Prompts**: 显式调用,定义"做什么具体任务"

Prompt 内部可以引用 Instructions 的规则: "按 instructions.md 的5步工作流执行..."。

### Copilot 还是会发明tag?

把警告做更直白:

```markdown
## CRITICAL: Tag Hallucination Prevention

Before writing ANY code with a new tag name:
1. Run `grep '"std[0-9]"' source.java` and tell the user the result
2. ONLY THEN propose a new tag (next integer)
3. If you find yourself writing a tag without having grepped, STOP and grep first

If user asks for "添加扫描" without specifying tag, you MUST ask:
"已有的 study tags 是 [X, Y, Z]。我建议新建 stdN。可以吗?"
```

LLM对显式步骤化的指令比"提醒不要XX"响应更好。

---

## 9. 与本skill其他文件的关系

```
本文档 (copilot_setup.md)
  ├─ 告诉你: 怎么把 SKILL.md 部署到 Copilot
  ├─ 引用: SKILL.md → 部署成 .github/copilot-instructions.md 或 .github/instructions/comsol.instructions.md
  ├─ 引用: references/*.md → 通过 #file: 临时引用,或拆分到不同 instruction 文件
  └─ 引用: team_workflow.md → git 工作流配套
```

部署完成后,典型工作流:
1. 用户在 VS Code 打开 `.java` → Copilot 自动加载 `comsol.instructions.md`
2. 用户问 "加一段CP扫描" → Copilot 按 instructions 的5步工作流操作
3. 复杂场景用 `/cp-sweep` 触发 prompt 模板
4. 需要细节时用 `#file:references/liion_lfp_reference.md` 临时加载
