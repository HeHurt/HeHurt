from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


SOURCE = Path(r"D:\Users\hez\Desktop\hithium")
TARGET = Path(r"C:\HithiumSSD\hithium")
REPORT_ROOT = Path(r"C:\HithiumSSD\sync_reports")
CODE_EXE = Path(r"D:\软件安装\Microsoft VS Code\Code.exe")
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
}
TSD_HEADER = b"%TSD-Header-###%"
MTIME_TOLERANCE_NS = 2_000_000_000


def is_reparse(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & 0x400)
    except (AttributeError, OSError):
        return path.is_symlink()


def relative_key(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def unique_backup_path(base: Path, relative: Path) -> Path:
    output = base / relative
    suffix = 1
    while output.exists():
        output = output.with_name(f"{output.name}.dup{suffix}")
        suffix += 1
    return output


def move_to_backup(path: Path, base: Path, relative: Path) -> Path:
    output = unique_backup_path(base, relative)
    output.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, output)
    return output


def needs_code_bridge(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            return stream.read(len(TSD_HEADER)) == TSD_HEADER
    except (PermissionError, OSError):
        return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def run_code_bridge(manifest_path: Path) -> tuple[set[str], list[dict]]:
    manifest_literal = json.dumps(str(manifest_path))
    script = (
        "const fs=require('fs'),p=require('path'),crypto=require('crypto');"
        f"const ops=JSON.parse(fs.readFileSync({manifest_literal},'utf8'));"
        "let ok=[],failed=[];"
        "for(const op of ops){try{fs.mkdirSync(p.dirname(op.dst),{recursive:true});"
        "const a=fs.readFileSync(op.src);fs.writeFileSync(op.dst,a);"
        "fs.utimesSync(op.dst,op.atime,op.mtime);const b=fs.readFileSync(op.dst);"
        "if(a.length!==b.length||!crypto.timingSafeEqual(a,b))"
        "throw new Error('verify mismatch');ok.push(op.rel);"
        "}catch(e){failed.push({rel:op.rel,error:String(e)});}}"
        "console.log(JSON.stringify({ok,failed}));"
    )
    environment = os.environ.copy()
    environment["ELECTRON_RUN_AS_NODE"] = "1"
    process = subprocess.run(
        [str(CODE_EXE), "-e", script],
        capture_output=True,
        text=True,
        env=environment,
        timeout=1800,
    )
    result = None
    for line in reversed(process.stdout.splitlines()):
        try:
            result = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if process.returncode != 0 or result is None:
        return set(), [{
            "rel": "<bridge-process>",
            "error": f"rc={process.returncode}; stdout={process.stdout[-1000:]}; stderr={process.stderr[-1000:]}",
        }]
    return set(result.get("ok", [])), result.get("failed", [])


def main() -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    report = REPORT_ROOT / stamp
    overwritten_root = report / "overwritten_target"
    target_only_root = report / "target_only"
    manifest_path = report / "code_bridge_manifest.json"
    summary_path = report / "summary.json"
    report.mkdir(parents=True, exist_ok=False)

    stats = {
        "stamp": stamp,
        "source": str(SOURCE),
        "target": str(TARGET),
        "scanned_source_files": 0,
        "unchanged": 0,
        "source_only_copied": 0,
        "different_overwritten": 0,
        "target_only_archived": 0,
        "target_dirs_created": 0,
        "reparse_dirs_skipped": 0,
        "reparse_files_skipped": 0,
        "office_temp_skipped": 0,
        "code_bridge_queued": 0,
        "code_bridge_copied": 0,
        "verified": 0,
        "verification_failed": 0,
        "copy_failed": 0,
        "git_robocopy_rc": None,
    }
    failures: list[dict] = []
    source_files: set[str] = set()
    copied_records: list[dict] = []
    bridge_operations: list[dict] = []

    if not SOURCE.is_dir() or not TARGET.is_dir():
        raise RuntimeError(f"Source/target missing: source={SOURCE.exists()} target={TARGET.exists()}")
    if is_reparse(SOURCE):
        raise RuntimeError("Source is already a reparse point")

    print(f"[start] report={report}", flush=True)

    def copy_source(
        source: Path,
        target: Path,
        relative: Path,
        backup: Path | None,
        category: str,
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            source_stat = source.stat()
            if needs_code_bridge(source):
                bridge_operations.append({
                    "src": str(source),
                    "dst": str(target),
                    "atime": source_stat.st_atime,
                    "mtime": source_stat.st_mtime,
                    "rel": str(relative).replace("\\", "/"),
                    "backup": str(backup) if backup else None,
                    "category": category,
                })
                stats["code_bridge_queued"] += 1
                return
            shutil.copy2(source, target)
            copied_records.append({
                "src": source,
                "dst": target,
                "rel": str(relative).replace("\\", "/"),
                "backup": backup,
                "category": category,
                "bridge": False,
            })
            stats[category] += 1
        except Exception as error:
            stats["copy_failed"] += 1
            failures.append({"phase": "copy", "path": str(relative), "error": repr(error)})
            if backup and backup.exists() and not target.exists():
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(backup, target)
                except Exception as restore_error:
                    failures.append({
                        "phase": "restore_after_copy_failure",
                        "path": str(relative),
                        "error": repr(restore_error),
                    })

    for directory, dirs, files in os.walk(SOURCE, topdown=True, followlinks=False):
        source_dir = Path(directory)
        kept_dirs = []
        for name in dirs:
            path = source_dir / name
            if name in SKIP_DIRS:
                continue
            if is_reparse(path):
                stats["reparse_dirs_skipped"] += 1
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs

        relative_dir = source_dir.relative_to(SOURCE)
        target_dir = TARGET / relative_dir
        if target_dir.exists() and not target_dir.is_dir():
            try:
                moved = move_to_backup(target_dir, overwritten_root, relative_dir)
                failures.append({
                    "phase": "type_conflict_archived",
                    "path": str(relative_dir),
                    "backup": str(moved),
                })
            except Exception as error:
                failures.append({
                    "phase": "type_conflict",
                    "path": str(relative_dir),
                    "error": repr(error),
                })
                dirs[:] = []
                continue
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            stats["target_dirs_created"] += 1

        for name in files:
            if name.startswith("~$"):
                stats["office_temp_skipped"] += 1
                continue
            source = source_dir / name
            relative = source.relative_to(SOURCE)
            key = str(relative).replace("\\", "/")
            source_files.add(key)
            stats["scanned_source_files"] += 1
            if stats["scanned_source_files"] % 500 == 0:
                copied = stats["source_only_copied"] + stats["different_overwritten"]
                print(
                    f"[scan] {stats['scanned_source_files']} files; copied={copied}; "
                    f"bridge={stats['code_bridge_queued']}; failed={stats['copy_failed']}",
                    flush=True,
                )
            target = TARGET / relative
            try:
                source_stat = source.stat()
                if not target.exists():
                    copy_source(source, target, relative, None, "source_only_copied")
                    continue
                if not target.is_file():
                    backup = move_to_backup(target, overwritten_root, relative)
                    copy_source(source, target, relative, backup, "different_overwritten")
                    continue
                target_stat = target.stat()
                same_metadata = (
                    source_stat.st_size == target_stat.st_size
                    and abs(source_stat.st_mtime_ns - target_stat.st_mtime_ns) <= MTIME_TOLERANCE_NS
                )
                if same_metadata:
                    stats["unchanged"] += 1
                    continue
                backup = move_to_backup(target, overwritten_root, relative)
                copy_source(source, target, relative, backup, "different_overwritten")
            except Exception as error:
                stats["copy_failed"] += 1
                failures.append({"phase": "compare_or_prepare", "path": key, "error": repr(error)})

    print(
        f"[pass1] scanned={stats['scanned_source_files']} unchanged={stats['unchanged']} "
        f"copied={stats['source_only_copied'] + stats['different_overwritten']} "
        f"bridge={len(bridge_operations)}",
        flush=True,
    )

    if bridge_operations:
        manifest_path.write_text(json.dumps(bridge_operations, ensure_ascii=False), encoding="utf-8")
        bridge_ok, bridge_failures = run_code_bridge(manifest_path)
        stats["code_bridge_copied"] = len(bridge_ok)
        failure_by_path = {item.get("rel"): item.get("error") for item in bridge_failures}
        for operation in bridge_operations:
            relative = operation["rel"]
            if relative in bridge_ok:
                stats[operation["category"]] += 1
                copied_records.append({
                    "src": Path(operation["src"]),
                    "dst": Path(operation["dst"]),
                    "rel": relative,
                    "backup": Path(operation["backup"]) if operation.get("backup") else None,
                    "category": operation["category"],
                    "bridge": True,
                })
                continue
            stats["copy_failed"] += 1
            failures.append({
                "phase": "code_bridge",
                "path": relative,
                "error": failure_by_path.get(relative, "unknown bridge failure"),
            })
            backup = Path(operation["backup"]) if operation.get("backup") else None
            target = Path(operation["dst"])
            if backup and backup.exists() and not target.exists():
                os.replace(backup, target)
        print(
            f"[bridge] queued={len(bridge_operations)} copied={stats['code_bridge_copied']}",
            flush=True,
        )

    target_seen = 0
    for directory, dirs, files in os.walk(TARGET, topdown=True, followlinks=False):
        target_dir = Path(directory)
        kept_dirs = []
        for name in dirs:
            path = target_dir / name
            if name in SKIP_DIRS:
                continue
            if is_reparse(path):
                stats["reparse_dirs_skipped"] += 1
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs
        for name in files:
            if name.startswith("~$"):
                continue
            path = target_dir / name
            relative = path.relative_to(TARGET)
            key = str(relative).replace("\\", "/")
            target_seen += 1
            if target_seen % 1000 == 0:
                print(
                    f"[target-scan] {target_seen} files; archived={stats['target_only_archived']}",
                    flush=True,
                )
            if key in source_files:
                continue
            try:
                move_to_backup(path, target_only_root, relative)
                stats["target_only_archived"] += 1
            except Exception as error:
                failures.append({
                    "phase": "archive_target_only",
                    "path": key,
                    "error": repr(error),
                })

    for directory, _, _ in os.walk(TARGET, topdown=False, followlinks=False):
        path = Path(directory)
        if path == TARGET or is_reparse(path):
            continue
        try:
            path.rmdir()
        except OSError:
            pass
    print(
        f"[pass2] target_seen={target_seen} target_only_archived={stats['target_only_archived']}",
        flush=True,
    )

    git_source = SOURCE / ".git"
    git_target = TARGET / ".git"
    if git_source.is_dir():
        git_target.mkdir(parents=True, exist_ok=True)
        process = subprocess.run(
            [
                "robocopy",
                str(git_source),
                str(git_target),
                "/E",
                "/COPY:DAT",
                "/DCOPY:DAT",
                "/R:2",
                "/W:1",
                "/XJ",
                "/FFT",
                "/XF",
                "*.lock",
                "/NFL",
                "/NDL",
                "/NP",
            ],
            capture_output=True,
        )
        stats["git_robocopy_rc"] = process.returncode
        robocopy_stdout = process.stdout.decode("gbk", errors="replace")
        robocopy_stderr = process.stderr.decode("gbk", errors="replace")
        (report / "robocopy_git.txt").write_text(
            robocopy_stdout + "\n" + robocopy_stderr,
            encoding="utf-8",
            errors="replace",
        )
        if process.returncode > 7:
            failures.append({"phase": "git_robocopy", "rc": process.returncode})
    print(f"[git] robocopy_rc={stats['git_robocopy_rc']}", flush=True)

    for index, record in enumerate(copied_records, 1):
        if record["bridge"]:
            stats["verified"] += 1
            continue
        try:
            if sha256(record["src"]) != sha256(record["dst"]):
                raise ValueError("SHA-256 mismatch")
            stats["verified"] += 1
        except Exception as error:
            stats["verification_failed"] += 1
            failures.append({"phase": "verify", "path": record["rel"], "error": repr(error)})
        if index % 200 == 0:
            print(
                f"[verify] {index}/{len(copied_records)} failed={stats['verification_failed']}",
                flush=True,
            )

    stats["failure_count"] = len(failures)
    stats["report_dir"] = str(report)
    summary_path.write_text(
        json.dumps({"stats": stats, "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("[summary] " + json.dumps(stats, ensure_ascii=False), flush=True)
    failed = (
        stats["copy_failed"]
        or stats["verification_failed"]
        or (stats["git_robocopy_rc"] is not None and stats["git_robocopy_rc"] > 7)
    )
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
