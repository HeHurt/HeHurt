FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYBAMM_DISABLE_TELEMETRY=true \
    PUBLIC_ENV=production \
    PUBLIC_JOB_ROOT=/data/studio_jobs

WORKDIR /app

COPY deploy/public_backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN mkdir -p /app/api /data/studio_jobs
COPY api/__init__.py api/jobs.py api/public_app.py /app/api/

VOLUME ["/data"]
EXPOSE 8080

CMD ["uvicorn", "api.public_app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]

