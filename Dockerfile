# ─── Étape 1 : builder ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Dépendances Python
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Copie du code et du Caddyfile
COPY main.py .env . /app/
COPY Caddyfile /etc/caddy/Caddyfile

# ─── Étape 2 : image finale ─────────────────────────────────────────────
FROM debian:bookworm-slim

# Installer Uvicorn, Caddy et curl (pour healthcheck)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    ca-certificates curl \
 && apt-get install -y wget gnupg \
 && wget -qO - https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | gpg --dearmor > /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/debian bookworm main" \
    > /etc/apt/sources.list.d/caddy-stable.list \
 && apt-get update \
 && apt-get install -y caddy \
 && rm -rf /var/lib/apt/lists/*

# Copier Uvicorn + libs
COPY --from=builder /install /usr/local
WORKDIR /app
COPY . /app

# Expose ports : 80 (HTTP), 443 (HTTPS)
EXPOSE 80 443

# Démarrer Caddy + Uvicorn (tini pour le PID 1)
RUN apt-get update && apt-get install -y --no-install-recommends tini
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sh", "-c", "\
    caddy run --config /etc/caddy/Caddyfile & \
    uvicorn main:app --host 127.0.0.1 --port 5000 \
"]
