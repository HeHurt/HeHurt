---
name: wechat-publisher
description: "Publish Markdown articles to a WeChat Official Account (微信公众号 / 公众号) with automatic inline-style formatting, no manual typesetting needed. Use this skill when the user asks to 发公众号, 发布到公众号, 自动发公众号, 写公众号文章, 把这篇发到公众号, push to WeChat MP, publish a WeChat article, or otherwise create / draft / publish content for a 微信公众号. Covers Markdown to WeChat HTML conversion, cover and inline image upload, draft creation (draft/add), and optional mass send (freepublish/submit) via the WeChat MP API."
---

# Wechat Publisher (公众号自动发布)

## Overview

Turn a Markdown file into a clean, on-brand WeChat Official Account article and publish it
— as a draft or a direct mass send — through the WeChat MP API. Automatic typesetting means
a user who "can't format" still gets a polished article straight from plain Markdown.

## When to use

- User says "发公众号" / "发布到公众号" / "自动发公众号" / "把这篇发到公众号".
- User wants to draft or publish WeChat MP content from Markdown.
- User mentions WeChat Official Account publishing or automation.

## Prerequisites

- A registered 微信公众号 (订阅号 / 服务号) with AppID + AppSecret
  (公众平台 → 设置与开发 → 基本配置).
- The execution environment must reach `https://api.weixin.qq.com`, and the machine's egress
  IP must be in the MP platform IP whitelist (设置与开发 → 基本配置 → IP 白名单).
- Python 3 with `requests`. JSON calls fall back to `urllib`; file upload needs `requests`.

## Workflow

1. Ensure the article is Markdown. A top frontmatter block is supported:

   ```markdown
   ---
   title: 文章标题
   author: 作者
   digest: 摘要（卡片上显示的一行）
   cover: cover.png
   ---

   # 正文 …
   ```

2. Use the existing local credentials file:

   ```text
   C:\Users\hez\WorkBuddy\Claw\wechat-publisher\config.json
   ```

   Always pass this path explicitly with `--config`. Do not search the skill directory,
   AppData, or other locations, and do not ask the user for credentials unless this file is
   missing, unreadable, or rejected by the WeChat API. Never print `appid` or `appsecret`.

3. Preview first — no network, safe to inspect layout:

   ```bash
   python scripts/wechat_publisher.py article.md --config "C:\Users\hez\WorkBuddy\Claw\wechat-publisher\config.json" --dry-run
   ```

   Writes `preview.html` (open in a browser to check the mobile layout) and prints the
   parsed title / author / digest / cover.

4. Create a draft:

   ```bash
   python scripts/wechat_publisher.py article.md --config "C:\Users\hez\WorkBuddy\Claw\wechat-publisher\config.json"
   ```

5. Create a draft and mass-send in one step:

   ```bash
   python scripts/wechat_publisher.py article.md --config "C:\Users\hez\WorkBuddy\Claw\wechat-publisher\config.json" --publish
   ```

## Notes / gotchas

- WeChat only accepts inline styles. The converter emits **zero style blocks**; the brand
  accent is WeChat green `#07c160`.
- Code blocks must use one block-level HTML element per source line and explicit `&nbsp;`
  indentation. Do not rely on literal newlines plus `white-space: pre-wrap`: the WeChat
  draft editor normalises those newlines to spaces and destroys Python indentation.
- `access_token` is cached locally (~7200s) in `token.json` next to the script.
- A cover image is required by `draft/add` (`thumb_media_id`). Pass a local `cover` path
  (auto-uploaded) or a pre-uploaded `cover_media_id`.
- Local images in the Markdown are auto-uploaded to the WeChat image CDN and their `src`
  rewritten to the returned URL.
- Mass send has rate limits. In production, prefer creating a draft and confirming it in the
  MP backend before using `--publish`.
- Create a draft by default. Add `--publish` only when the user explicitly requests a mass send.
- For endpoints, request shapes, and error codes, load `references/wechat_api.md`.

## Resources

- `scripts/wechat_publisher.py` — the publisher (Markdown→HTML, uploads, draft, publish).
- `scripts/config.example.json` — config template.
- `references/wechat_api.md` — WeChat MP API endpoint reference.
