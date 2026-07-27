#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
port="${1:-8000}"
printf 'Serving PyBlocks Studio at http://127.0.0.1:%s/standalone/\n' "$port"
exec python3 -m http.server "$port"
