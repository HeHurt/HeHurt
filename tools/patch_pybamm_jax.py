"""
Fix: jax 0.4.28+ 删除了 jax.extend.backend.get_backend()
     PyBaMM v26.4.2 的 evaluate_python.py 仍然调用此 API
     解决方案：在 site-packages 安装 sitecustomize.py 添加兼容层
"""
import sys
import pathlib

# 写 sitecustomize.py 到 site-packages
site_pkgs = pathlib.Path(sys.exec_prefix) / "Lib" / "site-packages"
target = site_pkgs / "sitecustomize.py"

patch_code = '''\
# Auto-generated compatibility patch: jax.extend.backend.get_backend()
# jax >=0.4.28 removed get_backend(); pybamm v26.4.2 still calls it.
try:
    import jax
    import jax.extend.backend as _jeb
    if not hasattr(_jeb, "get_backend"):
        class _FakeBackend:
            def __init__(self, p): self.platform = p
        def _get_backend():
            return _FakeBackend(jax.default_backend())
        _jeb.get_backend = _get_backend
        print("[sitecustomize] Patched jax.extend.backend.get_backend -> jax.default_backend()")
except Exception as _e:
    print(f"[sitecustomize] jax patch skipped: {_e}")
'''

# Append if file already exists, else create
if target.exists():
    existing = target.read_text(encoding="utf-8")
    if "jax.extend.backend.get_backend" in existing:
        print(f"Patch already present in {target}")
    else:
        target.write_text(existing + "\n" + patch_code, encoding="utf-8")
        print(f"Appended patch to existing {target}")
else:
    target.write_text(patch_code, encoding="utf-8")
    print(f"Created {target}")
