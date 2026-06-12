from __future__ import annotations

import base64
import csv
import json
import re
import uuid
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .studio_db import StudioDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "output"
PROJECT_STORE_ROOT = OUTPUT_ROOT / "studio_projects"
DATA_STORE_ROOT = OUTPUT_ROOT / "studio_data"
UPLOAD_ROOT = DATA_STORE_ROOT / "uploads"
DATASET_ROOT = DATA_STORE_ROOT / "datasets"

DATA_COLUMNS = [
    ("cycle", "循环序号"),
    ("capacity_ah", "容量 (Ah)"),
    ("charge_energy_wh", "充电能量 (Wh)"),
    ("discharge_energy_wh", "放电能量 (Wh)"),
    ("efficiency_pct", "库仑效率 (%)"),
]


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def safe_filename(name: str) -> str:
    cleaned = Path(name or "dataset").name.strip()
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", cleaned)
    return cleaned or "dataset"


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def compact_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def pybamm_version() -> str:
    try:
        return version("pybamm")
    except PackageNotFoundError:
        return "未安装"


def display_value(value: Any) -> str:
    if value is None or value == "":
        return "--"
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:.0f}"
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def numeric_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalize_column_name(name: Any) -> str:
    return re.sub(r"[\s_\-\[\]\(\)（）./%]+", "", str(name).lower())


def column_has(name: str, *keywords: str) -> bool:
    normalized = normalize_column_name(name)
    return all(keyword.lower() in normalized for keyword in keywords)


def pick_column(columns: list[str], rules: list[tuple[str, ...]]) -> str | None:
    for rule in rules:
        for column in columns:
            if column_has(column, *rule):
                return column
    return None


def read_table(path: Path) -> Any:
    import pandas as pd

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return pd.read_csv(path)


