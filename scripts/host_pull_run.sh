#!/usr/bin/env bash
# On the fixed Aliyun host: login ACR, pull image, start with compose.
# Usage:
#   export ACR_IMAGE=registry.cn-hangzhou.aliyuncs.com/<ns>/jianfei:latest
#   export ACR_USER=... ACR_PASS=...
#   # place config.yaml next to this compose file
#   ./scripts/host_pull_run.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${ACR_IMAGE:?set ACR_IMAGE}"
: "${ACR_USER:?set ACR_USER}"
: "${ACR_PASS:?set ACR_PASS}"

REGISTRY="${ACR_IMAGE%%/*}"
echo "$ACR_PASS" | docker login "$REGISTRY" -u "$ACR_USER" --password-stdin
docker pull "$ACR_IMAGE"

mkdir -p data uploads/meals
if [[ ! -f config.yaml ]]; then
  echo "Missing ./config.yaml — copy from your private config before start."
  exit 1
fi

IMAGE="$ACR_IMAGE" docker compose up -d
docker compose ps
echo "App: http://0.0.0.0:${PORT:-8000}"
# Inspect git remote inside container:
docker exec jianfei git remote -v || true
