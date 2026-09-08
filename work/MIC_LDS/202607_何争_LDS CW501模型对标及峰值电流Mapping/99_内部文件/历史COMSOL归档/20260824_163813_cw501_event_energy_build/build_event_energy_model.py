import hashlib
import json
from pathlib import Path

from com.comsol.model.util import ModelUtil


SOURCE = Path(r"D:\Users\hez\Desktop\mic\超大\Case1~41D电化学模型不同长度_CW501设计参数.mph")
OUTPUT = Path(r"D:\Users\hez\Desktop\mic\超大\Case1~41D电化学模型不同长度_CW501设计参数_事件循环二圈能效.mph")
REPORT = Path(r"C:\HithiumSSD\hithium\COMSOL\runs\20260824_163813_cw501_event_energy_build\patch_result.json")
TAG = "cw501_event_energy_build"

STATE_NAMES = [
    "charge1",
    "discharge1",
    "charge2",
    "hold",
    "discharge2",
    "TimeOfSwitch",
    "hold_dis",
    "cycle_id",
]


def fingerprint(path):
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }


def string_array(node, name):
    return [str(value) for value in node.getStringArray(name)]


def set_reinitialization(node, values):
    node.set("useConsistentInit", True)
    node.set("reInitName", STATE_NAMES)
    node.set("reInitValue", values)
    node.set("StudyStep", "std1/time")


def remove_if_present(manager, tag):
    try:
        manager.remove(tag)
    except Exception:
        pass


def verify_saved_model(path):
    verify_tag = TAG + "_verify"
    remove_if_present(ModelUtil, verify_tag)
    saved = ModelUtil.load(verify_tag, str(path))
    try:
        comp = saved.component("comp1")
        event = comp.physics("ev")
        ge = comp.physics("ge")
        checks = {
            "discrete_state_names": string_array(event.feature("ds1"), "dim") == STATE_NAMES,
            "discrete_state_initial_values": string_array(event.feature("ds1"), "dimInit")
            == ["1", "0", "0", "0", "0", "0", "0", "1"],
            "discharge_to_rest": string_array(event.feature("impl1"), "reInitValue")
            == ["0", "0", "0", "0", "0", "root.t", "1", "cycle_id+1"],
            "charge_rest_to_discharge_condition": str(event.feature("impl3").getString("condition"))
            == "(OkToSwitch>0)&&(hold>0)",
            "discharge_rest_to_charge_exists": "impl5" in [str(tag) for tag in event.feature().tags()],
            "second_cycle_capacity_states": string_array(ge.feature("ge1"), "name")
            == ["Q1", "Q_ch_2", "Q_dis_2"],
            "second_cycle_energy_states": string_array(ge.feature("ge2"), "name")
            == ["W1", "E_ch_2", "E_dis_2"],
            "global_evaluation_exists": "gev_cycle2" in [str(tag) for tag in saved.result().numerical().tags()],
            "result_table_exists": "tbl_cycle2" in [str(tag) for tag in saved.result().table().tags()],
        }
        return checks
    finally:
        ModelUtil.remove(verify_tag)


source_before = fingerprint(SOURCE)
if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite existing output model: {OUTPUT}")

