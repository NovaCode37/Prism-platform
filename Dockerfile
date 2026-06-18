ARG NODE_IMAGE=node:alpine
ARG PYTHON_IMAGE=python:3-alpine
ARG UV_IMAGE=ghcr.io/astral-sh/uv:alpine

FROM --platform=$BUILDPLATFORM ${UV_IMAGE} AS uv-bin

FROM ${NODE_IMAGE} AS frontend-build

WORKDIR /build/frontend

ENV NEXT_TELEMETRY_DISABLED=1

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./

ARG NEXT_PUBLIC_BASE_PATH=
ARG NEXT_PUBLIC_API_URL=
ARG NEXT_PUBLIC_API_KEY=
ENV NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_API_KEY=${NEXT_PUBLIC_API_KEY}

RUN npm run build \
    && npm cache clean --force

FROM ${PYTHON_IMAGE} AS python-build

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY --from=uv-bin /usr/local/bin/uv /usr/local/bin/uv

RUN apk add --no-cache --virtual .build-deps \
    build-base \
    cargo \
    cairo-dev \
    freetype-dev \
    jpeg-dev \
    lcms2-dev \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    linux-headers \
    openjpeg-dev \
    openssl-dev \
    pkgconf \
    tiff-dev \
    zlib-dev

COPY requirements-web.txt .
RUN uv venv /opt/venv --python /usr/local/bin/python --no-python-downloads \
    && uv pip install --python /opt/venv/bin/python --no-python-downloads -r requirements-web.txt \
    && find /opt/venv -type d \( -name tests -o -name test -o -name __pycache__ \) -prune -exec rm -rf '{}' + \
    && find /opt/venv -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.a' \) -delete \
    && (find /opt/venv -type f -name '*.so' -exec strip --strip-unneeded '{}' + || true) \
    && rm -rf \
    /opt/venv/bin/pip* \
    /opt/venv/lib/python*/site-packages/_distutils_hack \
    /opt/venv/lib/python*/site-packages/distutils-precedence.pth \
    /opt/venv/lib/python*/site-packages/pip* \
    /opt/venv/lib/python*/site-packages/pkg_resources \
    /opt/venv/lib/python*/site-packages/setuptools* \
    /opt/venv/lib/python*/site-packages/wheel*

FROM ${PYTHON_IMAGE}

WORKDIR /app

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache curl \
    && rm -rf \
    /usr/local/bin/pip* \
    /usr/local/lib/python*/ensurepip \
    /usr/local/lib/python*/site-packages/pip*

COPY --from=python-build /opt/venv /opt/venv

COPY . .
COPY --from=frontend-build /build/frontend/out /app/frontend/out

RUN mkdir -p results scan_data module_cache

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD sh -c 'host="${HEALTHCHECK_HOST:-${TRUSTED_HOSTS%%,*}}"; if [ -z "$host" ] || [ "$host" = "*" ]; then host=localhost; fi; curl -f -H "Host: $host" http://localhost:8080/healthz || exit 1'

CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers"]
