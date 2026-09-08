"""Create a 3D, single-layer LFP/graphite pouch cell from the 3D-P2D physics seed.

The geometry is rebuilt to the tab drawing supplied on 2026-08-31:
  active sheet: 52 mm x 86 mm
  stack: Cu | graphite | separator | LFP | Al
  tabs: 30 mm wide and 35 mm long on opposing short edges.

This first build intentionally keeps the tab metal as a collector-thickness
extension. The 0.20 mm welded multi-foil construction is represented later by
an explicit terminal/weld contact resistance; modelling that thickness as a
single through-stack solid would short the electrochemical layers.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from com.comsol.model.util import ModelUtil


RUN = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260831_150000_single_layer_pouch_dual_tab_v1")
SOURCE = RUN / "pouch_dual_tab_seed_v1.mph"
OUTPUT = RUN / "pouch_dual_tab_electrochem_v1.mph"
RESULT = RUN / "build_pouch_electrochem_v1_result.json"
TAG = "pouch_dual_tab_electrochem_v1"


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
        model.label("单层软包双侧出极耳：3D P2D 电化学基模 V1")
        model.comments(
            "52 mm x 86 mm active pouch sheet; 30 mm x 35 mm opposite-edge tabs; "
            "LFP/graphite P2D physics. Geometry dimensions follow 单层软包tab仿真-20260820-V2.pptx."
        )
        p = model.param()
        for name, value, description in (
            ("SOC_start", "0.01", "Initial cell SOC, inherited from coin V9"),
            ("C_rate", "0.5", "Applied C-rate for smoke and baseline"),
            ("L_sep", "9[um]", "Separator thickness inherited from coin V9"),
            ("rp_neg", "4.5[um]", "Graphite particle radius inherited from coin V9"),
            ("rp_pos", "0.55[um]", "LFP particle radius inherited from coin V9"),
            ("sigmas_neg", "4.453[S/m]", "Graphite composite electronic conductivity"),
            ("sigmas_pos", "100[S/m]", "LFP composite electronic conductivity"),
            ("csmax_neg", "29094.101[mol/m^3]", "Graphite maximum Li concentration"),
            ("csmax_pos", "20041.877[mol/m^3]", "LFP maximum Li concentration"),
            ("epss_neg", "0.655716", "Graphite active-material volume fraction"),
            ("epss_pos", "0.690170", "LFP active-material volume fraction"),
            ("epsl_neg", "0.321907", "Graphite initial electrolyte volume fraction"),
            ("epsl_sep", "0.4", "Separator initial porosity"),
            ("epsl_pos", "0.293582", "LFP initial electrolyte volume fraction"),
            ("i0ref_neg", "0.96[A/m^2]", "Negative-electrode reference exchange current density"),
            ("i0ref_pos", "0.70[A/m^2]", "Positive-electrode reference exchange current density"),
            ("tab_weld_R", "2[mohm]", "Lumped tab/weld contact resistance, initial engineering value"),
        ):
            p.set(name, value, description)

        comp = model.component("comp1")
        # Rebuild the supplied single-layer stack and the opposing-edge tabs.
        geom = comp.geom("geom1")
        geom.run()

        liion = comp.physics("liion")
        liion.feature("socicd1").set("SOC_init", "SOC_start")
        for feature, epsl, epss in (
            ("pce1", "epsl_neg", "epss_neg"),
            ("pce2", "epsl_pos", "epss_pos"),
        ):
            liion.feature(feature).set("epsl", epsl)
            liion.feature(feature).set("epss", epss)
        # The 3D-P2D template supplies electronic conductivity through each
        # electrode material property group. Do not overwrite pce*.sigmas:
        # in this COMSOL build that key is a material-input selector, not a
        # free expression slot as it is in the axisymmetric coin model.
        liion.feature("sep1").set("epsl", "epsl_sep")
        liion.feature("egnd1").set("IncludeContactResistance", "1")
        liion.feature("egnd1").set("Rc", "tab_weld_R")
        liion.feature("ec1").set("IncludeContactResistance", "1")
        liion.feature("ec1").set("Rc", "tab_weld_R")

        # LFP plateau matching the corrected coin V9 sign convention.
        comp.material("mat4").label("LFP, LiFePO4 positive electrode")
        comp.material("mat4").propertyGroup("ElectrodePotential").set(
            "Eeq",
            "3.42+0.03*tanh((0.08-doc)/0.025)-0.04*tanh((doc-0.93)/0.025)",
        )
        comp.material("mat4").propertyGroup("ElectrodePotential").set("dEeqdT", "0[V/K]")
        comp.material("mat4").propertyGroup("ElectrodePotential").set("cEeqref", "csmax_pos")

        comp.variable("var1").set("I_app", "liion.I_1C_cell*C_rate")

        # Compact in-plane mesh plus swept layer mesh; avoids an automatic
        # through-thickness tetrahedral mesh for the ~176 um stack.
        mesh = comp.mesh("mesh1")
        mesh.feature("map1").selection().geom("geom1", 2)
        mesh.feature("map1").selection().set([20])
        mesh.feature("swe1").selection().set(1, 2, 3, 4, 5, 6, 7)
        mesh.run()

        std = model.study("std1")
        std.feature("time").set("tlist", "range(0,30,600)")
        std.feature("time").set("rtol", "1e-3")

        model.save(str(OUTPUT))
        payload.update(
            {
                "ok": True,
                "geometry": {
                    "active_sheet": "52[mm] x 86[mm]",
                    "tabs": "30[mm] x 35[mm] on opposing short edges",
                    "stack": "8 um Cu | 61.5 um graphite | 9 um separator | 84 um LFP | 13 um Al",
                },
                "study_smoke": "0.5C, SOC=0.01, range(0,30,600) s",
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
