# Root Dockerfile for Back4App Containers (and other host-root builds).
# Build context: repository root. Does not replace backend/Dockerfile (Compose).
# Python version aligned with backend/Dockerfile and GitHub Actions CI (3.14).

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --create-home --home-dir /home/app app

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install --retries 5 --timeout 120 -r requirements.txt \
    && python -m pip install --retries 5 --timeout 120 -r requirements-dev.txt

# Application code + Alembic live under backend/; place them at /app so
# `uvicorn app.main:app` and `alembic` match the Compose image layout.
COPY --chown=app:app backend/ ./

RUN mkdir -p /app/.storage /app/.chroma \
        /home/app/.cache/ruff \
        /home/app/.cache/mypy \
    && chown -R app:app /app /home/app/.cache

ENV RUFF_CACHE_DIR=/home/app/.cache/ruff \
    MYPY_CACHE_DIR=/home/app/.cache/mypy

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
