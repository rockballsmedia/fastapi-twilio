# ─── Build de votre appli Python ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ─── Image finale ─────────────────────────────────────────────────────────
FROM caddy:2.8-alpine

# 1) Installer Python (pour Uvicorn) + venv
RUN apk add --no-cache python3 py3-virtualenv

# 2) Créer un venv et y installer Uvicorn + dépendances
RUN python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir uvicorn

# 3) Copier votre code
COPY --from=builder /app /app
WORKDIR /app

# 4) Copier le Caddyfile
COPY Caddyfile /etc/caddy/Caddyfile

# Ports exposés par Caddy
EXPOSE 80 443

# 5) Entrypoint qui lance Uvicorn depuis le venv, puis Caddy
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
