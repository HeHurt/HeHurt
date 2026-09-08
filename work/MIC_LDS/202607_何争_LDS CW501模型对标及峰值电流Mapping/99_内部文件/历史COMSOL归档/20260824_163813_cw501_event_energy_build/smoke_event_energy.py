import csv
import json
import time
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


MODEL = r"D:\Users\hez\Desktop\mic\超大\Case1~41D电化学模型不同长度_CW501设计参数_事件循环二圈能效.mph"
RUN_DIR = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260824_163813_cw501_event_energy_build")
REPORT = RUN_DIR / "smoke_metrics.json"
TIMELINE = RUN_DIR / "smoke_timeline.csv"
ERROR = RUN_DIR / "error_report.txt"
TAG = "cw501_event_energy_smoke"
EVAL_TAG = "__cycle2_smoke_eval"

EXPRESSIONS = [
    ("time_s", "t", "s"),
    ("cycle_id", "cycle_id", "1"),
    ("charge1", "charge1", "1"),
    ("charge2", "charge2", "1"),
    ("hold_charge", "hold", "1"),
    ("discharge2", "discharge2", "1"),
    ("hold_discharge", "hold_dis", "1"),
    ("voltage_V", "voltage", "V"),
    ("current_A", "liion.Its_ec1", "A"),
    ("Q_ch_2_Ah", "Q_ch_2", "Ah"),
    ("Q_dis_2_Ah", "Q_dis_2", "Ah"),
    ("E_ch_2_Wh", "E_ch_2", "Wh"),
    ("E_dis_2_Wh", "E_dis_2", "Wh"),
    ("efficiency", "E_dis_2/E_ch_2", "1"),
]


def tags(manager):
    try:
        return [str(value) for value in manager.tags()]
    except Exception:
        return []


def transitions(rows, state_name):
    result = []
    previous = rows[0][state_name]
    for row in rows[1:]:
        current = row[state_name]
        if current != previous:
            result.append({"time_s": row["time_s"], "from": previous, "to": current})
            previous = current
    return result


started = time.time()
try:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
    model = ModelUtil.load(TAG, MODEL)
    study = model.study("std1")
    study.feature("param2").set("plistarr", ["580", "0.062205123"])
    study.feature("param").set("plistarr", ["0.25"])
    study.feature("time").set("tlist", "range(0,25/C,25000/C)")
    study.run()

    numerical = model.result().numerical()
    try:
        numerical.remove(EVAL_TAG)
    except Exception:
        pass
    node = numerical.create(EVAL_TAG, "EvalGlobal")
    node.set("expr", [item[1] for item in EXPRESSIONS])
    node.set("unit", [item[2] for item in EXPRESSIONS])
    node.set("innerinput", "all")

    dataset_errors = {}
    used_dataset = None
    values = None
    for dataset in reversed(tags(model.result().dataset())):
        try:
            node.set("data", dataset)
            candidate = node.getReal()
            if candidate is not None and len(candidate) == len(EXPRESSIONS) and len(candidate[0]) > 1:
                values = [[float(value) for value in series] for series in candidate]
                used_dataset = dataset
                break
        except Exception as exc:
            dataset_errors[dataset] = str(exc)
    if values is None:
        raise RuntimeError(f"No evaluable transient dataset found: {dataset_errors}")

    row_count = min(len(series) for series in values)
    rows = []
    for index in range(row_count):
        rows.append({item[0]: values[position][index] for position, item in enumerate(EXPRESSIONS)})

    with TIMELINE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[item[0] for item in EXPRESSIONS])
        writer.writeheader()
        writer.writerows(rows)

    final = rows[-1]
    payload = {
        "ok": True,
        "model": MODEL,
        "runtime_overrides": {
            "L_JR_pos_mm": 580,
            "R_mohm": 0.062205123,
            "C": 0.25,
            "tlist": "range(0,25/C,25000/C)",
        },
        "dataset": used_dataset,
        "row_count": row_count,
        "elapsed_s": time.time() - started,
        "final": final,
        "final_display_units": {
            "Q_ch_2_Ah": final["Q_ch_2_Ah"] / 3600,
            "Q_dis_2_Ah": final["Q_dis_2_Ah"] / 3600,
            "E_ch_2_Wh": final["E_ch_2_Wh"] / 3600,
            "E_dis_2_Wh": final["E_dis_2_Wh"] / 3600,
            "efficiency": final["efficiency"],
        },
        "transitions": {
            "cycle_id": transitions(rows, "cycle_id"),
            "hold_charge": transitions(rows, "hold_charge"),
            "hold_discharge": transitions(rows, "hold_discharge"),
        },
        "acceptance": {
            "reached_after_second_discharge": final["cycle_id"] >= 3,
            "second_charge_energy_positive": final["E_ch_2_Wh"] > 0,
            "second_discharge_energy_positive": final["E_dis_2_Wh"] > 0,
            "efficiency_physical": 0 < final["efficiency"] <= 1.05,
            "charge_rest_occurred": any(row["hold_charge"] > 0.5 for row in rows),
            "discharge_rest_occurred": any(row["hold_discharge"] > 0.5 for row in rows),
        },
        "timeline_csv": str(TIMELINE),
    }
    if not all(payload["acceptance"].values()):
        raise RuntimeError(f"Smoke acceptance failed: {payload}")
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if ERROR.exists():
        ERROR.unlink()
    print(json.dumps(payload, ensure_ascii=False))
except Exception:
    ERROR.write_text(traceback.format_exc(), encoding="utf-8")
    raise
finally:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass
