"""Independently reload, assert and smoke-test the 2D coin-V9 electrochemical migration."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_2d_cross_section_v2_coin_v9_electrochem.mph"
OUTPUT = RUN / "pouch_dual_tab_2d_cross_section_v3_coin_v9_electrochem_smoke_solved.mph"
RESULT = RUN / "verify_and_smoke_pouch_2d_electrochem_v2_result.json"
PARAMS = Path(r"D:\Users\hez\Desktop\AI虚拟电芯\coin\params")
TAG = "pouch_2d_electrochem_v2_verify"


def remove_model() -> None:
    try:
        ModelUtil.remove(TAG)
    except Exception:
        pass


def entities(selection, dimension: int) -> list[int]:
    return sorted(int(item) for item in selection.entities(dimension))


def assert_equal(name: str, actual, expected) -> None:
    if actual != expected:
        raise RuntimeError(f"{name}: {actual!r} != {expected!r}")


def last_finite(values) -> float:
    try:
        outer_length = len(values)
        if outer_length:
            first = values[0]
            try:
                return float(first[len(first) - 1])
            except Exception:
                return float(values[outer_length - 1])
    except Exception:
        pass
    rows = values
    if not isinstance(rows, (list, tuple)):
        return float(rows)
    flat: list[float] = []
    for row in rows:
        if isinstance(row, (list, tuple)):
            flat.extend(float(item) for item in row)
        else:
            flat.append(float(row))
    return flat[-1]


def main() -> None:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    remove_model()
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        comp = model.component("comp1")
        liion = comp.physics("liion")

        expected_parameters = {
            "SOC": ".01",
            "rp_neg": "4.5e-6[m]",
            "rp_pos": "5.5e-7[m]",
            "Ds_neg": "1.060E-14[m^2/s]*1.5",
            "Ds_pos": "2.4E-16 [m^2/s]",
            "k_neg": "1.2121E-9[m/s]",
            "k_pos": "1.1131E-10[m/s]",
            "sigma_neg": "0.04453[S/cm]",
            "sigma_pos": "100[S/m]",
            "epsl_sep": "0.4",
            "Ac": "W_cell*H_cell",
            "C_rate": "0.5",
        }
        actual_parameters = {name: str(model.param().get(name)) for name in expected_parameters}
        assert_equal("parameters", actual_parameters, expected_parameters)

        expected_functions = {
            "ocv_lfp_base": PARAMS / "LFP.dat",
            "ocv_gr_discharge": PARAMS / "Gr_ocv.txt",
            "ocv_gr_charge": PARAMS / "Gr_charge.dat",
            "ely_sigma": PARAMS / "E_sigma.dat",
            "ely_D": PARAMS / "E_DL_int1.dat",
            "ely_tplus": PARAMS / "E_transpNm.dat",
        }
        actual_functions = {tag: str(model.func(tag).getString("filename")) for tag in expected_functions}
        assert_equal("function paths", actual_functions, {tag: str(path) for tag, path in expected_functions.items()})

        feature_tags = [str(item) for item in liion.feature().tags()]
        if "axi1" in feature_tags:
            raise RuntimeError(f"Axisymmetric feature remained in Cartesian model: {feature_tags}")
        physics = {
            "pce1": entities(liion.feature("pce1").selection(), 2),
            "sep1": entities(liion.feature("sep1").selection(), 2),
            "pce2": entities(liion.feature("pce2").selection(), 2),
            "cc1": entities(liion.feature("cc1").selection(), 2),
            "negative_terminal": entities(liion.feature("egnd1").selection(), 1),
            "positive_terminal": entities(liion.feature("ecd1").selection(), 1),
        }
        expected_physics = {
            "pce1": [4], "sep1": [5], "pce2": [6], "cc1": [1, 2, 3, 7, 8, 9],
            "negative_terminal": [1], "positive_terminal": [30],
        }
        assert_equal("physics selections", physics, expected_physics)

        materials = {
            "mat1": entities(comp.material("mat1").selection(), 2),
            "mat2": entities(comp.material("mat2").selection(), 2),
            "mat3": entities(comp.material("mat3").selection(), 2),
            "mat4": entities(comp.material("mat4").selection(), 2),
            "mat5": entities(comp.material("mat5").selection(), 2),
        }
        assert_equal(
            "material selections", materials,
            {"mat1": [4], "mat2": [6], "mat3": [5], "mat4": [7, 8, 9], "mat5": [1, 2, 3]},
        )
        assert_equal("graphite Ds", str(liion.feature("pce1").feature("pin1").getString("Ds")), "Ds_neg")
        assert_equal("LFP Ds", str(liion.feature("pce2").feature("pin1").getString("Ds")), "Ds_pos")
        assert_equal("graphite k", str(liion.feature("pce1").feature("per1").getString("k")), "k_neg")
        assert_equal("LFP k", str(liion.feature("pce2").feature("per1").getString("k")), "k_pos")
        assert_equal(
            "LFP OCV", str(liion.feature("pce2").feature("per1").getString("Eeq")),
            "ocv_lfp_base(liion.cs_surface/liion.csmax)+0.02[V]",
        )
        assert_equal("initial SOC", str(liion.feature("socicd1").getString("SOC_init")), "SOC")
        assert_equal("terminal current", str(liion.feature("ecd1").getString("Its")), "I_app")

        axis = comp.view("view1").axis()
        view = {"xscale": str(axis.getString("xscale")), "yscale": str(axis.getString("yscale"))}
        assert_equal("view scale", view, {"xscale": "1", "yscale": "100"})

        comp.mesh("mesh1").run()
        mesh = {
            "features": [str(item) for item in comp.mesh("mesh1").feature().tags()],
            "hmax": str(comp.mesh("mesh1").feature("size").getString("hmax")),
            "hmin": str(comp.mesh("mesh1").feature("size").getString("hmin")),
        }
        if "map1" not in mesh["features"]:
            raise RuntimeError(f"Mapped mesh missing after reload: {mesh}")

        # Short, bounded smoke run. This proves the migrated physics can initialize
        # and advance in time; it is not a full charge/discharge validation.
        model.study("std1").run()

        terminal_values: dict[str, float] = {}
        for tag, selection_name in (("av_neg", "sel_neg_terminal_2d"), ("av_pos", "sel_pos_terminal_2d")):
            model.result().numerical().create(tag, "AvLine")
            numerical = model.result().numerical(tag)
            numerical.selection().named(selection_name)
            numerical.set("expr", "phis")
            numerical.set("unit", "V")
            terminal_values[tag] = last_finite(numerical.getReal())
        terminal_values["voltage"] = terminal_values["av_pos"] - terminal_values["av_neg"]

        model.label("Single-layer pouch 2D V3 - coin V9 electrochemistry, 60 s smoke solved")
        model.save(str(OUTPUT))
        payload.update({
            "ok": True,
            "parameters": actual_parameters,
            "functions": actual_functions,
            "physics": physics,
            "materials": materials,
            "view": view,
            "mesh": mesh,
            "smoke": {"tlist": "range(0,5,60)", **terminal_values},
        })
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        remove_model()
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(payload, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
