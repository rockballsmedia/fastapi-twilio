#!/usr/bin/env sh
# 1) Démarre Uvicorn dans le venv
/venv/bin/uvicorn main:app --host 127.0.0.1 --port 5000 &

# 2) Lance Caddy (TLS + reverse-proxy)
/usr/bin/caddy run --config /etc/caddy/Caddyfile

