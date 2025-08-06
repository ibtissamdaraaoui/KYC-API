# Fichier: matching_service/app/minio_client.py

import os
import boto3
from botocore.client import Config

# Essayer de charger les variables depuis un fichier .env (utile pour le développement local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─────────────────── Paramètres de connexion à MinIO ───────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

# --- Configuration des NOMS DE BUCKETS (MODIFIÉ) ---
# On définit un nom pour chaque type de ressource.
MINIO_DOCS_BUCKET = os.getenv("MINIO_DOCS_BUCKET", "kyc-docs")
MINIO_SELFIES_BUCKET = os.getenv("MINIO_SELFIES_BUCKET", "kyc-selfies")

# --- Vérification critique au démarrage ---
# Si une variable essentielle manque, le service s'arrête avec un message clair.
if not all([MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY]):
    raise ValueError(
        "ERREUR CRITIQUE: Une ou plusieurs variables MinIO sont manquantes "
        "(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY). Le service ne peut pas démarrer."
    )

# ─────────────────── Création du client Boto3 pour MinIO ───────────────────
s3_client = None
try:
    # S'assurer que l'endpoint a le bon format (http:// ou https://)
    if not MINIO_ENDPOINT.startswith(("http://", "https://")):
        endpoint_url = f"http://{MINIO_ENDPOINT}"
    else:
        endpoint_url = MINIO_ENDPOINT

    # Création de l'instance du client qui sera partagée
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
        config=Config(signature_version="s3v4")
    )
    
    # Message de confirmation dans les logs
    print(f"✅ Client MinIO initialisé. Connexion à l'endpoint: '{endpoint_url}'")
    print(f"   - Bucket Documents: '{MINIO_DOCS_BUCKET}'")
    print(f"   - Bucket Selfies:   '{MINIO_SELFIES_BUCKET}'")

except Exception as e:
    print(f"❌ ERREUR CRITIQUE: Impossible d'initialiser le client MinIO. Erreur: {e}")
    # Relance l'exception pour arrêter le démarrage du conteneur si la connexion échoue.
    raise