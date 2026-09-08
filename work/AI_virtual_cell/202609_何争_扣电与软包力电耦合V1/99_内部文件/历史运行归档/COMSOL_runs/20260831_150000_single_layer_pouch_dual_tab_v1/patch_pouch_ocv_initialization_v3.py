"""Replace the 3D template's low-SOC OCV surrogate with the verified V9 LFP table."""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_electrochem_v1.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v4_v9_ocv.mph"
RESULT = RUN / "patch_pouch_ocv_initialization_v4_result.json"
LFP_FILE = r"D:\Users\hez\Desktop\AI虚拟电芯\coin\params\LFP.dat"
TAG = "pouch_dual_tab_electrochem_v4"


def remove(tag: str) -> None:
    try:
        ModelUtil.remove(tag)
    except Exception:
        pass


def main() -> None:
    payload: dict[str, object] = {"source": str(SOURCE), "output": str(OUTPUT), "ok": False}
    remove(TAG)
    try:
        model = ModelUtil.load(TAG, str(SOURCE))
        p = model.param()
        p.set("V_charge_cut", "3.65[V]", "Inherited V9 loaded-voltage charge cutoff")
        p.set("V_discharge_cut", "2.5[V]", "Inherited V9 loaded-voltage discharge cutoff")

        try:
            model.func().remove("ocv_lfp_v9_pouch")
        except Exception:
            pass
        model.func().create("ocv_lfp_v9_pouch", "Interpolation")
        fn = model.func("ocv_lfp_v9_pouch")
        fn.label("V9 LFP OCV lookup table")
        fn.set("funcname", "ocv_lfp_v9_pouch")
        fn.set("source", "file")
        fn.set("filename", LFP_FILE)
        fn.set("interp", "piecewisecubic")
        fn.set("extrap", "const")
        fn.set("argunit", [""])
        fn.set("fununit", ["V"])

        comp = model.component("comp1")
        comp.material("mat4").propertyGroup("ElectrodePotential").set("Eeq", "ocv_lfp_v9_pouch(doc)")
        comp.material("mat4").propertyGroup("ElectrodePotential").set("dEeqdT", "0[V/K]")
        comp.material("mat4").propertyGroup("ElectrodePotential").set("cEeqref", "csmax_pos")

        soc = comp.physics("liion").feature("socicd1")
        soc.set("SOC_init", "SOC_start")
        soc.set("Ecell_0SOC", "2.35[V]")
        soc.set("Ecell_100SOC", "3.65[V]")
        soc.set("Ecell_init", "2.37[V]")

        model.study("std1").feature("cdi").set("useinitsol", "off")
        model.study("std1").feature("time").set("tlist", "range(0,10,600)")
        model.study("std1").feature("time").set("rtol", "1e-3")
        model.label("单层软包双侧出极耳：3D P2D V3（V9 LFP OCV一致初值）")
        model.save(str(OUTPUT))
        payload.update(
            {
                "ok": True,
                "ocv": "LFP.dat imported as ocv_lfp_v9_pouch(doc)",
                "initialization": {"SOC": "0.01", "Ecell_0SOC": "2.35[V]", "Ecell_init": "2.37[V]", "Ecell_100SOC": "3.65[V]"},
            }
        )
    except Exception:
        payload["traceback"] = traceback.format_exc()
    finally:
        remove(TAG)
        RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("MPH_TOOL_RESULT_BEGIN")
        print(json.dumps(payload, ensure_ascii=False))
        print("MPH_TOOL_RESULT_END")


if __name__ in ("__main__", "builtins"):
    main()
