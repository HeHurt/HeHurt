"""Probe a COMSOL .mph file through a persistent sim-plugin-comsol session.

Usage:
    uv run python tools/comsol_mph_probe.py "D:/path/to/model.mph"

The script reuses the default live COMSOL session when available. If no session
exists, it starts a headless sim COMSOL session and then loads the model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run_sim(args: list[str], *, timeout: int = 300) -> dict:
    proc = subprocess.run(
        ["sim", "--json", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "sim command failed\n"
            f"command: sim --json {' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"sim returned non-JSON output:\n{proc.stdout}") from exc


def choose_session(explicit_session: str | None, connect: bool, ui_mode: str) -> tuple[str, bool]:
    if explicit_session:
        return explicit_session, False

    sessions = run_sim(["ps"], timeout=60)
    default_session = sessions.get("default_session")
    if default_session:
        return str(default_session), False

    if not connect:
        raise RuntimeError("No live COMSOL sim session found. Re-run without --no-connect.")

    connected = run_sim(["connect", "--solver", "comsol", "--ui-mode", ui_mode], timeout=300)
    session_id = connected.get("session_id") or connected.get("data", {}).get("session_id")
    if not session_id:
        raise RuntimeError(f"Could not find session_id in connect output:\n{json.dumps(connected, ensure_ascii=False)}")
    return str(session_id), True


def safe_tag(path: Path, tag: str | None) -> str:
    if tag:
        return tag
    stem = re.sub(r"[^0-9A-Za-z_]+", "_", path.stem).strip("_") or "model"
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return f"probe_{stem}_{digest}"[:60]


def file_header(path: Path) -> dict:
    head = path.read_bytes()[:128]
    return {
        "size": path.stat().st_size,
        "head_repr": repr(head[:48]),
        "tsd_header": b"%TSD-Header-" in head,
        "zip_header": head.startswith(b"PK"),
        "hdf5_header": head.startswith(bytes.fromhex("89 48 44 46 0d 0a 1a 0a")),
    }


def build_probe_snippet(path: Path, tag: str) -> str:
    return f'''
def safe(label, fn):
    try:
        return fn()
    except Exception as exc:
        return {{"error": label, "type": type(exc).__name__, "message": str(exc)}}


def tags(container):
    return safe("tags", lambda: [str(x) for x in container.tags()])


path = {str(path)!r}
tag = {tag!r}

existing = [str(x) for x in ModelUtil.tags()]
if tag in existing:
    safe("ModelUtil.remove", lambda: ModelUtil.remove(tag))

m = ModelUtil.load(tag, path)
out = {{
    "loaded": True,
    "tag": str(m.tag()),
    "label": str(m.label()),
    "model_path": safe("modelPath", lambda: str(m.modelPath())),
    "model_tags": [str(x) for x in ModelUtil.tags()],
    "components": tags(m.component()),
    "studies": tags(m.study()),
    "results": tags(m.result()),
    "param_varnames": safe("param.varnames", lambda: [str(x) for x in m.param().varnames()]),
}}

if isinstance(out["components"], list):
    out["component_details"] = {{}}
    for comp_tag in out["components"]:
        comp = m.component(comp_tag)
        detail = {{
            "geom": tags(comp.geom()),
            "material": tags(comp.material()),
            "physics": tags(comp.physics()),
            "mesh": tags(comp.mesh()),
        }}
        if isinstance(detail["physics"], list):
            detail["physics_features"] = {{}}
            for phys_tag in detail["physics"]:
                phys = comp.physics(phys_tag)
                detail["physics_features"][phys_tag] = {{
                    "type": safe("physics.getType", lambda phys=phys: str(phys.getType())),
                    "features": tags(phys.feature()),
                }}
        out["component_details"][comp_tag] = detail

_result = out
'''


def exec_probe(session_id: str, snippet: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(snippet)
        tmp_path = Path(tmp.name)
    try:
        result = run_sim(
            ["--session", session_id, "exec", "--file", str(tmp_path), "--label", "mph-probe"],
            timeout=300,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    data = result.get("data", result)
    if not data.get("ok", False):
        raise RuntimeError(json.dumps(data, ensure_ascii=False, indent=2))
    return data.get("result", data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a COMSOL .mph file through sim-plugin-comsol.")
    parser.add_argument("mph", help="Path to the .mph file.")
    parser.add_argument("--session", help="Existing sim session id. Defaults to sim ps default session.")
    parser.add_argument("--tag", help="COMSOL ModelUtil tag to use for loading.")
    parser.add_argument("--ui-mode", default="no_gui", choices=["no_gui", "gui"], help="UI mode if a session must start.")
    parser.add_argument("--no-connect", action="store_true", help="Fail instead of starting COMSOL when no session exists.")
    args = parser.parse_args()

    path = Path(args.mph).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    session_id, started = choose_session(args.session, not args.no_connect, args.ui_mode)
    tag = safe_tag(path, args.tag)
    result = {
        "session_id": session_id,
        "started_session": started,
        "path": str(path),
        "tag": tag,
        "file_header": file_header(path),
        "model": exec_probe(session_id, build_probe_snippet(path, tag)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
