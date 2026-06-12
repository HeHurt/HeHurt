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

    @app.post("/api/project/switch")
    async def switch_project(request: Request) -> dict[str, Any]:
        payload = await request.json()
        try:
            return project_store.switch_project(str(payload.get("project_name", "")))
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

    @app.post("/api/jobs/{job_id}/stop")
    def stop_job(job_id: str) -> dict[str, Any]:
        try:
            status = job_manager.stop_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Job not found.") from exc
        database.upsert_job(status, job_dir(job_id))
        return status

    app.mount("/", StaticFiles(directory=str(STUDIO_ROOT), html=True), name="studio")
    return app


app = create_app()


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
    args = parser.parse_args()

    port = find_port(args.port) if args.host in {"127.0.0.1", "localhost"} else args.port
    url = f"http://{args.host}:{port}/"
    print(f"Battery Sim Studio running at {url}")
    print(f"FastAPI docs available at {url}docs")
    if not args.no_browser:
        webbrowser.open_new(url)
    uvicorn.run(app, host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()
