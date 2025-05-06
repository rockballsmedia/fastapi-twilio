# Utilise l’image Python slim
FROM python:3.12-slim

WORKDIR /app

# Copier et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l’application
COPY . .

# Exposer le port 5000 (Coolify proxysera monté dessus)
EXPOSE 5000

# Lancer Uvicorn directement
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
