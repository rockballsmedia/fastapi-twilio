#!/usr/bin/env sh
# Démarre Uvicorn en arrière-plan
uvicorn main:app --host 127.0.0.1 --port 5000 &

# Puis lance Caddy, qui fera le TLS & proxy
caddy run --config /etc/caddy/Caddyfile
