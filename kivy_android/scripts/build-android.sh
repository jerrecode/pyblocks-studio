#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-debug}"
case "$MODE" in
  debug|release) ;;
  *) echo "Usage: $0 [debug|release]" >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/preflight.py

if [[ ! -x .venv-build/bin/buildozer ]]; then
  echo "Missing .venv-build. Run scripts/install-build-deps-debian.sh first." >&2
  exit 1
fi

. .venv-build/bin/activate
export BUILDOZER_WARN_ON_ROOT=0
buildozer -v android "$MODE"

printf '\nArtifacts:\n'
find bin -maxdepth 1 -type f -printf '  %p\n' 2>/dev/null || true
