"""Run and persist the first 3D P2D pouch-cell smoke solution."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v6_fast_smoke.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_smoke_v6.mph"
RESULT = RUN / "run_pouch_electrochem_smoke_v6_result.json"
TAG = "pouch_dual_tab_smoke_v6"


def remove() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def as_float_list(value):
    try:
        return [float(x) for x in value]
    except Exception:
        try:
            return [float(value)]
        except Exception:
            return [str(value)]


def main() -> None:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    remove()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        model.study("std1").feature("time").set("tlist", "range(0,10,600)")
        model.study("std1").run()

        table = "tbl_smoke_metrics"
        eval_tag = "gev_smoke_metrics"
        model.result().table().create(table, "Table")
        model.result().numerical().create(eval_tag, "EvalGlobal")
        evaluator = model.result().numerical(eval_tag)
        evaluator.set("data", "dset1")
        evaluator.set("table", table)
        evaluator.set(
            "expr",
            ["liion.phis0_ec1", "liion.SOC_cell", "liion.I_1C_cell", "I_app"],
        )
        evaluator.set(
            "descr",
            ["terminal_voltage_V", "cell_soc", "one_c_current_A", "applied_current_A"],
        )
        evaluator.set("unit", ["V", "1", "A", "A"])
        evaluator.set("looplevelinput", ["last"])
        evaluator.setResult()
        raw = evaluator.getReal()

        model.result().export().create("exp_smoke_metrics", "Table")
        model.result().export("exp_smoke_metrics").set("table", table)
        model.result().export("exp_smoke_metrics").set("filename", str(RUN / "smoke_metrics.csv"))
        model.result().export("exp_smoke_metrics").set("header", "on")
        model.result().export("exp_smoke_metrics").run()
        model.save(str(OUTPUT))

        payload.update(
            {
                "ok": True,
                "metrics_last_solution": {
                    "terminal_voltage_V": as_float_list(raw[0]),
                    "cell_soc": as_float_list(raw[1]),
                    "one_c_current_A": as_float_list(raw[2]),
                    "applied_current_A": as_float_list(raw[3]),
                },
                "result_csv": str(RUN / "smoke_metrics.csv"),
            }
        )
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        remove()
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(payload, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
