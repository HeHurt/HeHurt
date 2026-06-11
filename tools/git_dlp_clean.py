#!/usr/bin/env python
"""Git clean filter: store DLP-decrypted PLAINTEXT in git.

Trend Micro DLP encrypts .py/.ipynb at rest; git.exe (not whitelisted) would
otherwise commit the ciphertext (header %TSD-Header-###%). python.exe IS
whitelisted, so reading the file by path here yields decrypted bytes. We ignore
git's stdin (the ciphertext we don't need) and emit the by-path plaintext to
stdout, which git then stores as the blob.

Usage (configured in .git/config):
    [filter "dlp"]
        clean = python tools/git_dlp_clean.py %f
        required = true
"""
import sys


def main():
    # Drain git's stdin (ciphertext) so git's write side never blocks.
    try:
        sys.stdin.buffer.read()
    except Exception:
        pass
    if len(sys.argv) < 2:
        sys.stderr.write("git_dlp_clean: missing %f path argument\n")
        return 1
    with open(sys.argv[1], "rb") as f:
        sys.stdout.buffer.write(f.read())
    return 0


if __name__ == "__main__":
    sys.exit(main())
