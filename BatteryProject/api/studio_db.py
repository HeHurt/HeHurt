from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "output" / "studio.sqlite3"


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stamp_from_value(value: Any) -> str:
    if value is None or value == "":
        return now_stamp()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value)).isoformat(timespec="seconds")
    text = str(value)
    try:
        return datetime.fromtimestamp(float(text)).isoformat(timespec="seconds")
    except ValueError:
        return text


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


class StudioDatabase:
    """Small SQLite metadata store for the local Studio app.

    Large payloads remain as files under output/. SQLite stores searchable
    project, dataset, and job metadata so the UI can survive server restarts.
    """

    def __init__(self, path: Path = DEFAULT_DB_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS projects (
                  project_name TEXT PRIMARY KEY,
                  cell_type TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  config_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS datasets (
                  id TEXT PRIMARY KEY,
                  project_name TEXT,
                  file_name TEXT NOT NULL,
                  saved_path TEXT NOT NULL,
                  normalized_path TEXT NOT NULL,
                  imported_at TEXT NOT NULL,
                  rows INTEGER NOT NULL,
                  metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                  job_id TEXT PRIMARY KEY,
                  project_name TEXT,
                  status TEXT NOT NULL,
                  progress REAL,
                  current_cycle INTEGER,
                  total_cycles INTEGER,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  job_dir TEXT NOT NULL,
                  request_json TEXT NOT NULL,
                  status_json TEXT NOT NULL
                );
                """
            )

    def set_setting(self, key: str, value: str) -> None:
        stamp = now_stamp()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings(key, value, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  value = excluded.value,
                  updated_at = excluded.updated_at
                """,
                (key, value, stamp),
            )

    def get_setting(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def current_project_name(self, default: str = "Demo_Project") -> str:
        return self.get_setting("current_project") or default

    def load_project(self, project_name: str | None = None) -> dict[str, Any] | None:
        name = project_name or self.get_setting("current_project")
        if not name:
            return None
        with self.connect() as connection:
            row = connection.execute("SELECT config_json FROM projects WHERE project_name = ?", (name,)).fetchone()
        return json_loads(row["config_json"], None) if row else None

    def upsert_project(self, config: dict[str, Any], make_current: bool = True) -> None:
        metadata = config.get("project_metadata") or {}
        project_name = str(metadata.get("project_name") or config.get("project_name") or "Demo_Project").strip()
        if not project_name:
            project_name = "Demo_Project"
        cell_type = str(metadata.get("cell_type") or "NCM/Graphite").strip() or "NCM/Graphite"
        created_at = str(metadata.get("created_at") or now_stamp())
        updated_at = str(config.get("saved_at") or now_stamp())

        config = {
            **config,
            "project_name": project_name,
            "project_metadata": {
                **metadata,
                "project_name": project_name,
                "cell_type": cell_type,
                "created_at": created_at,
            },
        }
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects(project_name, cell_type, created_at, updated_at, config_json)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(project_name) DO UPDATE SET
                  cell_type = excluded.cell_type,
                  created_at = excluded.created_at,
                  updated_at = excluded.updated_at,
                  config_json = excluded.config_json
                """,
                (project_name, cell_type, created_at, updated_at, json_dumps(config)),
            )
        if make_current:
            self.set_setting("current_project", project_name)

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT project_name, cell_type, created_at, updated_at
                FROM projects
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_dataset(self, metadata: dict[str, Any], project_name: str | None = None) -> None:
        dataset_id = str(metadata["id"])
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO datasets(
                  id, project_name, file_name, saved_path, normalized_path,
                  imported_at, rows, metadata_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  project_name = excluded.project_name,
                  file_name = excluded.file_name,
                  saved_path = excluded.saved_path,
                  normalized_path = excluded.normalized_path,
                  imported_at = excluded.imported_at,
                  rows = excluded.rows,
                  metadata_json = excluded.metadata_json
                """,
                (
                    dataset_id,
                    project_name or self.current_project_name(),
                    str(metadata.get("file_name") or ""),
                    str(metadata.get("saved_path") or ""),
                    str(metadata.get("normalized_path") or ""),
                    str(metadata.get("imported_at") or now_stamp()),
                    int(metadata.get("rows") or 0),
                    json_dumps(metadata),
                ),
            )

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT metadata_json FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        return json_loads(row["metadata_json"], None) if row else None

    def list_datasets(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_name, file_name, imported_at, rows
                FROM datasets
                ORDER BY imported_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_job(self, status: dict[str, Any], job_dir: Path | str, project_name: str | None = None) -> None:
        job_id = str(status["job_id"])
        request = status.get("request") or {}
        stamp = now_stamp()
        created_at = stamp_from_value(status.get("created_at") or stamp)
        updated_at = stamp_from_value(status.get("updated_at") or stamp)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                  job_id, project_name, status, progress, current_cycle, total_cycles,
                  created_at, updated_at, job_dir, request_json, status_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                  project_name = excluded.project_name,
                  status = excluded.status,
                  progress = excluded.progress,
                  current_cycle = excluded.current_cycle,
                  total_cycles = excluded.total_cycles,
                  created_at = excluded.created_at,
                  updated_at = excluded.updated_at,
                  job_dir = excluded.job_dir,
                  request_json = excluded.request_json,
                  status_json = excluded.status_json
                """,
                (
                    job_id,
                    project_name or self.current_project_name(),
                    str(status.get("status") or "unknown"),
                    float(status.get("progress") or 0),
                    int(status.get("current_cycle") or 0),
                    int(status.get("total_cycles") or 0),
                    created_at,
                    updated_at,
                    str(job_dir),
                    json_dumps(request),
                    json_dumps(status),
                ),
            )

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT job_id, project_name, status, progress, current_cycle,
                       total_cycles, created_at, updated_at, job_dir
                FROM jobs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
