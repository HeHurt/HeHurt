# Battery Sim Studio public backend

This image exposes only the public SPMe demo contract. It does not copy Hithium
parameter files, datasets, local Studio projects, or the unrestricted local API.

Build from the `BatteryProject` directory:

```powershell
docker build -f deploy/public_backend/Dockerfile -t battery-sim-public .
```

Required production environment variables:

- `PUBLIC_JOB_SECRET`: a long random signing secret.
- `PUBLIC_ALLOWED_ORIGINS`: comma-separated Sites origins.

Optional limits:

- `PUBLIC_MAX_CONCURRENT_JOBS` (default `1`, maximum `2`).
- `PUBLIC_MAX_JOBS_PER_HOUR` (default `12`).
- `PUBLIC_JOB_TIMEOUT_S` (default `180`).
- `PUBLIC_TOKEN_TTL_S` (default `86400`).
- `PUBLIC_JOB_ROOT` (default `/data/studio_jobs`).

Run with a persistent volume:

```powershell
docker run --rm -p 8080:8080 `
  -e PUBLIC_JOB_SECRET='<random-secret>' `
  -e PUBLIC_ALLOWED_ORIGINS='https://your-site.example' `
  -v battery-sim-data:/data `
  battery-sim-public
```

The container intentionally runs one web worker because its concurrency and
hourly quota guards are process-local. A production platform should keep one
container replica for this public demo unless those guards are moved to a
shared queue or database.
