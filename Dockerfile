FROM python:3.11-slim

WORKDIR /app

RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
    && apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    libffi-dev \
    libcairo2-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt .
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r requirements-web.txt

COPY . .

RUN mkdir -p results

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD sh -c 'host="${HEALTHCHECK_HOST:-${TRUSTED_HOSTS%%,*}}"; if [ -z "$host" ] || [ "$host" = "*" ]; then host=localhost; fi; curl -f -H "Host: $host" http://localhost:8080/healthz || exit 1'

CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers"]
