from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.jobs import JobManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOB_ROOT = PROJECT_ROOT / "output" / "public_studio_jobs"
DEFAULT_DEV_SECRET = "battery-sim-local-development-only"
PUBLIC_PARAMETER_SETS = {"chen2020", "okane2022"}
TERMINAL_STATUSES = {"completed", "failed", "canceled"}


@dataclass(frozen=True)
class PublicSettings:
    """Runtime limits for the anonymous public simulation demo."""

    secret: str
    allowed_origins: tuple[str, ...]
    job_root: Path = DEFAULT_JOB_ROOT
    max_concurrent_jobs: int = 1
    max_jobs_per_hour: int = 12
    job_timeout_s: int = 180
    token_ttl_s: int = 24 * 60 * 60

    @classmethod
    def from_env(cls) -> "PublicSettings":
        secret = os.environ.get("PUBLIC_JOB_SECRET", DEFAULT_DEV_SECRET)
        if os.environ.get("PUBLIC_ENV", "development").lower() == "production":
            if secret == DEFAULT_DEV_SECRET or len(secret) < 32:
                raise RuntimeError("PUBLIC_JOB_SECRET must be at least 32 characters in production.")
        origins = tuple(
            item.strip()
            for item in os.environ.get(
                "PUBLIC_ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if item.strip()
        )
        return cls(
            secret=secret,
            allowed_origins=origins,
            job_root=Path(os.environ.get("PUBLIC_JOB_ROOT", DEFAULT_JOB_ROOT)),
            max_concurrent_jobs=max(1, min(2, int(os.environ.get("PUBLIC_MAX_CONCURRENT_JOBS", "1")))),
            max_jobs_per_hour=max(1, int(os.environ.get("PUBLIC_MAX_JOBS_PER_HOUR", "12"))),
            job_timeout_s=max(30, int(os.environ.get("PUBLIC_JOB_TIMEOUT_S", "180"))),
            token_ttl_s=max(300, int(os.environ.get("PUBLIC_TOKEN_TTL_S", str(24 * 60 * 60)))),
        )


class PublicSimulationRequest(BaseModel):
    """Small, resource-bounded simulation contract exposed by the public UI."""

    model: Literal["spme"] = "spme"
    parameter_set: Literal["chen2020", "okane2022"] = "chen2020"
    charge_rate: float = Field(default=0.5, ge=0.1, le=1.0)
    discharge_rate: float = Field(default=0.5, ge=0.1, le=1.0)
    charge_cutoff_v: float = Field(default=4.2, ge=3.8, le=4.3)
    discharge_cutoff_v: float = Field(default=2.5, ge=2.4, le=3.2)
    temperature_c: float = Field(default=25.0, ge=0.0, le=45.0)
    cycles: int = Field(default=1, ge=1, le=3)
    initial_soc: float = Field(default=0.5, ge=0.1, le=0.9)
    rest_minutes: int = Field(default=1, ge=0, le=15)


class SlidingWindowLimiter:
    """Process-local global limiter; the public container intentionally runs one worker."""

    def __init__(self, limit: int, window_s: float = 3600.0) -> None:
        self.limit = limit
        self.window_s = window_s
        self.events: deque[float] = deque()
        self.lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self.lock:
            while self.events and now - self.events[0] >= self.window_s:
                self.events.popleft()
            if len(self.events) >= self.limit:
                return False
            self.events.append(now)
            return True


def _encode_token(job_id: str, secret: str) -> str:
    issued_at = str(int(time.time()))
    payload = base64.urlsafe_b64encode(f"{job_id}:{issued_at}".encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _decode_token(token: str, secret: str, ttl_s: int) -> tuple[str, int]:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        padded = payload + "=" * (-len(payload) % 4)
        job_id, issued_raw = base64.urlsafe_b64decode(padded.encode()).decode().rsplit(":", 1)
        issued_at = int(issued_raw)
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=403, detail="Invalid job access token.") from exc
    token_age_s = int(time.time()) - issued_at
    if token_age_s < -60:
        raise HTTPException(status_code=403, detail="Invalid job access token timestamp.")
    if token_age_s > ttl_s:
        raise HTTPException(status_code=403, detail="Job access token has expired.")
    return job_id, issued_at


def _authorize_job(request: Request, job_id: str, settings: PublicSettings) -> None:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="A job access token is required.")
    token_job_id, _issued_at = _decode_token(authorization[7:].strip(), settings.secret, settings.token_ttl_s)
    if not hmac.compare_digest(token_job_id, job_id):
        raise HTTPException(status_code=403, detail="Job access token does not match this job.")


