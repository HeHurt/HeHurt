"""Read the generated solver configuration used by the pouch model."""

from __future__ import annotations

import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v4_v9_ocv.mph"
TAG = "audit_pouch_v4_solver"


def get(node, key):
    try:
        return node.getString(key)
    except Exception:
        try:
            return node.getStringArray(key)
        except Exception:
            return None


def main() -> None:
    result = {"ok": False}
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        sol = model.sol("sol1")
        result = {
            "ok": True,
            "sol_features": list(sol.feature().tags()),
            "s1": {key: get(sol.feature("s1"), key) for key in ("stol", "rtol", "maxiter", "linsolver", "nonlin", "usescaleresvar")},
            "t1": {key: get(sol.feature("t1"), key) for key in ("rtol", "tlist", "initialstepbdf", "maxstepbdf")},
        }
    except Exception as exc:
        result = {"ok": False, "error": repr(exc)}
    finally:
        try:
            ModelUtil.remove(TAG)
        except Exception:
            pass
        (RUN / "audit_pouch_v4_solver_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(result, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
