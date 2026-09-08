from pathlib import Path
import sys


source_dir = Path(sys.argv[1])
target_dir = Path(sys.argv[2])
target_dir.mkdir(parents=True, exist_ok=True)
for source_path in source_dir.glob("*_完整时序.csv"):
    target_path = target_dir / f"{source_path.stem}.json"
    target_path.write_text(source_path.read_text(encoding="utf-8-sig"), encoding="utf-8")
