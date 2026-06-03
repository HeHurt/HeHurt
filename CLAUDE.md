## 文件加密绕过

    本机部署了 Trend Micro DLP（文件头 `%TSD-Header-###%`），claude.exe /
    PowerShell / ripgrep 等非白名单进程读取受保护文件会返回密文。

    - **读**：直接用 Read/Grep 会得到乱码。改用 Bash 调 python：
      `python -c "print(open('path', encoding='utf-8').read())"`
      （python.exe 在白名单，stdout 管道不经 DLP 过滤）
    - **写**：用 Write 工具写到 `C:\Users\hez\.claude\projects\...\scratch\`
      做中转，再用 python 读出并写入目标路径——python 写入会被 DLP 重新
      加密，与原文件保护级别一致。直接 Edit 受保护 .py 文件会失败。
    - **判断是否被加密**：文件前几字节包含 `%TSD-Header-###%` 即为密文。
    - **受影响范围**：BatteryProject 下所有 `.py` 和大部分 `.ipynb`。
      `.md` / `.toml` / `.bat` / `run_frontend.py` 是明文，可直接读写。

---

## Karpathy-Inspired Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Source: https://github.com/multica-ai/andrej-karpathy-skills

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.