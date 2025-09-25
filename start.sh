#!/usr/bin/env bash
set -euo pipefail

echo "=== Runtime info ==="
python --version || true
pip --version || true
echo "PORT=${PORT:-unset}"
echo "PWD=$(pwd)"
ls -la || true

echo "=== Network check ==="
python - << 'PY'
import socket, os
host = '0.0.0.0'
port = int(os.environ.get('PORT', '5000'))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((host, port))
    print(f"Can bind to {host}:{port}")
finally:
    try:
        s.close()
    except Exception:
        pass
PY

echo "=== Starting server ==="
exec python -m gunicorn \
  --workers 1 \
  --threads 2 \
  --worker-class gthread \
  --timeout 120 \
  --graceful-timeout 30 \
  --log-level info \
  --access-logfile '-' \
  --error-logfile '-' \
  --bind 0.0.0.0:${PORT:-5000} \
  app:app

