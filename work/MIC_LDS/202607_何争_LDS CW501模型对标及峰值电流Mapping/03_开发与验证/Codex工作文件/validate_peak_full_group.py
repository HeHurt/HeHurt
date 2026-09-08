import importlib.util
import time
from pathlib import Path

MODULE_PATH = Path(
    r"D:\Users\hez\Desktop\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW501模型对标及峰值电流Mapping"
    r"\02_模型\cw501_peak_current_mapping.py"
)
OUTPUT_DIR = Path(
    r"C:\Users\hez\Documents\Codex\2026-07-29"
    r"\cw369-paramldscw369-py\work\peak_full_group"
)
spec = importlib.util.spec_from_file_location("peak_mapping_target", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

started = time.perf_counter()
frame = module.run_peak_current_mapping(
    output_dir=OUTPUT_DIR,
    durations_s=(10,),
    charge_temperatures_c=(0,),
    discharge_temperatures_c=(),
    charge_soc=module.DEFAULT_CHARGE_SOC,
    discharge_soc=(),
    output_period_s=2.0,
    ratio_xtol=1e-3,
    resume=False,
)
print("rows", len(frame))
print("ok", int((frame["status"] == "ok").sum()))
print("elapsed_s", time.perf_counter() - started)
print(frame[["soc", "peak_current_a", "status"]].to_string(index=False))
