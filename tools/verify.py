"""
Pre-Commit 验证脚本 — Harness 质量闸门
使用方法: python verify.py [--src] [--params] [--all]

src   : lint + 单元测试 BatteryProject/src
params: 参数文件可调用性检查
all   : 全部检查
"""
import argparse
import importlib
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
BATTERY_PROJECT_DIR = ROOT / "BatteryProject"
PARAMS_DIR = ROOT / "params"


def _pythonpath_with_project(env):
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    paths = [str(BATTERY_PROJECT_DIR), str(PARAMS_DIR)]
    existing = env.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def run_cmd(cmd: list[str], label: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  [{label}] {' '.join(cmd)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    passed = result.returncode == 0
    status = "PASS" if passed else "FAIL"
    print(f"  -> {status}")
    return passed


def run_cmd_env(cmd: list[str], label: str, env=None) -> bool:
    print(f"\n{'='*60}")
    print(f"  [{label}] {' '.join(cmd)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=str(ROOT), env=env)
    passed = result.returncode == 0
    status = "PASS" if passed else "FAIL"
    print(f"  -> {status}")
    return passed


def verify_src() -> bool:
    ok = True

    # 1. Lint (放宽对已有代码的风格检查，专注于逻辑错误)
    env = _pythonpath_with_project(os.environ.copy())

    lint_ok = run_cmd_env(
        [sys.executable, "-m", "flake8",
         "BatteryProject/src/",
         "--max-line-length=120",
         "--jobs=1",
         "--ignore=E501,W503,E402,W504,E302,E741,W292,W293,W391,E241,F401,F841"],
        "Lint (flake8)",
        env=env
    )
    ok = ok and lint_ok

    # 2. 单元测试 (设置 PYTHONPATH 确保 src 可导入)
    test_ok = run_cmd_env(
        [sys.executable, "-m", "pytest",
         "BatteryProject/tests/", "-q", "--tb=short", "-p", "no:cacheprovider"],
        "Unit Tests (pytest)",
        env=env
    )
    ok = ok and test_ok

    return ok


def verify_params() -> bool:
    params_dir = PARAMS_DIR
    ok = True

    for py_file in sorted(params_dir.glob("params*.py")):
        if py_file.name.startswith("__"):
            continue
        module_name = py_file.stem
        label = f"Params: {module_name}"
        print(f"\n{'='*60}")
        print(f"  [{label}]")
        print(f"{'='*60}")

        try:
            # 确保 params 目录在 sys.path
            if str(params_dir) not in sys.path:
                sys.path.insert(0, str(params_dir))

            mod = importlib.import_module(module_name)
            importlib.reload(mod)

            func = getattr(mod, "get_hithium_params", None)
            if func is None:
                print("  -> FAIL : 缺少 get_hithium_params 函数")
                ok = False
                continue

            result = func(1, 298.15)
            assert isinstance(result, dict), "返回值不是 dict"
            assert "Nominal cell capacity [A.h]" in result, \
                "缺少 'Nominal cell capacity [A.h]' 键"

            cap = result["Nominal cell capacity [A.h]"]
            print(f"  -> PASS : 容量 = {cap} Ah")

        except Exception as e:
            print(f"  -> FAIL : {e}")
            ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="Hithium Harness 验证")
    parser.add_argument("--src", action="store_true", help="验证 src (lint + test)")
    parser.add_argument("--params", action="store_true", help="验证参数文件")
    parser.add_argument("--all", action="store_true", help="全部验证")
    args = parser.parse_args()

    if not (args.src or args.params or args.all):
        args.all = True

    results = {}
    if args.src or args.all:
        results["src"] = verify_src()
    if args.params or args.all:
        results["params"] = verify_params()

    # 汇总
    print(f"\n{'='*60}")
    print("  验证汇总")
    print(f"{'='*60}")
    all_ok = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name:10s} : {status}")
        if not passed:
            all_ok = False

    if all_ok:
        print("\n  全部通过")
    else:
        print("\n  存在失败项 - 请修复后再继续")
        sys.exit(1)


if __name__ == "__main__":
    main()
