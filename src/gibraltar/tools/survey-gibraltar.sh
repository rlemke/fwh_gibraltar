#!/usr/bin/env bash
# Survey Gibraltar from a local OSM extract and render the Hollow Mountain map.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
[ -f "${REPO_ROOT}/.venv/bin/activate" ] && source "${REPO_ROOT}/.venv/bin/activate"
exec python3 "${SCRIPT_DIR}/survey_gibraltar.py" "$@"
