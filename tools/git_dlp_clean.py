#!/usr/bin/env python
"""Git clean filter: store DLP-decrypted plaintext in git."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time


DLP_HEADER = b"%TSD-Header"


def read_via_code(path):
    code_exe = os.environ.get("HITHIUM_CODE_EXE") or shutil.which("Code.exe")
    if not code_exe:
        code_exe = r"D:\软件安装\Microsoft VS Code\Code.exe"
    if not os.path.isfile(code_exe):
        raise RuntimeError(f"Code.exe not found: {code_exe}")

    fd, temp_path = tempfile.mkstemp(prefix="git-dlp-", suffix=".txt")
    os.close(fd)
    os.unlink(temp_path)
    source_path = os.path.abspath(path)
    script = (
        "const fs=require('fs');"
        f"fs.writeFileSync({json.dumps(temp_path)},"
        f"fs.readFileSync({json.dumps(source_path)}));"
    )
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    try:
        result = subprocess.run(
            [code_exe, "-e", script],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        deadline = time.monotonic() + 5
        while not os.path.exists(temp_path) and time.monotonic() < deadline:
            time.sleep(0.05)
        if result.returncode != 0 or not os.path.exists(temp_path):
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Code.exe bridge failed: {error}")
        with open(temp_path, "rb") as handle:
            data = handle.read()
        if data.startswith(DLP_HEADER):
            raise RuntimeError("Code.exe bridge returned DLP ciphertext")
        return data
    finally:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass


def main():
    try:
        sys.stdin.buffer.read()
    except Exception:
        pass
    if len(sys.argv) < 2:
        sys.stderr.write("git_dlp_clean: missing %f path argument\n")
        return 1
    with open(sys.argv[1], "rb") as handle:
        data = handle.read()
    if data.startswith(DLP_HEADER):
        data = read_via_code(sys.argv[1])
    sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
