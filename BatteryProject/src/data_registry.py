"""实验数据 registry：为 data_raw/ 与 data_processed/ 建立机器可查询的索引。

设计目标（北极星：AI Agent 驱动的仿真工作流）：
- Agent 一条命令能回答「有哪些电芯在哪些温度/倍率下的什么数据」；
- scan 自动登记文件并尽力推断工况（温度/倍率/测试类型/SOH/样本号）；
- 人工修订的字段（signals/source/quality/notes 及 status=curated）在重扫时保留。

registry 文件为仓库根目录 datasets.json（UTF-8、按 path 排序，diff 友好）。

用法（在仓库根目录）：
    python BatteryProject/src/data_registry.py scan
    python BatteryProject/src/data_registry.py ls --cell MIC --temp 25
    python BatteryProject/src/data_registry.py summary
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

HITHIUM_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FILENAME = "datasets.json"

# kind -> 数据目录名
DATA_DIRS = {"raw": "data_raw", "processed": "data_processed"}

# 只登记可作为数据集加载的表格类文件
DATA_EXTENSIONS = {".csv", ".xlsx", ".xls", ".xlsm", ".dat", ".txt", ".parquet"}

# 重扫时永远保留的人工字段
MANUAL_FIELDS = ("signals", "source", "quality", "notes")

# 测试类型关键词（顺序即优先级；对 relpath 全文小写匹配）
TEST_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("/rate/", "倍率"),
    ("benchmark", "倍率"),
    ("核容", "容量"),
    ("工况", "工况"),
    ("倍率充电", "倍率充电"),
    ("倍率放电", "倍率放电"),
    ("cycle life", "循环"),
    ("cycling", "循环"),
    ("循环", "循环"),
    ("cycle", "循环"),
    ("age", "循环"),
    ("dcr", "DCR"),
    ("mapping", "脉冲"),
    ("脉冲", "脉冲"),
    ("pulse", "脉冲"),
    ("ocv", "OCV"),
    ("eis", "EIS"),
    ("能效", "能效"),
    ("日历", "存储"),
    ("存储", "存储"),
    ("容量", "容量"),
    ("倍率", "倍率"),
]

_TEMP_STRONG = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:℃|°\s*[Cc]|度)")
_TEMP_WEAK = re.compile(r"(?<![\d.pP])(-?\d{1,3})\s*C(?![A-Za-z0-9])")
_RATE_P_COMPACT = re.compile(r"(\d+)p(\d+)\s*P(?![A-Za-z0-9])", re.IGNORECASE)
_RATE_P = re.compile(r"(\d+(?:\.\d+)?)\s*([CD]?P)(?![A-Za-z0-9])")
_RATE_C = re.compile(r"(\d+\.\d+)\s*C(?![A-Za-z0-9])")
_SOH = re.compile(r"SOH\s*(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)
_SAMPLE = re.compile(r"No\.?\s*(\d+)\s*#", re.IGNORECASE)


def infer_temperature(parts: list[str]) -> float | None:
    """从路径片段推断温度（℃）。从文件名向上层目录找，先强模式后弱模式。"""
    for text in parts:
        m = _TEMP_STRONG.search(text)
        if m:
            return float(m.group(1))
    for text in parts:
        m = _TEMP_WEAK.search(text)
        if m:
            value = float(m.group(1))
            if -40 <= value <= 80:
                return value
    return None


def infer_rate(parts: list[str]) -> str | None:
    """从路径片段推断倍率，如 0.5P / 0.25P / 0.5CP / 0.25C。"""
    for text in parts:
        m = _RATE_P_COMPACT.search(text)
        if m:
            return f"{float(m.group(1) + '.' + m.group(2)):g}P"
        m = _RATE_P.search(text)
        if m:
            return f"{float(m.group(1)):g}{m.group(2).upper()}"
        m = _RATE_C.search(text)
        if m:
            return f"{float(m.group(1)):g}C"
    return None


def infer_test_type(relpath: str) -> str | None:
    text = relpath.lower()
    for keyword, canonical in TEST_TYPE_KEYWORDS:
        if keyword in text:
            return canonical
    return None


def infer_soh(relpath: str) -> float | None:
    m = _SOH.search(relpath)
    return float(m.group(1)) if m else None


def infer_sample_id(relpath: str) -> str | None:
    m = _SAMPLE.search(relpath)
    return f"No{m.group(1)}#" if m else None


def entry_id(rel_posix: str) -> str:
    return hashlib.sha1(rel_posix.encode("utf-8")).hexdigest()[:10]


def build_entry(root: Path, file_path: Path, kind: str) -> dict[str, Any]:
    rel = file_path.relative_to(root)
    rel_posix = rel.as_posix()
    # data_raw/<cell>/<group.../file>
    cell = rel.parts[1] if len(rel.parts) > 2 else (rel.parts[1] if len(rel.parts) == 2 else None)
    group_parts = rel.parts[2:-1]
    # 推断顺序：文件名优先，其次由深到浅的目录名
    name_parts = [rel.parts[-1]] + list(reversed(group_parts))
    stat = file_path.stat()
    return {
        "id": entry_id(rel_posix),
        "path": rel_posix,
        "cell": cell,
        "kind": kind,
        "format": file_path.suffix.lstrip(".").lower(),
        "size_bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
        "group": "/".join(group_parts),
        "temperature_C": infer_temperature(name_parts),
        "rate": infer_rate(name_parts),
        "test_type": infer_test_type(rel_posix),
        "soh_pct": infer_soh(rel_posix),
        "sample_id": infer_sample_id(rel_posix),
        "signals": [],
        "source": None,
        "quality": None,
        "notes": None,
        "status": "auto",
    }


def iter_data_files(root: Path) -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for kind, dirname in DATA_DIRS.items():
        base = root / dirname
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() not in DATA_EXTENSIONS:
                continue
            if p.name.startswith("~$"):
                continue
            found.append((p, kind))
    return found


def load_registry(registry_path: Path) -> dict[str, Any]:
    """加载 registry；文件不存在或 JSON 损坏时返回空 registry。

    JSON 损坏时把原文件备份为 <name>.corrupt.<timestamp> 再返回空
    registry，避免单个坏文件使所有 ls/summary/scan 命令连锁崩溃。
    """
    if not registry_path.is_file():
        return {"version": 1, "updated": None, "entries": []}
    try:
        with open(registry_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        corrupt_backup = registry_path.with_suffix(
            registry_path.suffix + ".corrupt." + datetime.now().strftime("%Y%m%d%H%M%S")
        )
        try:
            registry_path.replace(corrupt_backup)
        except OSError:
            pass
        print(
            "WARNING: %s 损坏（%s），已备份至 %s 并重建空 registry。"
            % (registry_path, exc, corrupt_backup),
            file=sys.stderr,
        )
        return {"version": 1, "updated": None, "entries": []}


def save_registry(registry: dict[str, Any], registry_path: Path) -> None:
    """原子写入 registry：先写 .tmp 再 os.replace，避免中断产生截断 JSON。"""
    registry["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    registry["entries"] = sorted(registry["entries"], key=lambda e: e["path"])
    tmp_path = registry_path.with_suffix(registry_path.suffix + ".tmp")
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(registry, f, ensure_ascii=False, indent=1)
        f.write("\n")
    tmp_path.replace(registry_path)


def scan(root: Path = HITHIUM_ROOT, registry_path: Path | None = None) -> dict[str, Any]:
    """扫描数据目录，合并进现有 registry。

    合并规则：
    - 新文件 → 新登记（status=auto，工况尽力推断）；
    - 已有条目 → 人工字段（MANUAL_FIELDS）永远保留；status=curated/ignore 的条目
      不重推工况，只刷新 size/mtime；status=auto 的条目按当前规则重推；
    - 文件消失 → 条目保留并标记 status=missing（人工信息不丢）。
    """
    registry_path = registry_path or (root / REGISTRY_FILENAME)
    registry = load_registry(registry_path)
    old_by_path = {e["path"]: e for e in registry["entries"]}
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []
    n_new = n_updated = 0

    for file_path, kind in iter_data_files(root):
        fresh = build_entry(root, file_path, kind)
        seen.add(fresh["path"])
        old = old_by_path.get(fresh["path"])
        if old is None:
            entries.append(fresh)
            n_new += 1
            continue
        status = old.get("status", "auto")
        if status in ("curated", "ignore"):
            merged = dict(old)
            merged["size_bytes"] = fresh["size_bytes"]
            merged["mtime"] = fresh["mtime"]
        else:
            merged = fresh
            for field in MANUAL_FIELDS:
                if old.get(field):
                    merged[field] = old[field]
            merged["status"] = "auto"
        entries.append(merged)
        n_updated += 1

    n_missing = 0
    for path, old in old_by_path.items():
        if path not in seen:
            gone = dict(old)
            gone["status"] = "missing"
            entries.append(gone)
            n_missing += 1

    registry["entries"] = entries
    save_registry(registry, registry_path)
    print(f"scan 完成: {len(entries)} 条 (新 {n_new} / 已有 {n_updated} / 丢失 {n_missing}) -> {registry_path}")
    return registry


def filter_entries(
    entries: list[dict[str, Any]],
    cell: str | None = None,
    temp: float | None = None,
    rate: str | None = None,
    test: str | None = None,
    kind: str | None = None,
    fmt: str | None = None,
    status: str | None = None,
    path_contains: str | None = None,
) -> list[dict[str, Any]]:
    out = []
    for e in entries:
        if cell and cell.lower() not in (e.get("cell") or "").lower():
            continue
        if temp is not None and e.get("temperature_C") != temp:
            continue
        if rate and (e.get("rate") or "").lower() != rate.lower():
            continue
        if test and test.lower() not in (e.get("test_type") or "").lower():
            continue
        if kind and e.get("kind") != kind:
            continue
        if fmt and e.get("format") != fmt.lower().lstrip("."):
            continue
        if status and e.get("status") != status:
            continue
        if path_contains and path_contains.lower() not in e["path"].lower():
            continue
        out.append(e)
    return out


def query_datasets(
    *,
    cell: str | None = None,
    temp: float | None = None,
    rate: str | None = None,
    test: str | None = None,
    kind: str | None = None,
    fmt: str | None = None,
    status: str | None = None,
    path_contains: str | None = None,
    root: Path = HITHIUM_ROOT,
    registry_path: Path | None = None,
    require_unique: bool = False,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    """Query registry entries and attach an absolute path for notebook workflows.

    Missing and ignored entries are excluded by default. Set require_unique
    when a workflow expects exactly one experimental dataset.
    """
    registry_path = registry_path or (root / REGISTRY_FILENAME)
    hits = filter_entries(
        load_registry(registry_path)["entries"],
        cell=cell,
        temp=temp,
        rate=rate,
        test=test,
        kind=kind,
        fmt=fmt,
        status=status,
        path_contains=path_contains,
    )
    if not include_inactive and status is None:
        hits = [entry for entry in hits if entry.get("status") not in {"ignore", "missing"}]
    resolved = []
    for entry in hits:
        item = dict(entry)
        item["absolute_path"] = str((root / entry["path"]).resolve())
        resolved.append(item)
    if require_unique and len(resolved) != 1:
        query = {
            "cell": cell,
            "temp": temp,
            "rate": rate,
            "test": test,
            "kind": kind,
            "fmt": fmt,
            "path_contains": path_contains,
        }
        raise ValueError(f"dataset query expected exactly one match, got {len(resolved)}: {query}")
    return resolved


def curate_entry(
    registry_path: Path,
    *,
    entry_id_value: str | None = None,
    entry_path: str | None = None,
    **updates: Any,
) -> dict[str, Any]:
    """Update one registry entry without hand-editing datasets.json."""
    if bool(entry_id_value) == bool(entry_path):
        raise ValueError("provide exactly one of entry_id_value or entry_path")
    allowed = {
        "cell", "temperature_C", "rate", "test_type", "soh_pct", "sample_id",
        "signals", "source", "quality", "notes", "status",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"unsupported curate fields: {sorted(unknown)}")
    registry = load_registry(registry_path)
    matches = [
        entry for entry in registry["entries"]
        if (entry_id_value and entry.get("id") == entry_id_value)
        or (entry_path and entry.get("path") == entry_path)
    ]
    if len(matches) != 1:
        raise ValueError(f"curate selector expected exactly one match, got {len(matches)}")
    entry = matches[0]
    for key, value in updates.items():
        if value is not None:
            entry[key] = value
    save_registry(registry, registry_path)
    return dict(entry)


def _fmt_row(e: dict[str, Any]) -> str:
    temp = f"{e['temperature_C']:g}℃" if e.get("temperature_C") is not None else "-"
    return (
        f"{e['id']}  {e.get('cell') or '-':<14} {temp:>7}  {e.get('rate') or '-':<7} "
        f"{e.get('test_type') or '-':<6} {e.get('status'):<8} {e['path']}"
    )


def cmd_ls(args: argparse.Namespace, registry: dict[str, Any]) -> None:
    hits = filter_entries(
        registry["entries"],
        cell=args.cell,
        temp=args.temp,
        rate=args.rate,
        test=args.test,
        kind=args.kind,
        fmt=args.format,
        status=args.status,
        path_contains=args.path,
    )
    for e in hits:
        print(_fmt_row(e))
    print(f"-- {len(hits)}/{len(registry['entries'])} 条")


def cmd_summary(registry: dict[str, Any]) -> None:
    entries = [e for e in registry["entries"] if e.get("status") != "missing"]
    by_cell: dict[str, dict[str, int]] = {}
    for e in entries:
        cell = e.get("cell") or "?"
        key = e.get("test_type") or "未识别"
        by_cell.setdefault(cell, {})
        by_cell[cell][key] = by_cell[cell].get(key, 0) + 1
    for cell in sorted(by_cell):
        parts = ", ".join(f"{k} x{v}" for k, v in sorted(by_cell[cell].items(), key=lambda kv: -kv[1]))
        print(f"{cell:<16} {sum(by_cell[cell].values()):>4} 条  ({parts})")
    n_temp = sum(1 for e in entries if e.get("temperature_C") is not None)
    print(f"-- 共 {len(entries)} 条有效；温度识别率 {n_temp}/{len(entries)}")


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="实验数据 registry")
    parser.add_argument("--root", type=Path, default=HITHIUM_ROOT, help="仓库根目录（默认自动定位）")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan", help="扫描 data_raw/ 与 data_processed/ 并更新 datasets.json")
    p_ls = sub.add_parser("ls", help="按条件列出数据集")
    p_ls.add_argument("--cell")
    p_ls.add_argument("--temp", type=float)
    p_ls.add_argument("--rate")
    p_ls.add_argument("--test")
    p_ls.add_argument("--kind", choices=list(DATA_DIRS))
    p_ls.add_argument("--format")
    p_ls.add_argument("--status")
    p_ls.add_argument("--path", help="路径包含（子串匹配）")
    p_curate = sub.add_parser("curate", help="按 id/path 校准一个数据条目，无需手改 JSON")
    selector = p_curate.add_mutually_exclusive_group(required=True)
    selector.add_argument("--id", dest="entry_id")
    selector.add_argument("--path", dest="entry_path")
    p_curate.add_argument("--cell")
    p_curate.add_argument("--temp", type=float)
    p_curate.add_argument("--rate")
    p_curate.add_argument("--test")
    p_curate.add_argument("--soh", type=float)
    p_curate.add_argument("--sample")
    p_curate.add_argument("--signals", help="逗号分隔，如 voltage,current,capacity")
    p_curate.add_argument("--source")
    p_curate.add_argument("--quality")
    p_curate.add_argument("--notes")
    p_curate.add_argument("--status", choices=["auto", "curated", "ignore"], default="curated")
    sub.add_parser("summary", help="按电芯汇总数据覆盖情况")
    args = parser.parse_args(argv)

    registry_path = args.root / REGISTRY_FILENAME
    if args.command == "scan":
        scan(args.root, registry_path)
    elif args.command == "ls":
        cmd_ls(args, load_registry(registry_path))
    elif args.command == "curate":
        signals = None
        if args.signals is not None:
            signals = [item.strip() for item in args.signals.split(",") if item.strip()]
        entry = curate_entry(
            registry_path,
            entry_id_value=args.entry_id,
            entry_path=args.entry_path,
            cell=args.cell,
            temperature_C=args.temp,
            rate=args.rate,
            test_type=args.test,
            soh_pct=args.soh,
            sample_id=args.sample,
            signals=signals,
            source=args.source,
            quality=args.quality,
            notes=args.notes,
            status=args.status,
        )
        print(_fmt_row(entry))
    elif args.command == "summary":
        cmd_summary(load_registry(registry_path))


if __name__ == "__main__":
    main()
