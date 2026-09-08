import json
from pathlib import Path


ROOT = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs")
POUCH = ROOT / "20260831_150000_single_layer_pouch_dual_tab_v1" / "postprocess_v8_coin_comparison" / "pouch_v8_full_cycle_comparison.json"
COIN = ROOT / "20260820_140000_coin_v9_nonlinear_breathing_cycle" / "full_cycle_comparison.json"
OUTPUT = POUCH.parent / "post_discharge_rebound_diagnosis.json"


def nearest_after(time_s, start, delay):
    target = time_s[start] + delay
    return min(range(start, len(time_s)), key=lambda index: abs(time_s[index] - target))


def summarize(series, family):
    time_s = series["time_s"]
    current = series["current_Crate"]
    discharge = [index for index, value in enumerate(current) if value < -0.1]
    cutoff = max(discharge)
    rest = next(index for index in range(cutoff + 1, len(current)) if abs(current[index]) < 0.1)
    rest_60 = nearest_after(time_s, rest, 60)
    rest_600 = nearest_after(time_s, rest, 600)
    final = len(time_s) - 1
    if family == "coin":
        pressure = [1000 * value for value in series["p_sep_MPa"]]
        porosity = series["epsl_sep"]
        span = [high - low for low, high in zip(series["cl_min_mol_m3"], series["cl_max_mol_m3"])]
    else:
        pressure = series["pressure_sep_kPa"]
        porosity = series["porosity_sep"]
        span = [high - low for low, high in zip(series["electrolyte_min_mol_m3"], series["electrolyte_max_mol_m3"])]

    def state(index):
        return {
            "time_s": time_s[index],
            "voltage_V": series["voltage_V"][index],
            "SOC_pct": 100 * series["actual_SOC"][index],
            "theta_neg": series["theta_neg"][index],
            "theta_pos": series["theta_pos"][index],
            "electrolyte_span_mol_m3": span[index],
            "separator_pressure_kPa": pressure[index],
            "separator_porosity": porosity[index],
        }

    return {
        "cutoff_loaded": state(cutoff),
        "first_zero_current": state(rest),
        "rest_60s": state(rest_60),
        "rest_600s": state(rest_600),
        "final": state(final),
        "instant_rebound_mV": 1000 * (series["voltage_V"][rest] - series["voltage_V"][cutoff]),
        "final_rebound_mV": 1000 * (series["voltage_V"][final] - series["voltage_V"][cutoff]),
    }


pouch = json.loads(POUCH.read_text(encoding="utf-8"))
coin = json.loads(COIN.read_text(encoding="utf-8"))
result = {
    "coin_baseline": summarize(coin["cases"]["off"]["series"], "coin"),
    "coin_coupled_100N": summarize(coin["cases"]["literature_nonlinear"]["series"], "coin"),
    "pouch_baseline": summarize(pouch["cases"]["baseline"]["series"], "pouch"),
    "pouch_coupled_100N": summarize(pouch["cases"]["coupled_100N"]["series"], "pouch"),
}
OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
