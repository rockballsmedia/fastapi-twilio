# 1) Build Python
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# 2) Final image avec Caddy et votre app
FROM caddy:2.8-alpine

# Copie de l'app Python
COPY --from=builder /app /app

# Copie de votre Caddyfile
COPY Caddyfile /etc/caddy/Caddyfile

# Pour lancer à la fois Uvicorn et Caddy
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Exposez les ports 80 et 443
EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