def _public_status(status: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "job_id",
        "job_type",
        "status",
        "progress",
        "current_cycle",
        "total_cycles",
        "cycles_requested",
        "sim_time_h",
        "elapsed_s",
        "created_at",
        "updated_at",
        "error",
        "request",
        "logs",
    }
    clean = {key: value for key, value in status.items() if key in allowed}
    if isinstance(clean.get("logs"), list):
        clean["logs"] = clean["logs"][-20:]
    return clean


def _active_job_count(job_manager: JobManager) -> int:
    active = 0
    for process in list(job_manager.processes.values()):
        try:
            active += int(process.is_alive())
        except (AssertionError, ValueError):
            continue
    return active


def create_app(
    settings: PublicSettings | None = None,
    job_manager: JobManager | None = None,
) -> FastAPI:
    """Create the restricted public API without exposing local Studio data routes."""

    runtime = settings or PublicSettings.from_env()
    manager = job_manager or JobManager(job_root=runtime.job_root)
    limiter = SlidingWindowLimiter(runtime.max_jobs_per_hour)
    create_lock = threading.Lock()

    app = FastAPI(title="Battery Sim Studio Public API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(runtime.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.state.public_settings = runtime
    app.state.job_manager = manager

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "battery-sim-public",
            "models": ["spme"],
            "parameter_sets": sorted(PUBLIC_PARAMETER_SETS),
            "limits": {
                "max_cycles": 3,
                "max_concurrent_jobs": runtime.max_concurrent_jobs,
                "max_jobs_per_hour": runtime.max_jobs_per_hour,
                "job_timeout_s": runtime.job_timeout_s,
            },
        }

    @app.post("/api/jobs", status_code=201)
    def create_job(payload: PublicSimulationRequest) -> dict[str, Any]:
        with create_lock:
            if _active_job_count(manager) >= runtime.max_concurrent_jobs:
                raise HTTPException(status_code=429, detail="Simulation capacity is busy. Try again later.")
            if not limiter.allow():
                raise HTTPException(status_code=429, detail="Public simulation quota has been reached for this hour.")
            request_payload = {
                "job_type": "cycle",
                "model": payload.model,
                "parameter_set": payload.parameter_set,
                "charge_rate": payload.charge_rate,
                "discharge_rate": payload.discharge_rate,
                "rate_unit": "C",
                "nominal_voltage_v": 3.6,
                "charge_cutoff_v": payload.charge_cutoff_v,
                "discharge_cutoff_v": payload.discharge_cutoff_v,
                "temperature_c": payload.temperature_c,
                "cycles": payload.cycles,
                "run_mode": "smoke",
                "initial_soc": payload.initial_soc,
                "aging_enabled": False,
                "dcr_enabled": False,
                "rest_minutes": payload.rest_minutes,
            }
            status = manager.create_job(request_payload)
        response = _public_status(status)
        response["access_token"] = _encode_token(status["job_id"], runtime.secret)
        return response

    @app.get("/api/jobs/{job_id}")
    def get_job_status(job_id: str, request: Request) -> dict[str, Any]:
        _authorize_job(request, job_id, runtime)
        try:
            status = manager.get_status(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc
        if status.get("status") not in TERMINAL_STATUSES:
            age_s = time.time() - float(status.get("created_at") or time.time())
            if age_s > runtime.job_timeout_s:
                status = manager.stop_job(job_id)
                status["error"] = f"Public job exceeded the {runtime.job_timeout_s}s runtime limit."
        return _public_status(status)

    @app.get("/api/jobs/{job_id}/results")
    def get_job_results(job_id: str, request: Request) -> dict[str, Any]:
        _authorize_job(request, job_id, runtime)
        try:
            return manager.get_result(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Results are not available.") from exc

    @app.post("/api/jobs/{job_id}/stop")
    def stop_job(job_id: str, request: Request) -> dict[str, Any]:
        _authorize_job(request, job_id, runtime)
        try:
            return _public_status(manager.stop_job(job_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc

    return app


app = create_app()
