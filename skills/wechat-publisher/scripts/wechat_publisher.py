#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 自动发公众号 —— 本地发布工具

把一篇 Markdown 文章：
  1. 转换成微信兼容的内联样式 HTML（自动排版，无需手工调格式）
  2. 上传正文配图（media/uploadimg）与封面图（material/add_material）
  3. 创建草稿（draft/add）
  4. 可选：提交发布（freepublish/submit）

特性：
  - 零强依赖，仅用 requests（不可用则回退 urllib，仅文件上传需要 requests）
  - access_token 本地缓存（7200s），避免重复获取
  - --dry-run：跳过所有网络请求，仅生成 HTML 并写出 preview.html，方便先看排版
  - 支持文章顶部 YAML 风格 frontmatter（title/author/digest/cover）

用法：
  python wechat_publisher.py article.md
  python wechat_publisher.py article.md --publish          # 创建草稿并直接群发
  python wechat_publisher.py article.md --dry-run          # 仅预览，不联网
  python wechat_publisher.py article.md --config my.json
"""

import sys
import os
import re
import json
import time
import argparse
import mimetypes
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except Exception:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

API = "https://api.weixin.qq.com/cgi-bin"
ROOT = Path(__file__).resolve().parent
TOKEN_CACHE = ROOT / "token.json"
DEFAULT_CONFIG = Path(r"C:\Users\hez\WorkBuddy\Claw\wechat-publisher\config.json")

# 微信品牌绿，作为强调色贯穿全文
ACCENT = "#07c160"


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #
def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    # 允许用环境变量覆盖敏感字段
    cfg["appid"] = os.environ.get("WX_APPID", cfg.get("appid", ""))
    cfg["appsecret"] = os.environ.get("WX_APPSECRET", cfg.get("appsecret", ""))
    return cfg


# --------------------------------------------------------------------------- #
# frontmatter
# --------------------------------------------------------------------------- #
def parse_frontmatter(text):
    """解析顶部 --- 包裹的 YAML 风格元数据，返回 (meta:dict, body:str)。"""
    meta = {}
    body = text
    if text.lstrip().startswith("---"):
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        if m:
            raw, body = m.group(1), m.group(2)
            for line in raw.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


# --------------------------------------------------------------------------- #
# Markdown -> 微信内联样式 HTML
# --------------------------------------------------------------------------- #
def escape_html(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text):
    text = escape_html(text)
    # 图片 ![alt](url)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" '
        'style="max-width:100%;display:block;margin:14px auto;border-radius:6px;">',
        text,
    )
    # 链接 [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}" style="color:{ACCENT};'
        'text-decoration:none;word-break:break-all;">{m.group(1)}</a>',
        text,
    )
    # 粗体 **x**
    text = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="font-weight:700;">\1</strong>', text)
    # 斜体 *x*
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    # 行内代码 `x`
    text = re.sub(
        r"`([^`]+)`",
        lambda m: (
            '<code style="background:#f2f2f2;padding:2px 6px;border-radius:4px;'
            'font-family:Consolas,Menlo,monospace;font-size:14px;color:#c7254e;">'
            f"{m.group(1)}</code>"
        ),
        text,
    )
    return text


def md_to_wechat(md_text):
    lines = md_text.replace("\r\n", "\n").split("\n")
    out = []
    i, n = 0, len(lines)
    hsize = {1: 22, 2: 20, 3: 18, 4: 16, 5: 15, 6: 14}

    def is_block_start(s):
        s = s.strip()
        return (
            s.startswith("#")
            or s.startswith(">")
            or s.startswith("```")
            or re.match(r"^-{3,}$", s)
            or re.match(r"^\s*[-*]\s+", s)
            or re.match(r"^\s*\d+\.\s+", s)
        )

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # 代码块
        if stripped.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            code_lines = []
            for code_line in buf:
                # WeChat's draft editor normalises literal newlines inside <code>
                # to spaces. Use one block element per source line and encode
                # spaces explicitly so Python indentation survives draft/add.
                escaped_line = escape_html(code_line.expandtabs(4)).replace(
                    " ", "&nbsp;"
                )
                code_lines.append(
                    '<p style="margin:0;min-height:1.6em;font-family:Consolas,Menlo,'
                    'monospace;font-size:14px;line-height:1.6;color:#24292e;'
                    f'word-break:break-all;">{escaped_line or "&nbsp;"}</p>'
                )
            code = "".join(code_lines)
            out.append(
                '<section style="background:#f6f8fa;border:1px solid #e1e4e8;'
                'border-radius:8px;padding:14px 16px;overflow:auto;margin:18px 0;">'
                f"{code}</section>"
            )
            continue

        if stripped == "":
            i += 1
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            txt = inline(m.group(2))
            out.append(
                f'<section style="margin:26px 0 12px;font-weight:700;'
                f'font-size:{hsize.get(lvl,16)}px;line-height:1.4;color:#1f2329;'
                f'border-left:4px solid {ACCENT};padding-left:10px;">{txt}</section>'
            )
            i += 1
            continue

        # 分隔线
        if re.match(r"^-{3,}$", stripped):
            out.append('<hr style="border:none;border-top:1px solid #e5e5e5;margin:22px 0;">')
            i += 1
            continue

        # 引用
        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].strip())
                i += 1
            txt = "<br>".join(inline(b) for b in buf)
            out.append(
                '<section style="background:#f7f8fa;border-left:4px solid #d0d7de;'
                f'padding:12px 16px;margin:18px 0;color:#57606a;font-size:15px;'
                f'line-height:1.8;">{txt}</section>'
            )
            continue

        # 无序列表
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(inline(re.match(r"^\s*[-*]\s+(.*)$", lines[i]).group(1)))
                i += 1
            lis = "".join(f'<li style="margin:8px 0;">{it}</li>' for it in items)
            out.append(
                f'<ul style="padding-left:22px;margin:18px 0;font-size:15px;'
                f'line-height:1.8;color:#333;">{lis}</ul>'
            )
            continue

        # 有序列表
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(inline(re.match(r"^\s*\d+\.\s+(.*)$", lines[i]).group(1)))
                i += 1
            lis = "".join(f'<li style="margin:8px 0;">{it}</li>' for it in items)
            out.append(
                f'<ol style="padding-left:22px;margin:18px 0;font-size:15px;'
                f'line-height:1.8;color:#333;">{lis}</ol>'
            )
            continue

        # 段落
        buf = []
        while i < n and lines[i].strip() != "" and not is_block_start(lines[i]):
            buf.append(lines[i])
            i += 1
        para = " ".join(inline(b) for b in buf)
        out.append(
            f'<p style="margin:16px 0;font-size:15px;line-height:1.8;color:#333;'
            f'letter-spacing:.3px;">{para}</p>'
        )

    html = "\n".join(out)
    html = (
        '<section style="font-family:-apple-system,BlinkMacSystemFont,'
        '\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#333;'
        'max-width:677px;margin:0 auto;padding:0 4px;">'
        f"{html}</section>"
    )
    return html


# --------------------------------------------------------------------------- #
# 微信 API
# --------------------------------------------------------------------------- #
def http_get_json(url):
    if HAS_REQUESTS:
        return requests.get(url, timeout=20).json()
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def http_post_json(url, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if HAS_REQUESTS:
        return requests.post(
            url,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=20,
        ).json()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def http_post_file(url, file_path, fields=None):
    if not HAS_REQUESTS:
        raise RuntimeError("文件上传需要 requests 库（pip install requests）")
    with open(file_path, "rb") as f:
        resp = requests.post(
            url,
            files={
                "media": (
                    Path(file_path).name,
                    f,
                    mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                )
            },
            data=fields or {},
            timeout=30,
        )
    return resp.json()


def get_token(appid, secret, force=False):
    if not force and TOKEN_CACHE.exists():
        d = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
        if time.time() < d.get("expires_at", 0) - 120:
            return d["access_token"]
    r = http_get_json(
        f"{API}/token?grant_type=client_credential&appid={appid}&secret={secret}"
    )
    if "access_token" not in r:
        raise RuntimeError(f"获取 access_token 失败：{r}")
    d = {"access_token": r["access_token"], "expires_at": time.time() + r.get("expires_in", 7200)}
    TOKEN_CACHE.write_text(json.dumps(d), encoding="utf-8")
    return r["access_token"]


def upload_cover(token, cover_path):
    """上传封面图，返回 media_id。cover_path 为本地图片路径。"""
    r = http_post_file(
        f"{API}/material/add_material?access_token={token}&type=image", cover_path
    )
    if "media_id" not in r:
        raise RuntimeError(f"上传封面失败：{r}")
    return r["media_id"]


def upload_content_image(token, img_path):
    """上传正文配图，返回微信图床 URL。"""
    r = http_post_file(f"{API}/media/uploadimg?access_token={token}", img_path)
    if "url" not in r:
        raise RuntimeError(f"上传配图失败：{r}")
    return r["url"]


def replace_local_images(html, token, base_dir):
    """把 HTML 中的本地图片路径替换为微信图床 URL。"""

    def repl(m):
        src = m.group(1)
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        local = (base_dir / src).resolve()
        if local.exists():
            try:
                url = upload_content_image(token, str(local))
                return m.group(0).replace(src, url)
            except Exception as e:
                print(f"  [warn] 配图上传失败，保留原路径：{local} ({e})")
                return m.group(0)
        return m.group(0)

    return re.sub(r'src="([^"]+)"', repl, html)


def add_draft(token, article):
    r = http_post_json(f"{API}/draft/add?access_token={token}", {"articles": [article]})
    if "media_id" not in r:
        raise RuntimeError(f"创建草稿失败：{r}")
    return r["media_id"]


def submit_publish(token, media_id):
    r = http_post_json(f"{API}/freepublish/submit?access_token={token}", {"media_id": media_id})
    if r.get("errcode", 0) != 0:
        raise RuntimeError(f"提交发布失败：{r}")
    return r.get("publish_id")


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="WorkBuddy 自动发公众号")
    ap.add_argument("article", help="Markdown 文章路径")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="配置文件路径")
    ap.add_argument("--publish", action="store_true", help="创建草稿后直接提交群发")
    ap.add_argument("--dry-run", action="store_true", help="仅生成 HTML 预览，不联网")
    ap.add_argument("--no-cache", action="store_true", help="强制刷新 access_token")
    args = ap.parse_args()

    article_path = Path(args.article).resolve()
    if not article_path.exists():
        print(f"[error] 找不到文章：{article_path}")
        sys.exit(1)

    cfg = load_config(args.config)
    appid, secret = cfg.get("appid", ""), cfg.get("appsecret", "")
    author = cfg.get("author", "")
    default_cover = cfg.get("cover", "")
    default_cover_media_id = cfg.get("cover_media_id", "")

    raw = article_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    html = md_to_wechat(body)

    title = meta.get("title") or cfg.get("title") or article_path.stem
    author = meta.get("author") or author
    digest = meta.get("digest") or ""
    cover = meta.get("cover") or default_cover

    base_dir = article_path.parent

    # 预览
    preview = ROOT / "preview.html"
    preview.write_text(
        f"<!doctype html><meta charset=utf-8><title>{title}</title>"
        f"<div style='max-width:677px;margin:20px auto;'>{html}</div>",
        encoding="utf-8",
    )
    print(f"[ok] 已生成排版预览：{preview}")

    if args.dry_run:
        print("[dry-run] 未联网。以下是关键参数：")
        print(f"  title   : {title}")
        print(f"  author  : {author}")
        print(f"  digest  : {digest}")
        print(f"  cover   : {cover or '(未设置)'}")
        print(f"  content : {len(html)} 字符（内联样式 HTML）")
        local_imgs = re.findall(r'src="(?!http|data)([^"]+)"', html)
        if local_imgs:
            print(f"  待上传配图：{local_imgs}")
        print("[dry-run] 完成。正式创建草稿请去掉 --dry-run。")
        return

    if not appid or not secret:
        print("[error] config.json 缺少 appid/appsecret，无法联网发布。")
        sys.exit(1)

    token = get_token(appid, secret, force=args.no_cache)
    print("[ok] access_token 已获取")

    # 正文配图
    html = replace_local_images(html, token, base_dir)

    # 封面
    if default_cover_media_id:
        thumb_media_id = default_cover_media_id
    elif cover:
        cover_path = (base_dir / cover).resolve()
        if not cover_path.exists():
            print(f"[error] 封面图不存在：{cover_path}")
            sys.exit(1)
        thumb_media_id = upload_cover(token, str(cover_path))
        print("[ok] 封面已上传")
    else:
        print("[error] 缺少封面图（请在 config 或 frontmatter 设置 cover / cover_media_id）")
        sys.exit(1)

    article_payload = {
        "title": title,
        "author": author,
        "digest": digest,
        "content": html,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }

    media_id = add_draft(token, article_payload)
    print(f"[ok] 草稿已创建，media_id={media_id}")

    if args.publish:
        publish_id = submit_publish(token, media_id)
        print(f"[ok] 已提交群发，publish_id={publish_id}")
    else:
        print("[done] 草稿已就绪，可在公众号后台预览/群发；加 --publish 可自动群发。")


if __name__ == "__main__":
    main()
