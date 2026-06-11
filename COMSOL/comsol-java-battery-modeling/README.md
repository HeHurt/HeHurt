# comsol-java-battery-modeling v3.0

面向电池仿真工程师的 AI Skill,支持两种工作模式:
- **Snippet Mode** (v2.x): AI 输出代码片段,用户粘贴/编译/验证 (适合 Copilot Chat / Claude.ai / Cursor)
- **Autonomous Mode** (★ v3.0 新): AI 写完整 .java → 自主编译 → 自主求解 → 自主 debug → 出 .mph + 报告 (适合 Claude Code / Copilot Agent / Cursor Composer)

> **v3.0 vs v2.1**: 从"代码片段生成器"质变为"自主仿真 Agent"。新增完整执行管线、错误模式库、debug 循环、验收条件框架、自动 docx 报告。
>
> **v2.1 vs v2.0**: `.java` 导出瘦身工作流。
>
> **v2.0 vs v1.0**: 5步工作流纪律、Git/团队工作流、详细 Copilot 配置、明确"红线"清单。

## 配置假设

- COMSOL Multiphysics **6.4** (Windows 主,Linux/Mac 等价路径)
- 化学体系: **LFP / 石墨**
- 几何: **1D P2D** 或 **1D P2D + 3D热耦合**
- 工况: **CC恒流** + **CP恒功率** (储能场景)
- 不涉及老化建模

## 两种模式速览

### Snippet Mode 5+1 步工作流

0. **Pre-Step 1**: 检查 `.java` 体积,>1MB 先瘦身
1. 用户在 COMSOL 中导出 `.java`
2. AI grep 建立心智地图
3. AI 计划修改 (改/留/加/副作用 4清单)
4. AI 生成代码片段 (四段header + 六铁律)
5. 用户编译验证 + 回写

### Autonomous Mode 6 步工作流

A. **对齐**: 任务 + 验收条件 + COMSOL路径 + 预算 (用户确认)
B. **生成完整 .java** (带 main + study.run + save + 指标导出)
C. **编译** (comsolcompile, 自动 debug 编译错误)
D. **求解** (comsolbatch, 监控进度, 处理收敛失败)
E. **验收** (对照 acceptance.yaml, 不通过则物理调参回到 B)
F. **生成报告** (.docx, 5-8 页)

## 文件结构

```
comsol-java-battery-modeling/
├── SKILL.md                                    主skill (双模式)
├── README.md                                   本文件
├── examples/
│   ├── README.md
│   ├── github_instructions/
│   │   └── comsol.instructions.md             复制到 .github/instructions/
│   ├── github_prompts/
│   │   ├── cp-sweep.prompt.md                 Snippet模式: CP扫描
│   │   ├── c-rate-sweep.prompt.md             Snippet模式: C倍率扫描
│   │   ├── diff-models.prompt.md              Snippet模式: 对比两个.java
│   │   └── autonomous-sim.prompt.md   ★ v3.0  Autonomous模式触发
│   └── scripts/
│       ├── analyze_java_size.py               .java体积诊断 (v2.1)
│       ├── strip_java_for_ai.py               生成AI阅读专用版 (v2.1)
│       ├── comsol_batch_runner.py     ★ v3.0  主执行管线 (编译+求解+验收)
│       ├── parse_comsol_errors.py     ★ v3.0  错误日志解析器
│       └── generate_report.py         ★ v3.0  .docx报告生成器
└── references/
    ├── comsol_java_anatomy.md                  .java结构 + grep定位法
    ├── liion_lfp_reference.md                  LFP/Gr参数 + CP实现 + LumpedBattery/SPM
    ├── multiscale_1d_3d_coupling.md            1D P2D + 3D热耦合
    ├── parameter_sweep_patterns.md             参数扫描5模式 + CSV导出
    ├── matlab_livelink_patterns.md             LiveLink驱动 + 优化器集成
    ├── comsol_64_api_notes.md                  6.4 vs 5.x API差异
    ├── team_workflow.md                        Git/仓库/命名/diff
    ├── copilot_setup.md                        .github/instructions/ 详细配置
    ├── java_export_slimming.md                 .java瘦身完整工作流 (v2.1)
    ├── autonomous_execution.md         ★ v3.0  执行管线 + 错误模式库 + debug循环
    ├── acceptance_criteria.md          ★ v3.0  验收条件YAML框架 + 实验对标
    ├── comsol_official_docs.md         ★ v3.0  官方文档检索指南
    └── simulation_report_template.md   ★ v3.0  仿真报告标准模板
```

## 使用方法 (按工具)

### 在 Claude Code 中 (Autonomous Mode 推荐)

