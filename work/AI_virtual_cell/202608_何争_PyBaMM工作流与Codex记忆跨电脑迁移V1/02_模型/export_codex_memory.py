from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path):
    return sorted(path for path in root.rglob("*") if path.is_file())


def write_zip(archive: Path, sources: list[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for source, prefix in sources:
            if source.is_file():
                output.write(source, f"{prefix}/{source.name}")
                continue
            for path in iter_files(source):
                output.write(path, f"{prefix}/{path.relative_to(source).as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export local Codex memories and session evidence.")
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-sessions", action="store_true")
    args = parser.parse_args()

    codex_home = args.codex_home.resolve()
    output = args.output.resolve()
    memories = codex_home / "memories"
    if not memories.is_dir():
        raise FileNotFoundError(f"Codex memories not found: {memories}")

    output.mkdir(parents=True, exist_ok=True)
    mirror = output / "codex_memory_tree" / "memories"
    if mirror.exists():
        raise FileExistsError(f"Refusing to overwrite an existing memory mirror: {mirror}")
    shutil.copytree(memories, mirror)

    archives: list[Path] = []
    memory_archive = output / "Codex_long_term_memories_complete.zip"
    write_zip(memory_archive, [(memories, "memories")])
    archives.append(memory_archive)

    if args.include_sessions:
        session_sources: list[tuple[Path, str]] = []
        for name in ("sessions", "archived_sessions", "automations"):
            source = codex_home / name
            if source.exists():
                session_sources.append((source, name))
        session_index = codex_home / "session_index.jsonl"
        if session_index.exists():
            session_sources.append((session_index, "index"))
        evidence_archive = output / "Codex_historical_sessions_evidence.zip"
        write_zip(evidence_archive, session_sources)
        archives.append(evidence_archive)

    memory_files = iter_files(memories)
    inventory = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_codex_home": str(codex_home),
        "memory_file_count": len(memory_files),
        "memory_total_bytes": sum(path.stat().st_size for path in memory_files),
        "memory_files": [
            {
                "path": path.relative_to(memories).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in memory_files
        ],
        "archives": [
            {"path": path.name, "size": path.stat().st_size, "sha256": sha256(path)}
            for path in archives
        ],
        "excluded_by_design": [
            "auth credentials and tokens",
            "Codex caches and bundled runtimes",
            "live desktop SQLite state",
            "unsanitized config.toml",
        ],
    }
    (output / "memory_export_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
