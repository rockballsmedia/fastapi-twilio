# ─── Étape 1 : builder Python ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

COPY . /app

# ─── Étape 2 : image finale avec Caddy ────────────────────────────────────
FROM caddy:2.8-alpine

# Installer Python + Uvicorn dans l’image Caddy
RUN apk add --no-cache python3 py3-pip
RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir uvicorn websockets \
    && pip3 install --no-cache-dir --prefix=/usr/local /app

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . /app

# Copier le Caddyfile pour qu’il serve sur le bon domaine
COPY Caddyfile /etc/caddy/Caddyfile

# Expose HTTP & HTTPS
EXPOSE 80 443

# Démarrage de Caddy + Uvicorn
ENTRYPOINT ["sh", "-c"]
CMD ["caddy run --config /etc/caddy/Caddyfile & uvicorn main:app --host 127.0.0.1 --port 5000"]
