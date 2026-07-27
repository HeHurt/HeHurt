---
name: comsol-java-battery-modeling
description: 以 Codex 为核心审计、修改、运行和验证 COMSOL Multiphysics 6.4 锂离子电池模型。用于现有 .mph 模型审计、差异比较和另存修改，COMSOL 导出 .java 修改，liion/P2D、1D-3D 电化学-热耦合、CC/CP 工况、参数扫描、comsolcompile/comsolbatch 自动化、求解器调试、结果提取和仿真报告。仅需 MATLAB LiveLink 时改用 comsol-livelink-matlab skill。
---

# COMSOL 电池模型自动化 v4.0

以 Codex 作为唯一面向用户的入口和编排核心：理解需求、选择路线、控制执行、判断物理合理性、验证结果并完成交付。把 sim-cli、ModelUtil、COMSOL Desktop/MCP、`comsolcompile`、`comsolbatch` 和 Python 脚本视为底层执行器，不要求用户自行选择或调用。

用户只需提供模型路径和目标。不要要求普通用户准备 JSON 或运行命令；仅在调试底层工具时暴露手动操作。

## 先选路线

| 输入与目标 | 路线 | 按需读取 |
|---|---|---|
| 已有 `.mph`：检查、比较、诊断、修改 | MPH Direct Mode：sim-cli + `ModelUtil` | `references/mph_runtime_workflow.md` |
| 已有导出 `.java`：理解或局部修改 | Java Snippet Mode | `references/comsol_java_anatomy.md` 及相关领域资料 |
| 新建、运行并交付 `.java/.mph/metrics/report` | Autonomous Java Mode | `references/autonomous_execution.md`、`references/acceptance_criteria.md` |
| MATLAB 调度或优化器集成 | `comsol-livelink-matlab` | 不在本 skill 重复 LiveLink 流程 |

选择能完成任务的最小路线。不要机械串联 Java、sim-cli、MCP 和 Desktop；只有当前路线缺少必要观察或操作能力时才增加工具。

## 权限与确认

- 目标明确的只读检查：直接执行。
- 修改现有模型：保留源文件并另存；只有物理选择会实质改变结果时才询问。
- 完整建模、标定或长时间计算：先确认验收条件、工作目录、运行预算和允许调整的物理参数。
- 用户仅要求诊断：提供证据，不自动修改。

## MPH Direct Mode

### 标准闭环

```text
审计 audit → 差异 diff → 另存修改 patch → 回读 verify → 最小求解 smoke → 正式计算
```

使用 `scripts/mph_tool.py` 的五个动作：

| 动作 | 用途 |
|---|---|
| `audit` | 读取模型结构及指定参数、变量、物理节点、研究和探针 |
| `diff` | 离线比较两个审计 JSON 的新增、删除和变化路径 |
| `patch` | 执行限定修改、另存 `.mph`，随后自动回读断言 |
| `verify` | 不修改模型，只验证保存后的表达式和节点 |
| `smoke` | 在内存中缩短工况并运行最小稳态或瞬态，提取关键指标 |

### 快速执行

1. 先运行 `uv run sim --json ps`，复用健康会话。
2. 没有健康会话时再连接：

```powershell
uv run sim --json --no-interactive connect --solver comsol --ui-mode no_gui
```

3. 把任务 JSON 保留在 run 目录，并复制到 `.sim\mph_tool_config.json`；通过会话执行 `scripts/mph_tool.py`。配置 schema 和命令见 `references/mph_runtime_workflow.md`。
4. 顺序加载大模型；完成后用 `ModelUtil.remove(tag)` 释放模型，并断开本任务创建的会话。

只有连接或 solver discovery 失败时才运行 `uv run sim check comsol` 和 `uv run sim plugin doctor comsol --deep`。

### 必须遵循的诊断顺序

1. 识别 component、physics、study、dataset、probe 和 selection。
2. 从边界条件追踪表达式到真实消费者；变量存在不代表物理场正在使用它。
3. 只查询与问题相关的属性。
4. 明确区分已确认事实、推断和未验证项。
5. 修改后另存、卸载、重载并断言保存表达式。
6. 修改物理或求解表达式后，先跑最小 smoke case，再进行完整扫描。

## 电化学—热耦合检查清单

处理电流、产热、接触电阻或温度耦合时，逐项检查：

- P2D 端电流、3D 极耳电流密度和后处理使用同一带符号电流源。
- 接触电阻压降只修正一次，`I^2R` 接触热只计入一次。
- 热映射满足积分功率守恒：`P_to_ht = P_p2d + P_contact + P_metal`，误差在数值容差内。
- P2D 与 3D 金属热源的 domain selection 不意外重叠。
- `Ds_neg`、`Ds_pos`、`k_neg`、`k_pos` 的物理属性真正引用目标动态温度变量，而非同名全局参数。
- 体积产热乘物理体积一次，拒绝二次层厚加权。
- 初始 SOC、OCV 标定、端电压截止和接触压降修正相互独立。

