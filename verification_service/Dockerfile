# ──────────────── image de base ────────────────
FROM python:3.10-slim

# ──────────────── Installation dépendances système ────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY app/ ./app/

# Exposer le port pour FastAPI
EXPOSE 8002

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
