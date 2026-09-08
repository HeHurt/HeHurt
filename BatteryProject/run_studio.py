from __future__ import annotations

import argparse
import contextlib
import socket
import webbrowser
from http import HTTPStatus
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from api.compare import compare_job_to_dataset
from api.jobs import JobManager
from api.studio_db import StudioDatabase
from api.studio_io import StudioDataManager, StudioProjectStore


PROJECT_ROOT = Path(__file__).resolve().parent
STUDIO_ROOT = PROJECT_ROOT / "studio"


def create_app() -> FastAPI:
    if not STUDIO_ROOT.exists():
        raise FileNotFoundError(f"Studio directory does not exist: {STUDIO_ROOT}")

    database = StudioDatabase()
    job_manager = JobManager()
    data_manager = StudioDataManager(db=database)
    project_store = StudioProjectStore(db=database)

    app = FastAPI(title="Battery Sim Studio API", version="0.1.0")
    app.state.database = database
    app.state.job_manager = job_manager
    app.state.data_manager = data_manager
    app.state.project_store = project_store

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=HTTPStatus.BAD_REQUEST)

    def csv_download(csv_text: str, filename: str) -> Response:
        return Response(
            content=csv_text.encode("utf-8-sig"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def job_dir(job_id: str) -> Path:
        return job_manager.job_root / job_id

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "backend": "fastapi",
            "db_path": str(database.path),
        }

    @app.get("/api/projects")
    def list_projects() -> dict[str, Any]:
        return {"ok": True, "projects": database.list_projects()}

    @app.get("/api/jobs")
    def list_jobs() -> dict[str, Any]:
        jobs = database.list_jobs()
        # The SQLite rows are snapshots; refresh non-terminal jobs from their
        # status.json so the history list reflects reality without per-job polling.
        for job in jobs:
            if job.get("status") not in {"running", "queued"}:
                continue
            try:
                status = job_manager.get_status(job["job_id"])
            except KeyError:
                continue
            database.upsert_job(status, job_dir(job["job_id"]))
            job.update(
                status=status.get("status"),
                progress=status.get("progress"),
                current_cycle=status.get("current_cycle"),
                total_cycles=status.get("total_cycles"),
            )
        return {"ok": True, "jobs": jobs}

    @app.get("/api/project/config")
    def load_project_config() -> dict[str, Any]:
        return project_store.load_config()

    @app.post("/api/project/config", status_code=HTTPStatus.CREATED)
    async def save_project_config(request: Request) -> dict[str, Any]:
        payload = await request.json()
        return project_store.save_config(payload)

    @app.post("/api/data/import", status_code=HTTPStatus.CREATED)
    async def import_data(request: Request) -> dict[str, Any]:
        payload = await request.json()
        try:
            return data_manager.import_upload(payload)
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/data")
    def list_datasets() -> dict[str, Any]:
        return {"ok": True, "datasets": database.list_datasets()}

    @app.get("/api/data/{dataset_id}")
    def get_dataset_detail(dataset_id: str) -> dict[str, Any]:
        try:
            return data_manager.dataset_detail(dataset_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Dataset not found.") from exc
    @app.get("/api/bench/jobs")
    def bench_jobs() -> dict[str, Any]:
        """已完成任务列表(对标工作台仿真侧下拉)。"""
        jobs = database.list_jobs(limit=50)
        finished = [
            {
                "job_id": job["job_id"],
                "job_type": _job_type_from_dir(job.get("job_dir") or ""),
                "status": job.get("status"),
                "updated_at": job.get("updated_at"),
                "name": job.get("name"),
            }
            for job in jobs
            if job.get("status") == "completed"
        ]
        return {"ok": True, "jobs": finished}

    @app.get("/api/bench/sim-exp")
    def bench_sim_exp(job_id: str, dataset_id: str, threshold: float = 5.0) -> dict[str, Any]:
        """Sim-Exp 对标:仿真 job vs 实验数据集(对齐/RRMSE/异常区间/参数版本)。"""
        from api.compare import bench_sim_exp as _bench_sim_exp

        try:
            result = job_manager.get_result(job_id)
            records = data_manager.load_records(dataset_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc
        return _bench_sim_exp(job_id, dataset_id, result, records, threshold)

    @app.get("/api/bench/runs-curve")
    def bench_runs_curve(job_a: str, job_b: str) -> dict[str, Any]:
        """两个 Run 曲线对比(同名曲线对齐 + RRMSE + 元信息)。"""
        from api.compare import bench_runs_curve as _bench_runs_curve

        try:
            result_a = job_manager.get_result(job_a)
            result_b = job_manager.get_result(job_b)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc
        return _bench_runs_curve(result_a, result_b)

    @app.get("/api/bench/runs")
    def bench_runs(job_a: str, job_b: str) -> dict[str, Any]:
        """两个 run 的参数版本对比(manifest 字段 diff)。"""
        from api.compare import bench_runs_manifest

        try:
            result_a = job_manager.get_result(job_a)
            result_b = job_manager.get_result(job_b)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc
        return bench_runs_manifest(result_a, result_b)

    def _job_type_from_dir(job_dir: str) -> str:
        try:
            import json as _json
            from pathlib import Path as _Path

            status = _json.loads(_Path(job_dir).joinpath("status.json").read_text(encoding="utf-8"))
            return str(status.get("job_type", "cycle"))
        except Exception:  # noqa: BLE001
            return "cycle"

    @app.get("/api/job-types")
    def list_job_types() -> dict[str, Any]:
        """返回任务类型注册表(含表单 schema),供前端任务中心动态生成表单。"""
        from api.jobs import JOB_TYPES, PLANNED_JOB_TYPES

        available = [
            {
                "job_type": key,
                "label": spec.get("label", key),
                "schema": spec.get("schema", []),
                "available": True,
            }
            for key, spec in JOB_TYPES.items()
        ]
        planned = [
            {"job_type": key, "label": label, "schema": [], "available": False}
            for key, label in PLANNED_JOB_TYPES
        ]
        return {"ok": True, "job_types": available + planned}

    @app.get("/api/registry/facets")
    def registry_facets() -> dict[str, Any]:
        """返回实验数据 registry 的可筛选维度取值(电芯/温度/倍率/测试类型/质量状态)。"""
        from src.data_registry import REGISTRY_FILENAME, HITHIUM_ROOT, load_registry

        registry = load_registry(HITHIUM_ROOT / REGISTRY_FILENAME)
        entries = registry.get("entries", [])

        def uniq(key: str) -> list[str]:
            values: set[str] = set()
            for entry in entries:
                value = entry.get(key)
                if value in (None, ""):
                    continue
                values.add(str(value))
            return sorted(values, key=lambda item: (item is None, str(item)))

        return {
            "ok": True,
            "facets": {
                "cell": uniq("cell"),
                "temperature_C": uniq("temperature_C"),
                "rate": uniq("rate"),
                "test_type": uniq("test_type"),
                "kind": uniq("kind"),
                "status": uniq("status"),
            },
            "total": len(entries),
        }

    @app.get("/api/registry")
    def list_registry(
        cell: str | None = None,
        temp: float | None = None,
        rate: str | None = None,
        test: str | None = None,
        kind: str | None = None,
        fmt: str | None = None,
        status: str | None = None,
        soh: str | None = None,
        path_contains: str | None = None,
    ) -> dict[str, Any]:
        """按电芯/温度/倍率/测试类型/SOH/质量状态筛选实验数据(复用 src.data_registry)。"""
        from src.data_registry import REGISTRY_FILENAME, HITHIUM_ROOT, filter_entries, load_registry

        entries = load_registry(HITHIUM_ROOT / REGISTRY_FILENAME).get("entries", [])
        hits = filter_entries(
            entries,
            cell=cell,
            rate=rate,
            test=test,
            kind=kind,
            fmt=fmt,
            status=status,
            path_contains=path_contains,
        )
        if temp is not None:
            target = float(temp)
            hits = [e for e in hits if _temperature_matches(e, target)]
        if soh:
            hits = [e for e in hits if str(e.get("soh_pct") or "") == soh]
        if status is None:
            hits = [e for e in hits if e.get("status") not in {"ignore", "missing"}]
        kept = ["path", "kind", "format", "cell", "temperature_C", "rate",
                "test_type", "soh_pct", "sample_id", "status", "id"]
        rows = [{key: e.get(key) for key in kept if key in e} for e in hits]
        return {"ok": True, "count": len(rows), "entries": rows, "total": len(entries)}

    def _temperature_matches(entry: dict[str, Any], target: float) -> bool:
        try:
            return float(entry.get("temperature_C")) == target
        except (TypeError, ValueError):
            return False


    @app.post("/api/project/switch")
    async def switch_project(request: Request) -> dict[str, Any]:
        payload = await request.json()
        try:
            return project_store.switch_project(str(payload.get("project_name", "")))
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/data/{dataset_id}/extrapolate")
    def extrapolate_dataset(dataset_id: str, target_soh: float = 65.0) -> dict[str, Any]:
        try:
            return data_manager.extrapolate(dataset_id, target_soh)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Dataset not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/jobs/{job_id}/compare")
    def compare_job(job_id: str, dataset_id: str) -> dict[str, Any]:
        try:
            result = job_manager.get_result(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found.") from exc
        try:
            records = data_manager.load_records(dataset_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Dataset not found.") from exc
        try:
            return compare_job_to_dataset(result, records)
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/data/{dataset_id}/export.csv")
    def export_dataset_csv(dataset_id: str) -> Response:
        try:
            return csv_download(data_manager.export_csv(dataset_id), f"studio_dataset_{dataset_id}.csv")
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Dataset not found.") from exc

    @app.post("/api/jobs", status_code=HTTPStatus.CREATED)
    async def create_job(request: Request) -> dict[str, Any]:
        payload = await request.json()
        try:
            status = job_manager.create_job(payload)
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)) from exc
        database.upsert_job(status, job_dir(status["job_id"]))
        return status

    @app.get("/api/jobs/{job_id}")
    def get_job_status(job_id: str) -> dict[str, Any]:
        try:
            status = job_manager.get_status(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found.") from exc
        database.upsert_job(status, job_dir(job_id))
        return status

    @app.get("/api/jobs/{job_id}/results")
    def get_job_results(job_id: str) -> dict[str, Any]:
        try:
            return job_manager.get_result(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found.") from exc

    @app.get("/api/jobs/{job_id}/export.csv")
    def export_job_csv(job_id: str) -> Response:
        try:
            return csv_download(job_manager.export_csv(job_id), f"studio_job_{job_id}.csv")
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found.") from exc

    @app.post("/api/jobs/{job_id}/rename")
    async def rename_job(job_id: str, request: Request) -> dict[str, Any]:
        """重命名任务(可选,≤80 字符)。"""
        payload = await request.json()
        name = str(payload.get("name", "") or "").strip()[:80]
        database.rename_job(job_id, name or None)
        return {"ok": True, "job_id": job_id, "name": name or None}

    @app.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str) -> dict[str, Any]:
        """删除已完成/失败/已停止的任务(running/queued 拒绝)。"""
        try:
            return job_manager.delete_job(job_id)
        except ValueError as exc:
            raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc

    @app.post("/api/jobs/{job_id}/stop")
    def stop_job(job_id: str) -> dict[str, Any]:
        """请求停止任务(worker 将在下一个检查点终止执行)。"""
        try:
            status = job_manager.stop_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found.") from exc
        database.upsert_job(status, job_dir(job_id))
        return status

    app.mount("/", StaticFiles(directory=str(STUDIO_ROOT), html=True), name="studio")
    return app


app = create_app()


def _start_worker() -> None:
    """以独立子进程拉起 api/worker.py(Web 只提交与查询,worker 负责执行)。"""
    import subprocess
    import sys as _sys

    worker_py = Path(__file__).resolve().parent / "api" / "worker.py"
    try:
        subprocess.Popen(
            [_sys.executable, str(worker_py)],
            cwd=str(PROJECT_ROOT),
            stdout=None,
            stderr=None,
            start_new_session=True,
        )
        print("Battery Sim Studio worker started (api/worker.py)")
    except OSError as exc:
        print(f"WARN: worker 启动失败({exc});任务将停留在 queued,请手动运行 python api/worker.py")


def find_port(preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available port found from {preferred} to {preferred + 49}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the Battery Sim Studio FastAPI server.")
    parser.add_argument("--port", type=int, default=8601, help="Preferred local server port.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically.")
    parser.add_argument("--no-worker", action="store_true", help="Do not spawn the independent task worker.")
    args = parser.parse_args()

    if not args.no_worker:
        _start_worker()

    port = find_port(args.port) if args.host in {"127.0.0.1", "localhost"} else args.port
    url = f"http://{args.host}:{port}/"
    print(f"Battery Sim Studio running at {url}")
    print(f"FastAPI docs available at {url}docs")
    if not args.no_browser:
        webbrowser.open_new(url)
    uvicorn.run(app, host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()