def first_numeric_column(df: Any, excluded: set[str]) -> str | None:
    for column in df.columns:
        if column in excluded:
            continue
        values = [numeric_or_none(value) for value in df[column].head(20).tolist()]
        if sum(value is not None for value in values) >= max(2, min(5, len(values) // 2)):
            return column
    return None


def normalize_dataframe(df: Any) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    df = df.dropna(how="all").copy()
    df.columns = [str(column).strip() for column in df.columns]
    columns = list(df.columns)

    mapped = {
        "cycle": pick_column(columns, [("cycle",), ("循环",), ("序号",)]),
        "capacity_ah": pick_column(columns, [("capacity", "ah"), ("discharge", "capacity"), ("放电", "容量"), ("容量",)]),
        "charge_energy_wh": pick_column(columns, [("charge", "energy"), ("充电", "能量")]),
        "discharge_energy_wh": pick_column(columns, [("discharge", "energy"), ("放电", "能量")]),
        "efficiency_pct": pick_column(columns, [("efficiency",), ("库仑", "效率"), ("能量", "效率"), ("效率",)]),
        "resistance_mohm": pick_column(columns, [("dcr",), ("内阻",), ("resistance",)]),
    }
    if mapped["capacity_ah"] is None:
        mapped["capacity_ah"] = first_numeric_column(df, {value for value in mapped.values() if value})

    records: list[dict[str, Any]] = []
    for index, row in df.iterrows():
        cycle = numeric_or_none(row[mapped["cycle"]]) if mapped["cycle"] else None
        charge_energy = numeric_or_none(row[mapped["charge_energy_wh"]]) if mapped["charge_energy_wh"] else None
        discharge_energy = numeric_or_none(row[mapped["discharge_energy_wh"]]) if mapped["discharge_energy_wh"] else None
        efficiency = numeric_or_none(row[mapped["efficiency_pct"]]) if mapped["efficiency_pct"] else None
        if efficiency is None and charge_energy and discharge_energy:
            efficiency = discharge_energy / charge_energy * 100.0

        record = {
            "cycle": int(round(cycle)) if cycle is not None else int(index) + 1,
            "capacity_ah": numeric_or_none(row[mapped["capacity_ah"]]) if mapped["capacity_ah"] else None,
            "charge_energy_wh": charge_energy,
            "discharge_energy_wh": discharge_energy,
            "efficiency_pct": efficiency,
            "resistance_mohm": numeric_or_none(row[mapped["resistance_mohm"]]) if mapped["resistance_mohm"] else None,
        }
        if any(record.get(key) is not None for key in ("capacity_ah", "charge_energy_wh", "discharge_energy_wh", "efficiency_pct")):
            records.append(record)
    return records, mapped


def preview_rows(records: list[dict[str, Any]]) -> list[list[str]]:
    if len(records) <= 7:
        selected: list[dict[str, Any] | None] = list(records)
    else:
        selected = [*records[:3], None, *records[-3:]]
    rows = []
    for record in selected:
        if record is None:
            rows.append(["...", "...", "...", "...", "..."])
            continue
        rows.append([display_value(record.get(key)) for key, _label in DATA_COLUMNS])
    return rows


def nearest_record(records: list[dict[str, Any]], target_cycle: float) -> dict[str, Any] | None:
    finite = [record for record in records if numeric_or_none(record.get("cycle")) is not None]
    if not finite:
        return None
    return min(finite, key=lambda record: abs(float(record["cycle"]) - target_cycle))


def build_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    capacity_records = [
        (float(record["cycle"]), float(record["capacity_ah"]))
        for record in records
        if numeric_or_none(record.get("capacity_ah")) is not None
    ]
    initial_capacity = capacity_records[0][1] if capacity_records else None
    nominal_capacity = max((value for _cycle, value in capacity_records), default=None)
    cycle_to_80 = None
    if initial_capacity:
        threshold = initial_capacity * 0.8
        for cycle, value in capacity_records:
            if value <= threshold:
                cycle_to_80 = int(round(cycle))
                break

    efficiencies = [
        float(record["efficiency_pct"])
        for record in records
        if numeric_or_none(record.get("efficiency_pct")) is not None
    ]

    resistance_growth = None
    resistance_records = [record for record in records if numeric_or_none(record.get("resistance_mohm")) is not None]
    if resistance_records:
        first = numeric_or_none(resistance_records[0].get("resistance_mohm"))
        target = nearest_record(resistance_records, 500)
        target_value = numeric_or_none(target.get("resistance_mohm")) if target else None
        if first and target_value is not None:
            resistance_growth = (target_value / first - 1.0) * 100.0

    return {
        "initial_capacity_ah": initial_capacity,
        "nominal_capacity_ah": nominal_capacity,
        "cycle_to_80": cycle_to_80,
        "resistance_growth_500_pct": resistance_growth,
        "mean_efficiency_pct": (sum(efficiencies) / len(efficiencies)) if efficiencies else None,
        "row_count": len(records),
    }


class StudioDataManager:
    def __init__(
        self,
        upload_root: Path = UPLOAD_ROOT,
        dataset_root: Path = DATASET_ROOT,
        db: StudioDatabase | None = None,
    ) -> None:
        self.upload_root = upload_root
        self.dataset_root = dataset_root
        self.db = db
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.dataset_root.mkdir(parents=True, exist_ok=True)

    def import_upload(self, payload: dict[str, Any]) -> dict[str, Any]:
        file_name = safe_filename(str(payload.get("file_name", "")))
        encoded = str(payload.get("content_base64", ""))
        if not file_name or not encoded:
            raise ValueError("Missing file_name or content_base64.")
        suffix = Path(file_name).suffix.lower()
        if suffix not in {".csv", ".txt", ".xlsx", ".xls"}:
            raise ValueError("Only CSV/TXT/XLSX/XLS files are supported.")

        raw = base64.b64decode(encoded)
        if len(raw) > 80 * 1024 * 1024:
            raise ValueError("Uploaded file is larger than 80 MB.")

        dataset_id = uuid.uuid4().hex[:12]
        upload_path = self.upload_root / f"{compact_stamp()}_{dataset_id}_{file_name}"
        upload_path.write_bytes(raw)

        df = read_table(upload_path)
        records, mapped_columns = normalize_dataframe(df)
        if not records:
            raise ValueError("No usable numeric cycle data was found in the uploaded file.")

        dataset_dir = self.dataset_root / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        normalized_path = dataset_dir / "normalized.csv"
        self.write_records_csv(normalized_path, records)

        metadata = {
            "id": dataset_id,
            "file_name": file_name,
            "saved_path": str(upload_path),
            "normalized_path": str(normalized_path),
            "imported_at": now_stamp(),
            "rows": len(records),
            "source_columns": list(map(str, df.columns)),
            "mapped_columns": mapped_columns,
        }
        atomic_write_json(dataset_dir / "metadata.json", metadata)
        if self.db:
            self.db.upsert_dataset(metadata)
        return {
            "ok": True,
            "dataset": metadata,
            "preview": {
                "columns": [label for _key, label in DATA_COLUMNS],
                "rows": preview_rows(records),
            },
            "metrics": build_metrics(records),
        }

    def write_records_csv(self, path: Path, records: list[dict[str, Any]]) -> None:
        fieldnames = ["cycle", "capacity_ah", "charge_energy_wh", "discharge_energy_wh", "efficiency_pct", "resistance_mohm"]
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for record in records:
                writer.writerow({field: "" if record.get(field) is None else record.get(field) for field in fieldnames})

    def export_csv(self, dataset_id: str) -> str:
        dataset_dir = self.dataset_root / dataset_id
        csv_path = dataset_dir / "normalized.csv"
        if not csv_path.exists():
            raise KeyError(dataset_id)
        return csv_path.read_text(encoding="utf-8-sig")

    def load_records(self, dataset_id: str) -> list[dict[str, Any]]:
        csv_path = self.dataset_root / dataset_id / "normalized.csv"
        if not csv_path.exists():
            raise KeyError(dataset_id)
        records: list[dict[str, Any]] = []
        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                records.append({key: numeric_or_none(value) for key, value in row.items()})
        return records

    def dataset_detail(self, dataset_id: str) -> dict[str, Any]:
        metadata = read_json(self.dataset_root / dataset_id / "metadata.json", None)
        if metadata is None and self.db:
            metadata = self.db.get_dataset(dataset_id)
        if metadata is None:
            raise KeyError(dataset_id)
        records = self.load_records(dataset_id)
        return {
            "ok": True,
            "dataset": metadata,
            "preview": {
                "columns": [label for _key, label in DATA_COLUMNS],
                "rows": preview_rows(records),
            },
            "metrics": build_metrics(records),
        }


class StudioProjectStore:
    def __init__(
        self,
        root: Path = PROJECT_STORE_ROOT,
        project_name: str = "Demo_Project",
        db: StudioDatabase | None = None,
    ) -> None:
        self.root = root
        self.project_name = project_name
        self.db = db
        self.project_dir = self.root / safe_filename(project_name)
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def current_project_dir(self) -> Path:
        name = self.db.current_project_name(self.project_name) if self.db else self.project_name
        directory = self.root / safe_filename(name)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @property
    def config_path(self) -> Path:
        return self.current_project_dir() / "config.json"

    def runtime_info(self) -> dict[str, Any]:
        return {"pybamm_version": pybamm_version()}

    def default_config(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_metadata": {
                "project_name": self.project_name,
                "cell_type": "NCM/Graphite",
                "created_at": now_stamp(),
            },
            "saved_at": None,
            "simulation_request": {},
            "current_job_id": None,
            "dataset": None,
            "ui": {},
        }

    def normalize_config(self, config: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        changed = False
        if config is None:
            return self.default_config(), True

        metadata = config.get("project_metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            changed = True
        if not metadata.get("project_name"):
            metadata["project_name"] = str(config.get("project_name") or self.project_name)
            changed = True
        if not metadata.get("cell_type"):
            metadata["cell_type"] = "NCM/Graphite"
            changed = True
        if not metadata.get("created_at"):
            metadata["created_at"] = now_stamp()
            changed = True
        if config.get("project_name") != metadata["project_name"]:
            config["project_name"] = metadata["project_name"]
            changed = True
        config["project_metadata"] = metadata
        if changed:
            atomic_write_json(self.config_path, config)
        return config, changed

    def ensure_config(self) -> dict[str, Any]:
        db_config = self.db.load_project() if self.db else None
        if db_config:
            config, changed = self.normalize_config(db_config)
            if changed and self.db:
                self.db.upsert_project(config)
            return config

        config = read_json(self.config_path, None)
        if config is None:
            config = self.default_config()
            atomic_write_json(self.config_path, config)
            if self.db:
                self.db.upsert_project(config)
            return config

        config, changed = self.normalize_config(config)
        if changed:
            atomic_write_json(self.config_path, config)
        if self.db:
            self.db.upsert_project(config)
        return config

    def save_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.ensure_config()
        existing_metadata = existing.get("project_metadata") or {}
        incoming_metadata = payload.get("project_metadata") or {}
        project_name = str(
            incoming_metadata.get("project_name")
            or payload.get("project_name")
            or existing_metadata.get("project_name")
            or self.project_name
        ).strip() or self.project_name
        cell_type = str(
            incoming_metadata.get("cell_type")
            or existing_metadata.get("cell_type")
            or "NCM/Graphite"
        ).strip() or "NCM/Graphite"
        created_at = existing_metadata.get("created_at") or incoming_metadata.get("created_at") or now_stamp()
        config = {
            "project_name": project_name,
            "project_metadata": {
                "project_name": project_name,
                "cell_type": cell_type,
                "created_at": created_at,
            },
            "saved_at": now_stamp(),
            "simulation_request": payload.get("simulation_request") or {},
            "current_job_id": payload.get("current_job_id"),
            "dataset": payload.get("dataset"),
            "ui": payload.get("ui") or {},
        }
        atomic_write_json(self.config_path, config)
        versioned = self.config_path.parent / f"config_{compact_stamp()}.json"
        atomic_write_json(versioned, config)
        if self.db:
            self.db.upsert_project(config)
        return {
            "ok": True,
            "config": config,
            "runtime": self.runtime_info(),
            "path": str(self.config_path),
            "version_path": str(versioned),
            "db_path": str(self.db.path) if self.db else None,
        }

    def switch_project(self, name: str) -> dict[str, Any]:
        project_name = str(name or "").strip()
        if not project_name:
            raise ValueError("Project name is required.")
        config = self.db.load_project(project_name) if self.db else None
        if config is None:
            config = {
                "project_name": project_name,
                "project_metadata": {
                    "project_name": project_name,
                    "cell_type": "NCM/Graphite",
                    "created_at": now_stamp(),
                },
                "saved_at": None,
                "simulation_request": {},
                "current_job_id": None,
                "dataset": None,
                "ui": {},
            }
        if self.db:
            self.db.upsert_project(config, make_current=True)
        atomic_write_json(self.config_path, config)
        return {
            "ok": True,
            "config": config,
            "runtime": self.runtime_info(),
            "path": str(self.config_path),
        }

    def load_config(self) -> dict[str, Any]:
        config = self.ensure_config()
        return {
            "ok": True,
            "config": config,
            "runtime": self.runtime_info(),
            "path": str(self.config_path),
            "db_path": str(self.db.path) if self.db else None,
        }
