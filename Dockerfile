# Choix de l’image officielle Python légère
FROM python:3.12-slim

# Répertoire de travail dans le conteneur
WORKDIR /app

# Copie du code source dans le conteneur
COPY . /app

# Installation des dépendances
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-dotenv \
    twilio \
    openai \
    websockets \
    requests

# Exposition du port utilisé par Uvicorn
ENV PORT=5000
EXPOSE 5000

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]