remove_if_present(ModelUtil, TAG)
model = ModelUtil.load(TAG, str(SOURCE))
try:
    comp = model.component("comp1")
    event = comp.physics("ev")

    discrete = event.feature("ds1")
    discrete.set("dim", STATE_NAMES)
    discrete.set("dimInit", ["1", "0", "0", "0", "0", "0", "0", "1"])
    discrete.set(
        "dimDescr",
        ["", "", "", "", "", "", "放电后静置状态", "当前充放电循环编号"],
    )

    discharge_to_rest = event.feature("impl1")
    discharge_to_rest.label("放电转静置")
    discharge_to_rest.set("condition", "(discharge1up<0)")
    set_reinitialization(
        discharge_to_rest,
        ["0", "0", "0", "0", "0", "root.t", "1", "cycle_id+1"],
    )

    charge_to_rest = event.feature("impl2")
    set_reinitialization(
        charge_to_rest,
        ["0", "0", "0", "1", "0", "root.t", "0", "cycle_id"],
    )

    charge_rest_to_discharge = event.feature("impl3")
    charge_rest_to_discharge.set("condition", "(OkToSwitch>0)&&(hold>0)")
    set_reinitialization(
        charge_rest_to_discharge,
        ["0", "0", "0", "0", "1", "root.t", "0", "cycle_id"],
    )

    remove_if_present(event.feature(), "impl5")
    discharge_rest_to_charge = event.feature().create("impl5", "ImplicitEvent")
    discharge_rest_to_charge.label("静置转充电")
    discharge_rest_to_charge.set("condition", "(OkToSwitch>0)&&(hold_dis>0)")
    set_reinitialization(
        discharge_rest_to_charge,
        ["0", "0", "1", "0", "0", "root.t", "0", "cycle_id"],
    )

    current = comp.variable("var1")
    current.set(
        "I",
        "root.i_1C*0.125*3.2[V]/(comp1.vol)*charge1"
        "-root.i_1C*0.125*3.2[V]/(comp1.vol)*discharge1"
        "+root.i_1C*C*3.2[V]/(comp1.vol)*charge2"
        "+0[A]*hold"
        "-root.i_1C*C*3.2[V]/(comp1.vol)*discharge2"
        "+0[A]*hold_dis",
    )

    ge = comp.physics("ge")
    capacity = ge.feature("ge1")
    capacity.set("name", ["Q1", "Q_ch_2", "Q_dis_2"])
    capacity.set(
        "equation",
        [
            "Q1t-abs(liion.Its_ec1)",
            "Q_ch_2t-liion.Its_ec1*charge2*(cycle_id==2)",
            "Q_dis_2t+liion.Its_ec1*discharge2*(cycle_id==2)",
        ],
    )
    capacity.set("initialValueU", ["0", "0", "0"])
    capacity.set("initialValueUt", ["0", "0", "0"])
    capacity.set("description", ["全程累计容量", "第二圈充电容量", "第二圈放电容量"])

    energy = ge.feature("ge2")
    energy.set("name", ["W1", "E_ch_2", "E_dis_2"])
    energy.set(
        "equation",
        [
            "W1t-abs(liion.Its_ec1*voltage)",
            "E_ch_2t-liion.Its_ec1*voltage*charge2*(cycle_id==2)",
            "E_dis_2t+liion.Its_ec1*voltage*discharge2*(cycle_id==2)",
        ],
    )
    energy.set("initialValueU", ["0", "0", "0"])
    energy.set("initialValueUt", ["0", "0", "0"])
    energy.set("description", ["全程累计能量", "第二圈充电能量", "第二圈放电能量"])

    remove_if_present(model.result().table(), "tbl_cycle2")
    table = model.result().table().create("tbl_cycle2", "Table")
    table.label("第二圈充放电能量与能效")

    remove_if_present(model.result().numerical(), "gev_cycle2")
    evaluation = model.result().numerical().create("gev_cycle2", "EvalGlobal")
    evaluation.label("第二圈能效")
    evaluation.set(
        "expr",
        ["cycle_id", "Q_ch_2", "Q_dis_2", "E_ch_2", "E_dis_2", "E_dis_2/E_ch_2"],
    )
    evaluation.set("unit", ["1", "Ah", "Ah", "Wh", "Wh", "1"])
    evaluation.set(
        "descr",
        ["循环编号", "第二圈充电容量", "第二圈放电容量", "第二圈充电能量", "第二圈放电能量", "第二圈能效"],
    )
    evaluation.set("table", "tbl_cycle2")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(OUTPUT))
finally:
    ModelUtil.remove(TAG)

source_after = fingerprint(SOURCE)
checks = verify_saved_model(OUTPUT)
if source_before != source_after:
    raise RuntimeError("Source model fingerprint changed during save-as workflow")
if not all(checks.values()):
    raise RuntimeError(f"Reload verification failed: {checks}")

payload = {
    "ok": True,
    "source": source_before,
    "source_after": source_after,
    "source_modified": False,
    "output_model": fingerprint(OUTPUT),
    "reload_checks": checks,
}
REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False))
