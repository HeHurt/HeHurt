---
name: wechat-article-export
description: "Use when the user asks to export an answer, explanation, notebook conclusion, research note, or technical write-up into a WeChat official account article / 公众号文章 / 微信公众号可发布文件, especially when they need stable formulas, copy-ready formatting, or a file they can directly copy into the editor."
---

# WeChat Article Export

## Purpose

Convert an existing answer or technical note into a WeChat-official-account-ready file that is safe for copy/paste and does not rely on LaTeX rendering.

## Output Rules

Always produce a file, not just chat text.

Default output location:
- `docs/wechat/`

Default output format:
- `.html` with inline CSS for stable typography and copy-friendly layout

Only switch formats if the user explicitly asks for another one.

If the environment already has a reliable Word generation path available, prefer also creating a companion `.docx` for the same article when the user asks for Word import, document upload, or office-friendly delivery.

## Formula Rules

WeChat official account editors do not reliably render LaTeX, KaTeX, or MathJax.

Therefore:
- Do not output raw LaTeX as the final article formula format.
- Convert formulas into stable text-form equations.
- Prefer simple ASCII or plain-text mathematical notation inside styled blocks.
- Keep variable names unambiguous, for example:
  - `j0_plating = F * k_pl * c_e`
  - `j_plating = - j0_plating * exp(alpha_pl * F * eta_plating / (R * T))`
- If the original math is long, split it across multiple short formula blocks.

## Structure Rules

Unless the user asks otherwise, use this article structure:

1. Title
2. Optional alternate titles
3. Short lead paragraph
4. Optional summary / abstract
5. Key conclusion section
6. Mechanism explanation sections
7. Engineering impact or parameter interpretation
8. Practical tuning or usage advice
9. Optional interaction closing line
10. Short footer note

When the user asks for publishing help, also generate these extra fields inside the file or at the top of the article:
- 3 candidate titles
- 1 short abstract
- 1 opening guide paragraph suitable for public readers
- 1 ending interaction sentence suitable for公众号留言引导

## Style Rules

- Use concise Chinese suitable for technical public articles.
- Keep paragraphs short.
- Use clear section headings.
- Highlight one-line conclusions in callout blocks.
- Avoid overly academic citation formatting unless the user asks for references.
- If a formula appears, explain its engineering meaning immediately after it.

## Copy-Ready Constraints

- Assume the user wants to open the file and copy it directly into WeChat.
- Favor warm, clean inline styles and conservative layout.
- Avoid complex tables unless the content is inherently tabular.
- Avoid any dependency on external CSS, scripts, web fonts, or CDN assets.

## Batch Export Rules

If the user asks to export a whole round of Q&A, a notebook discussion, or a series of related explanations:
- Split the content into multiple articles by topic, not by raw chat turns.
- Prefer one strong topic per article.
- Use consistent visual style across the set.
- Name files with a clear series slug, for example:
  - `topic-a-wechat.html`
  - `topic-b-wechat.html`
  - `topic-c-wechat.html`
- If helpful, create a lightweight manifest or list in the final response summarizing the set.

## Word Export Rules

When the user asks for Word import or document upload:
- If `python-docx` or an equivalent reliable path is available, create a `.docx` companion file.
- Preserve headings, callouts, formula blocks, and bullet lists in the Word version.
- Do not rely on Word equation objects unless explicitly requested; keep formulas as stable text-form blocks.
- If a true `.docx` cannot be generated reliably, fall back to `.rtf` or Word-friendly `.html`, and tell the user clearly.

## File Naming

Use a descriptive slug ending with `-wechat.html` unless the user specifies a name.

Examples:
- `docs/wechat/sei-aging-interpretation-wechat.html`
- `docs/wechat/plating-overpotential-wechat.html`

## Workflow

1. Identify the exact source content the user wants exported.
2. Rewrite it into article form rather than dumping raw Q&A.
3. Replace all LaTeX-style formulas with stable text-form equations.
4. If useful, prepare alternate titles, summary, opening guide paragraph, and closing interaction sentence.
5. Create the output file under `docs/wechat/`.
6. If Word import was requested and the environment supports it, create a companion `.docx`.
7. Tell the user what files were created and whether they are intended for direct copy, Word import, or secondary tools.

## When The User Wants "格式和公式都正确"

Interpret that as:
- no raw LaTeX in the final deliverable
- no dependence on notebook rendering
- no dependence on VS Code markdown preview extensions
- the file should remain readable and mathematically unambiguous in plain browser rendering

## When The User Wants "可以直接发公众号"

Interpret that as:
- prioritize direct copy into the公众号编辑器
- keep the layout conservative and robust
- generate polished section headings and a publication-ready opening
- avoid any raw chat phrasing such as “你问我” or “上面提到” unless explicitly desired
- prefer short, publishable paragraphs over Q&A fragments

## Do Not

- Do not leave formulas in `$...$` or `$$...$$` form in the exported file.
- Do not create more than the minimum necessary files.
- Do not assume WeChat supports HTML upload; optimize for opening and copying rendered content unless the user asks for another pipeline.