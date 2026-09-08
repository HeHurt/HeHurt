from pathlib import Path


template = Path(r"D:\Users\hez\Desktop\hithium\COMSOL\runs\20260810_115103_coin_v3_conductivity_fix\validate_v3.py").read_text(encoding="utf-8")
template = template.replace("coin_geometry_fixed_V3.mph", "coin_geometry_fixed_V5.mph")
template = template.replace('OUTPUT = RUN_DIR / "validation.json"', 'OUTPUT = RUN_DIR / "validation_v5.json"')
template = template.replace('"full_charge_series.csv"', '"full_charge_series_v5.csv"')
exec(compile(template, "validate_v5_generated.py", "exec"))