`liion` 域使用电化学产热。独立的 3D 电子导体使用模型中已验证的焦耳热机制，例如适当的 multiphysics coupling 或显式 `ec.Qh`，并证明 domain 不重复计热。不要笼统禁止所有 Electromagnetic/Joule Heating coupling。

## Java Snippet Mode

1. 先检查文件体积；导出文件超过 500 KB 时读取 `references/java_export_slimming.md`。
2. 用 `rg` 定位 parameter、component、geometry、physics、coupling、study、solver 和 result。
3. 复用现有 tag 和导出的 API property，不发明 tag 或方法名。
4. 交付代码片段时说明插入位置、新 tag、依赖、风险和粘贴方法。
5. 保持依赖顺序：参数 → 几何 → 物理 → 网格 → 研究 → 结果。

## Autonomous Java Mode

使用 `references/complete_model_template.md` 作为完整模型骨架，通过 `examples/scripts/comsol_batch_runner.py` 逐轮完成编译、求解和验收。每轮读取 `cycle_result.json`，只修改有证据支持的源代码或配置，并控制迭代预算。

默认用 `comsolcompile.exe` 编译、`comsolbatch.exe` 求解。不得覆盖用户源 `.java` 或已成功的 `.mph`。

生成报告时使用脚本真实接口：

```powershell
python examples/scripts/generate_report.py `
  --java GeneratedModel.java `
  --metrics metrics.csv `
  --criteria acceptance.yaml `
  --debug-log debug_history.json `
  --workdir . `
  --out simulation_report.docx
```

报告脚本不接受 `--mph`；先把结果导出为 CSV。

## 本机 DLP 规则

- DLP 包装的 `.mph` 可由运行在 `comsolmphserver.exe` 中的 COMSOL 后端加载；离线读取器可能把它判断为无效文件。
- `.java` 若以 `%TSD-Header-###%` 开头，使用已批准的 `Code.exe` bridge 或其他验证过的白名单进程；不得编辑密文字节。
- 非简单 Python 优先使用 `exec --file`，避免 PowerShell 内联转义。
- 不同时在内存中保留多个大型 `.mph`；顺序审计后离线比较 JSON。

## 安全与交付

- 除非用户明确要求覆盖，否则永远另存 `.mph` 和 `.java`。
- 从模型或 named selection 解析实体，不猜 domain、boundary 或 edge ID。
- 物理参数显式携带单位。
- 记录源路径、输出路径、修改操作、smoke 配置、指标和错误。
- 长求解采用可取消执行并持续汇报进度。
- License 错误视为阻断，不循环重试。
- 正常交付修改文件、差异说明、回读结果、最小求解指标和功率/能量守恒结论；不要把 smoke 成功表述成完整扫描完成。

## 参考资料路由

只读取任务需要的资料：

| 需求 | 资料 |
|---|---|
| `.mph` 审计、比较、修改、验证、smoke 和 JSON schema | `references/mph_runtime_workflow.md` |
| Java 结构和定向检索 | `references/comsol_java_anatomy.md` |
| COMSOL 6.4 API | `references/comsol_64_api_notes.md` |
| LFP/石墨参数和 `liion` 模式 | `references/liion_lfp_reference.md` |
| 1D–3D 耦合 | `references/multiscale_1d_3d_coupling.md` |
| 参数扫描 | `references/parameter_sweep_patterns.md` |
| 完整 Java 模板 | `references/complete_model_template.md` |
| 编译、求解和调试 | `references/autonomous_execution.md` |
| 验收条件 | `references/acceptance_criteria.md` |
| 官方 API 检索 | `references/comsol_official_docs.md` |
| 报告布局 | `references/simulation_report_template.md` |
| 团队路径和产物 | `references/team_workflow.md` |

## 交付前验证

- 重载每个保存的 `.mph`，断言请求修改的表达式和节点。
- 物理修改后运行最小有效稳态或瞬态。
- 从 smoke solution 读取请求指标。
- 修改本 skill 后运行：

```powershell
$env:PYTHONUTF8='1'
python C:\HithiumSSD\hithium\skills\.system\skill-creator\scripts\quick_validate.py C:\HithiumSSD\hithium\skills\comsol-java-battery-modeling
python -m pytest C:\HithiumSSD\hithium\skills\comsol-java-battery-modeling\tests -q
```
