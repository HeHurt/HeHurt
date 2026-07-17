from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.public_app import PublicSettings, create_app


class FakeProcess:
    def __init__(self, alive: bool = False) -> None:
        self.alive = alive

    def is_alive(self) -> bool:
        return self.alive


class FakeJobManager:
    def __init__(self) -> None:
        self.processes = {}
        self.statuses = {}
        self.last_request = None

    def create_job(self, request):
        self.last_request = request
        job_id = f"job{len(self.statuses) + 1}"
        status = {
            "job_id": job_id,
            "job_type": "cycle",
            "status": "running",
            "progress": 10,
            "current_cycle": 0,
            "total_cycles": request["cycles"],
            "cycles_requested": request["cycles"],
            "created_at": 1000.0,
            "updated_at": 1000.0,
            "worker_pid": 1234,
            "traceback": "must not leak",
            "request": request,
            "logs": [],
        }
        self.statuses[job_id] = status
        self.processes[job_id] = FakeProcess(False)
        return status

    def get_status(self, job_id):
        if job_id not in self.statuses:
            raise KeyError(job_id)
        return self.statuses[job_id]

    def get_result(self, job_id):
        if job_id not in self.statuses:
            raise KeyError(job_id)
        return {"summary": {"cycle_count": 1}, "series": {"time_h": [0.0, 1.0]}}

    def stop_job(self, job_id):
        status = self.get_status(job_id)
        status["status"] = "canceled"
        return status


def settings(**changes):
    values = {
        "secret": "test-secret",
        "allowed_origins": ("https://studio.example",),
        "job_root": Path("unused"),
        "max_concurrent_jobs": 1,
        "max_jobs_per_hour": 12,
        "job_timeout_s": 180,
        "token_ttl_s": 3600,
    }
    values.update(changes)
    return PublicSettings(**values)


def create_client(manager=None, **setting_changes):
    fake = manager or FakeJobManager()
    return TestClient(create_app(settings(**setting_changes), fake)), fake


def create_job(client):
    return client.post(
        "/api/jobs",
        json={
            "model": "spme",
            "parameter_set": "chen2020",
            "charge_rate": 0.5,
            "discharge_rate": 0.5,
            "cycles": 1,
        },
    )


def test_health_reports_public_limits():
    client, _manager = create_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["models"] == ["spme"]
    assert response.json()["limits"]["max_cycles"] == 3


def test_create_job_forces_safe_backend_options_and_hides_process_details():
    client, manager = create_client()
    response = create_job(client)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert "worker_pid" not in body
    assert "traceback" not in body
    assert manager.last_request["run_mode"] == "smoke"
    assert manager.last_request["aging_enabled"] is False
    assert manager.last_request["dcr_enabled"] is False


def test_internal_parameter_set_and_dfn_are_rejected():
    client, _manager = create_client()
    internal = client.post("/api/jobs", json={"parameter_set": "hithium314"})
    dfn = client.post("/api/jobs", json={"model": "dfn"})
    assert internal.status_code == 422
    assert dfn.status_code == 422


def test_job_routes_require_matching_access_token():
    client, _manager = create_client()
    created = create_job(client).json()
    job_id = created["job_id"]
    missing = client.get(f"/api/jobs/{job_id}")
    wrong_job = client.get(
        "/api/jobs/another-job",
        headers={"Authorization": f"Bearer {created['access_token']}"},
    )
    valid = client.get(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer {created['access_token']}"},
    )
    assert missing.status_code == 401
    assert wrong_job.status_code == 403
    assert valid.status_code == 200


def test_malformed_access_token_is_rejected_without_server_error():
    client, _manager = create_client()
    created = create_job(client).json()
    response = client.get(
        f"/api/jobs/{created['job_id']}",
        headers={"Authorization": "Bearer not-valid-base64.invalid"},
    )
    assert response.status_code == 403


def test_public_api_has_no_global_job_listing():
    client, _manager = create_client()
    assert client.get("/api/jobs").status_code == 405


def test_concurrency_limit_is_enforced():
    manager = FakeJobManager()
    manager.processes["busy"] = FakeProcess(True)
    client, _manager = create_client(manager)
    response = create_job(client)
    assert response.status_code == 429
    assert "busy" in response.json()["detail"].lower()


def test_global_hourly_quota_is_enforced():
    client, _manager = create_client(max_jobs_per_hour=1)
    assert create_job(client).status_code == 201
    assert create_job(client).status_code == 429


def test_cors_allows_only_configured_site_origin():
    client, _manager = create_client()
    allowed = client.options(
        "/api/jobs",
        headers={
            "Origin": "https://studio.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    denied = client.options(
        "/api/jobs",
        headers={
            "Origin": "https://other.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "https://studio.example"
    assert "access-control-allow-origin" not in denied.headers
