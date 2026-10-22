FROM ghcr.io/spiffe/spire-agent:1.14.1@sha256:7bb8469af28f00908a96a8a51fb36cbbcdfb85efe78e94b492f949f33284bf4d AS spire
FROM python:3.12.12-slim-bookworm@sha256:593bd06efe90efa80dc4eee3948be7c0fde4134606dd40d8dd8dbcade98e669c
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.lock.txt /app/requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --uid 10001 --create-home agent
COPY --from=spire /opt/spire/bin/spire-agent /opt/spire/bin/spire-agent
COPY testbed /app/testbed
COPY infra /app/infra
COPY scripts /app/scripts
COPY dashboard /app/dashboard
COPY analysis /app/analysis
CMD ["python", "-m", "testbed.service"]
