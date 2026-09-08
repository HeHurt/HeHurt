import importlib.util
from pathlib import Path


TASK_ROOT = Path(
    r"D:\Users\hez\Desktop\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW501模型对标及峰值电流Mapping"
)
MODEL_PATH = TASK_ROOT / "02_模型" / "cw501_peak_current_mapping.py"
OUTPUT_DIR = TASK_ROOT / "04_输出结果" / "峰值电流Mapping"

spec = importlib.util.spec_from_file_location("cw501_peak_current_mapping", MODEL_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

module.run_peak_current_mapping(
    output_dir=OUTPUT_DIR,
    durations_s=module.DEFAULT_DURATIONS_S,
    charge_temperatures_c=module.DEFAULT_CHARGE_TEMPERATURES_C,
    discharge_temperatures_c=module.DEFAULT_DISCHARGE_TEMPERATURES_C,
    charge_soc=module.DEFAULT_CHARGE_SOC,
    discharge_soc=module.DEFAULT_DISCHARGE_SOC,
    output_period_s=2.0,
    ratio_xtol=1e-3,
    resume=True,
)
frame = module.load_peak_current_mapping(OUTPUT_DIR)
excel_path = module.export_peak_current_excel(
    frame,
    OUTPUT_DIR / "CW501_10s30s60s峰值电流Mapping.xlsx",
)
print(f"rows={len(frame)}")
print(f"excel={excel_path}")
