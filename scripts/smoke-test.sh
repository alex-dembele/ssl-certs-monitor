#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"
API_URL="${API_URL:-http://localhost:8000}"

curl --fail --silent --show-error "${BASE_URL}/" >/dev/null
curl --fail --silent --show-error "${API_URL}/health" >/dev/null

if [[ -n "${BACKEND_API_TOKEN:-}" ]]; then
  curl --fail --silent --show-error \
    -H "Authorization: Bearer ${BACKEND_API_TOKEN}" \
    "${API_URL}/api/domains" >/dev/null
else
  curl --fail --silent --show-error "${API_URL}/api/domains" >/dev/null
fi

echo "Smoke test passed: frontend, API health and domain endpoint are reachable."
