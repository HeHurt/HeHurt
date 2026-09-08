import importlib.util
import time
from pathlib import Path

MODULE_PATH = Path(
    r"D:\Users\hez\Desktop\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW501模型对标及峰值电流Mapping"
    r"\02_模型\cw501_peak_current_mapping.py"
)
spec = importlib.util.spec_from_file_location("peak_v2", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

model = module.build_peak_model()
parameters = module.fresh_parameter_values(25)
nominal = float(parameters["Nominal cell capacity [A.h]"])

started = time.perf_counter()
for direction in ("charge", "discharge"):
    result = module.run_peak_current_reusable(
        model=model,
        parameters=parameters,
        nominal_capacity_ah=nominal,
        duration_s=10,
        direction=direction,
        soc_values=(0.5,),
        output_period_s=2.0,
        ratio_xtol=1e-3,
    )
    print(direction, result)
print("elapsed_s", time.perf_counter() - started)
