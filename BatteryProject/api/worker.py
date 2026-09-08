"""独立任务 worker:轮询 Studio sqlite 队列执行任务。

设计(P0-C):
- Web API 只负责提交(写 status.json + sqlite jobs 表)与查询;本进程负责实际执行。
- 每任务一个 spawn 子进程(与 JOB_TYPES worker 同契约),worker 监控子进程并检查 cancel_requested。
- 启动时 _recover_stale:Web/worker 重启后,残留 running 任务重新排队(带 attempts 上限)或标记失败。

启动:
    python api/worker.py            # 独立常驻
run_studio.py --no-worker          # Web 单独跑(不拉起 worker)
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
for _path in (PROJECT_ROOT, WORKSPACE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from api.jobs import JOB_ROOT, JOB_TYPES, atomic_write_json, log_status, read_json, update_status  # noqa: E402
from api.studio_db import StudioDatabase  # noqa: E402

POLL_SECONDS = 2.0
MAX_ATTEMPTS = 3
CANCEL_CHECK_SECONDS = 1.0


def _status_path(job_dir: Path) -> Path:
    return job_dir / "status.json"


def _cancel_requested(job_dir: Path) -> bool:
    status = read_json(_status_path(job_dir), {}) or {}
    return bool(status.get("cancel_requested"))


def _now_stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _sync_db(db: StudioDatabase, job_dir: Path) -> None:
    status = read_json(_status_path(job_dir), {}) or {}
    if status:
        db.upsert_job(status, job_dir)


def _claim_next(db: StudioDatabase) -> dict[str, Any] | None:
    """取一个 queued 任务(先到先得),CAS 式防多 worker 抢占。"""
    with db.connect() as connection:
        row = connection.execute(
            "SELECT job_id, job_dir, request_json FROM jobs WHERE status='queued' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        claimed = connection.execute(
            "UPDATE jobs SET status='running', updated_at=? WHERE job_id=? AND status='queued'",
            (_now_stamp(), row["job_id"]),
        ).rowcount
        if claimed != 1:
            return None  # 已被其他 worker 认领
    return dict(row)


def _recover_stale(db: StudioDatabase) -> None:
    """Web/worker 重启后恢复:status.json 与 sqlite 不一致的以 status.json 为准;
    running 且无人认领的 -> 重新排队(attempts 超限则标记失败)。"""
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT job_id, job_dir, status_json FROM jobs WHERE status IN ('running', 'queued')"
        ).fetchall()
    for row in rows:
        job_dir = Path(row["job_dir"])
        if not job_dir.is_absolute():
            job_dir = PROJECT_ROOT / job_dir
        try:
            status = read_json(_status_path(job_dir), {}) or {}
        except Exception:  # noqa: BLE001
            continue
        current = status.get("status")
        if current in {"completed", "failed", "canceled"}:
            _sync_db(db, job_dir)
            continue
        if current == "running":
            attempts = int(status.get("attempts", 0)) + 1
            if attempts >= MAX_ATTEMPTS:
                log_status(
                    job_dir,
                    "ERROR",
                    f"任务恢复失败(第 {attempts} 次),标记为失败",
                    status="failed",
                    progress=100,
                )
            else:
                log_status(
                    job_dir,
                    "WARN",
                    f"检测到未完成运行(Web/worker 曾重启),重新排队 尝试 {attempts}/{MAX_ATTEMPTS}",
                )
                update_status(job_dir, status="queued", attempts=attempts, worker_pid=None, error=None)
            _sync_db(db, job_dir)
        elif current == "queued":
            _sync_db(db, job_dir)


def _run_task(job_dir_str: str, job_type: str, request: dict[str, Any]) -> None:
    """子进程入口:委托给 JOB_TYPES[job_type]['worker'],与现有 worker 同契约。"""
    spec = JOB_TYPES.get(job_type)
    if spec is None:
        raise KeyError(f"unknown job_type: {job_type}")
    spec["worker"](job_dir_str, request)


def _execute_job(db: StudioDatabase, job: dict[str, Any]) -> None:
    job_id = str(job["job_id"])
    job_dir = Path(job["job_dir"])
    if not job_dir.is_absolute():
        job_dir = PROJECT_ROOT / job_dir  # 兼容历史相对路径记录
    try:
        request = json.loads(job["request_json"])
    except (json.JSONDecodeError, TypeError):
        request = {}
    job_type = str(request.get("job_type", ""))

    update_status(
        job_dir,
        status="running",
        worker_pid=os.getpid(),
        attempts=int((read_json(_status_path(job_dir), {}) or {}).get("attempts", 0)),
    )
    _sync_db(db, job_dir)

    context = mp.get_context("spawn")
    proc = context.Process(target=_run_task, args=(str(job_dir), job_type, request), daemon=True)
    proc.start()
    try:
        while proc.is_alive():
            if _cancel_requested(job_dir):
                proc.terminate()
                proc.join(timeout=5)
                log_status(job_dir, "WARN", "任务已被用户停止", status="canceled", progress=100)
                break
            time.sleep(CANCEL_CHECK_SECONDS)
    finally:
        if proc.is_alive():
            proc.terminate()
    _sync_db(db, job_dir)


def worker_loop() -> None:
    db = StudioDatabase()
    print(f"[worker] 启动 队列={db.path}", flush=True)
    _recover_stale(db)
    while True:
        job = _claim_next(db)
        if job is None:
            time.sleep(POLL_SECONDS)
            continue
        try:
            _execute_job(db, job)
        except Exception as exc:  # noqa: BLE001
            job_dir = Path(job["job_dir"])
            log_status(job_dir, "ERROR", f"worker 执行异常: {exc}", status="failed", progress=100)
            _sync_db(db, job_dir)


def main() -> None:
    worker_loop()


if __name__ == "__main__":
    main()