```bash
# 1. 安装 skill
mkdir -p ~/.claude/skills
cp -r ./comsol-java-battery-modeling ~/.claude/skills/

# 2. 安装 Python 依赖
pip install pyyaml pandas matplotlib python-docx

# 3. 在 Claude Code 里描述任务,例如:
#    "帮我用 COMSOL 6.4 自动跑通一个 LFP 280Ah 电芯的 1C 放电仿真,
#     验收要求容量>270Ah 和最高温度<60°C,跑完后给我 .mph 和 docx 报告"
#    Claude 会自动激活 Autonomous Mode
```

### 在 VS Code GitHub Copilot 中

**Snippet Mode** (默认):
```bash
mkdir -p .github/instructions .github/prompts
cp examples/github_instructions/comsol.instructions.md .github/instructions/
cp examples/github_prompts/*.prompt.md .github/prompts/
```

**Autonomous Mode** (Copilot Agent Mode 才支持):
- 切换到 Agent Mode
- 调用 `/autonomous-sim` prompt
- 按引导填入路径和验收条件

### 在 Cursor 中

把 `SKILL.md` 加到 `.cursorrules`,Composer Agent 模式可触发 Autonomous Mode。

## Python 依赖

仅 Autonomous Mode 和瘦身脚本需要:

```bash
pip install pyyaml pandas numpy matplotlib python-docx
```

(v2.1 的 `.java` 瘦身脚本只用 Python 标准库,无依赖)

## v3.0 核心新特性详解

### 1. 完整 .java 生成

不再只是片段,而是含 `main()` 的完整可编译文件,内置:
- `study.run()` 自动求解
- `model.save()` 自动输出 .mph
- 指标自动导出 CSV (`metrics.csv`, `voltage_vs_time.csv` 等)

### 2. 自主 debug 循环

```
编译 → 失败? → 错误模式库 → 修复 → 重试 (max 8 次)
                              ↓
                          求解 → 失败? → 收敛策略库 → 调求解器 → 重试
                                          ↓
                                      验证 → 不通过? → 物理调参表 → 调参 → 重试
                                                       ↓
                                                   生成 .docx 报告
```

详细错误模式库见 `references/autonomous_execution.md`。

### 3. 验收条件 YAML 框架

4 个层次,用户至少提供一项:
- **L1**: 求解通过
- **L2**: 物理合理性 (built-in)
- **L3**: 数值指标 (容量/温度/电压)
- **L4**: 实验数据对标 (RMSE/MAE/R2 vs CSV)

详见 `references/acceptance_criteria.md`。

### 4. 5-8 页自动 .docx 报告

7 个章节: 摘要 + 模型 + 参数 + 结果 + Debug过程 + 验收对标 + 结论。
含曲线图、表格、调参追溯。详见 `references/simulation_report_template.md`。

### 5. 官方文档检索集成

AI 遇到错误模式库覆盖不了的问题时,主动检索:
- `COMSOL_ProgrammingReferenceManual.pdf` (建模流程/批处理)
- `COMSOL_ReferenceManual.pdf` (命令/接口)
- Javadoc HTML (497个API类)

详见 `references/comsol_official_docs.md`。

## 红线汇总 (两模式通用)

| 红线 | 适用 |
|---|---|
| 永远不用 `ElectromagneticHeating` 做电热耦合,只用 `ElectrochemicalHeating` | 两种模式 |
| 永远不用 `model.batch()` 做参数扫描,用 `study.feature("param")` | 两种模式 |
| 永远不直接读 `.mph` (加密) | 两种模式 |
| 永远不发明 tag 或 API 方法名 | 两种模式 |
| 未确认验收条件前不编译求解 | Autonomous Mode |
| 不超 max_iterations | Autonomous Mode |
| 不修改物理场结构 (只调数值) | Autonomous Mode |
| 不覆盖用户参考 .java | Autonomous Mode |
| License 错误立即停止,不自动重试 | Autonomous Mode |

## 版本历史

- **v3.0 (2026-05-20)**: Autonomous Mode (闭环自动化), 4个新reference + 3个新Python脚本
- v2.1 (2026-05-18): `.java`瘦身工作流 + 诊断/剥离脚本
- v2.0 (2026-05-18): 5步工作流纪律 + 团队Git + Copilot详细配置
- v1.0 (2026-05-15): 初版 LFP/Gr 6.4 + CC/CP + 1D+3D + LiveLink

## 局限

- 不支持 `.mph` 直接读取(公司加密策略)
- 不涉及老化建模(SEI/锂沉积/机械)
- AI 自主调参限于数值参数(扩散系数、反应速率、求解器),不修改物理场结构
- Autonomous Mode 需要本地 COMSOL 6.4 + bash 工具环境
- LiveLink 集成路径暂未自动化(v3.0 只走 comsolcompile/comsolbatch)
