- [x] Verify that the copilot-instructions.md file in the .github directory is created.
- [x] Clarify Project Requirements
- [x] Scaffold the Project
- [x] Customize the Project
- [x] Install Required Extensions (none required)
- [x] Compile the Project
- [x] Create and Run Task (not needed)
- [x] Launch the Project
- [x] Ensure Documentation is Complete
- Work through each checklist item systematically.
- Keep communication concise and focused.
- Follow development best practices.
- 在编写任何代码之前，请先描述方案并等待批准。如果需求不明确，在编写任何代码之前务必提出澄清问题。
- 如果一项任务需要修改超过3个文件，请先停下来，将其分解成更小的任务。
- 编写代码后，列出可能出现的问题，并建议相应的测试用例来覆盖这些问题。
- 当发现 bug 时，首先要编写一个能够重现该 bug 的测试，然后不断修复它，直到测试通过为止。
- 每次我纠正你之后，就在 .github/copilot-instructions.md 文件中添加一条新规则，这样就不会再发生这种情况了。
- 使用 `stock-value-analyzer` 做股票价值分析时，最终报告必须导出为 Markdown 文件并保存到 `D:\Users\hez\Desktop\hithium-外移`，最终回复必须给出该文件绝对路径，不得只在对话中输出。
- 当 Notebook 重跑后现象未变化时，不要只看单元执行状态，必须核对 Notebook 当前绑定的函数对象是否已经切到最新模块实现，必要时显式 reload 模块并重新绑定符号。
- 在工作区不同区域工作前，先阅读对应的 AGENTS.md harness 文件（根目录有分域指导表）。
- 修改 PyBaMM 参数文件中的 OCP 时，必须同时覆盖基准键（`"Negative/Positive electrode OCP [V]"`）和分支键（`lithiation`/`delithiation`），因为 `ElectrodeSOHSolver` 内部只读基准键。
- 参数函数中不得对 PyBaMM 符号变量（如 T、sto）使用 Python `if/elif/else`，必须用 heaviside 写法；`np.exp` 也应改为 `pybamm.exp`。
- 反算初始浓度不要用 scipy 手工插值，必须用 `ElectrodeSOHSolver` 二分搜索 Q_Li 让 eSOH 自身给出目标容量。
- 实验与仿真对标作图时，实验横轴必须使用实验原始循环号，不得用加速等效圈数或按仿真上限截断造成“虚假拉伸”。
- 实验容量保持率对标时，必须先删除前期容量爬坡圈数，从容量最高点开始保留实验曲线，并以该峰值容量作为 100% 容量保持率基准；不得再用首圈直接归一化。
- 当某个模型选项在某温度下报错时，不得先假定它是温度特异问题；至少要在 25℃ 与目标温度各做一次最小复现，再判断是温度敏感还是参数/模型通用缺陷。
- 在 Windows 上排查 COMSOL 或其他本机软件时，不得只检查 C 盘或当前 PATH；至少同时检查常见安装盘符（如 D 盘）以及实际 bin 目录，再判断软件是否不存在。
- 判断 COMSOL Java 是否编译成功时，不得只看外层终端或工具返回的 Exit Code；必须同时检查编译器正文输出和 compile*.log，若出现 `Compilation failed`、`无法编译 java 文件` 或 `65535 bytes limit` 一律按编译失败处理。
- 迁移 Notebook 或历史工作区目录时，默认先直接迁移，不要为了“可能兼容”额外补入口文件、桥接脚本或兜底适配；兼容问题留到后续按具体文件逐个修复。
- 本机工作区文件可能受加密软件保护；如果 PowerShell/`Get-Content`/`cmd type` 看到 `%TSD-Header-###%` 或乱码，不要反复排查编码，改用 Python 读取/解析文件内容。
- 整合多个 Notebook 为 canonical 时必须保留旧文件功能并集；只允许把重复代码下沉到公共模块，不得删减分析章节、图表、实验对标、诊断或导出入口，未完成 feature parity 验证不得归档为完成。

---

## Karpathy-Inspired Coding Guidelines

Source: https://github.com/multica-ai/andrej-karpathy-skills — Bias toward caution over speed; for trivial tasks use judgment.

### 1. Think Before Coding — Don't assume. Don't hide confusion. Surface tradeoffs.
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First — Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes — Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.
- Remove imports/variables/functions that YOUR changes made unused; don't remove pre-existing dead code unless asked.
- The test: every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution — Define success criteria. Loop until verified.
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"
- For multi-step tasks, state a brief plan with verification checks per step.
- Strong success criteria let you loop independently; weak criteria ("make it work") require constant clarification.
