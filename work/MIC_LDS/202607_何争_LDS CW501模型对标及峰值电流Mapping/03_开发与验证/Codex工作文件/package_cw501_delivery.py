from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


task = Path(r"D:\Users\hez\Desktop\hithium\work\MIC_LDS\202607_何争_LDS CW501模型对标及峰值电流Mapping")
run = Path(r"D:\Users\hez\Desktop\hithium\BatteryProject\output\runs\cw501_benchmark\20260729_093615_full_v2")
workspace = Path(r"C:\Users\hez\Documents\Codex\2026-07-29\cw369-paramldscw369-py")
report = workspace / "outputs" / "CW501_DFN参数审计与模型对标报告.md"
model = task / "02_模型" / "cw501_dfn_benchmark.py"
notebook = task / "02_模型" / "CW501_DFN模型对标.ipynb"
peak_notebook = task / "02_模型" / "CW501_10s30s60s峰值电流Mapping.ipynb"
peak_model = task / "02_模型" / "cw501_peak_current_mapping.py"
params = Path(r"D:\Users\hez\Desktop\hithium\params\paramsLDSCW501.py")
published = task / "04_输出结果" / "20260729_093615_full_v2"
readme = task / "05_复现说明" / "README.md"
task_report = task / "01_仿真报告" / "CW501_DFN参数审计与模型对标报告.md"

published.mkdir(parents=True, exist_ok=True)
readme.parent.mkdir(parents=True, exist_ok=True)
task_report.parent.mkdir(parents=True, exist_ok=True)
readme.write_bytes(report.read_bytes())
task_report.write_bytes(report.read_bytes())

for source in run.iterdir():
    if source.is_file():
        (published / source.name).write_bytes(source.read_bytes())

zip_path = workspace / "outputs" / "CW501_DFN模型对标交付包.zip"
with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
    archive.writestr("01_报告/CW501_DFN参数审计与模型对标报告.md", report.read_bytes())
    archive.writestr("02_模型/cw501_dfn_benchmark.py", model.read_bytes())
    archive.writestr("02_模型/CW501_DFN模型对标.ipynb", notebook.read_bytes())
    archive.writestr("02_模型/cw501_peak_current_mapping.py", peak_model.read_bytes())
    archive.writestr("02_模型/CW501_10s30s60s峰值电流Mapping.ipynb", peak_notebook.read_bytes())
    archive.writestr("02_模型/paramsLDSCW501.py", params.read_bytes())
    for source in sorted(run.iterdir()):
        if source.is_file():
            archive.writestr(f"04_输出结果/{source.name}", source.read_bytes())
    for folder_name in ["峰值电流Mapping_smoke", "峰值电流Mapping_edge_smoke"]:
        source_dir = task / "04_输出结果" / folder_name
        if source_dir.exists():
            for source in sorted(source_dir.rglob("*")):
                if source.is_file():
                    relative = source.relative_to(task)
                    archive.writestr(str(relative).replace("\\", "/"), source.read_bytes())

(task / zip_path.name).write_bytes(zip_path.read_bytes())
print(zip_path)
