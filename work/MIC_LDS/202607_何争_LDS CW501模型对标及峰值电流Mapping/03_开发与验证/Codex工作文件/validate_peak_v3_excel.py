import importlib.util
from pathlib import Path


MODULE_PATH = Path(
    r"C:\Users\hez\Documents\Codex\2026-07-29"
    r"\cw369-paramldscw369-py\work\cw501_peak_current_mapping_v2.py"
)
OUTPUT_DIR = Path(
    r"C:\Users\hez\Documents\Codex\2026-07-29"
    r"\cw369-paramldscw369-py\work\peak_v3_excel_smoke"
)
spec = importlib.util.spec_from_file_location("peak_mapping_v3", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

frame = module.run_peak_current_mapping(
    output_dir=OUTPUT_DIR,
    durations_s=(10,),
    charge_temperatures_c=(25,),
    discharge_temperatures_c=(25,),
    charge_soc=(0.5,),
    discharge_soc=(0.5,),
    output_period_s=2.0,
    ratio_xtol=1e-3,
    resume=False,
)
current = frame[frame["algorithm_version"] == module.ALGORITHM_VERSION]
print(
    current[
        [
            "direction",
            "peak_current_a",
            "pulse_first_voltage_v",
            "pulse_ocv_voltage_v",
            "pulse_power_w",
            "pulse_dcr_mohm",
        ]
    ].to_string(index=False)
)
excel_path = module.export_peak_current_excel(
    current,
    OUTPUT_DIR / "CW501_10s30s60s峰值电流Mapping.xlsx",
)
print(excel_path)
