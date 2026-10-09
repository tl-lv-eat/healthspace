# syntax=docker/dockerfile:1
# Multi-stage: Vue build + FastAPI runtime. Image keeps a git checkout with origin.

ARG GIT_REMOTE=""

# ----- frontend -----
FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ----- runtime -----
FROM python:3.12-slim-bookworm AS runtime

ARG GIT_REMOTE=""
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    JIANFEI_GIT_REMOTE=${GIT_REMOTE}

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App source (include .git so remote stays bound inside the image)
COPY . .
COPY --from=frontend /src/frontend/dist ./frontend/dist

# Bind / refresh origin to the same remote used for push (build-arg)
RUN set -eux; \
    if [ -d .git ]; then \
      if [ -n "$GIT_REMOTE" ]; then \
        if git remote get-url origin >/dev/null 2>&1; then \
          git remote set-url origin "$GIT_REMOTE"; \
        else \
          git remote add origin "$GIT_REMOTE"; \
        fi; \
      fi; \
      git remote -v || true; \
      git status -sb || true; \
    else \
      echo "WARN: .git missing in build context — image will not have git remote"; \
    fi

# Seed dirs; runtime should mount /app/data and /app/config.yaml for persistence
RUN mkdir -p /app/data /app/uploads/meals \
    && if [ ! -f /app/config.yaml ] && [ -f /app/config.example.yaml ]; then \
         cp /app/config.example.yaml /app/config.yaml; \
       fi

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/auth/personas >/dev/null || exit 1

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
