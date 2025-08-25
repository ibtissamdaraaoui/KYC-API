import boto3
import os

# ────────────────────────────────────────────────────────────────
# 1) Paramètres MinIO (récupérés depuis les variables d’environnement)
# ────────────────────────────────────────────────────────────────
MINIO_ENDPOINT     = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY   = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY   = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET       = os.getenv("MINIO_DOCS_BUCKET")             # Nom du bucket par défaut
# Ajout de la vérification pour la robustesse
if not all([MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET]):
    raise ValueError("Une ou plusieurs variables d'environnement MinIO sont manquantes.")
# ────────────────────────────────────────────────────────────────
# 2) Initialisation du client Boto3 pour MinIO
# ────────────────────────────────────────────────────────────────
s3_client = boto3.client(
    's3',
    endpoint_url=f"http://{MINIO_ENDPOINT}",  # Protocole explicite requis
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1"  # Doit être défini même si non utilisé par MinIO
)

# ────────────────────────────────────────────────────────────────
# 3) (Optionnel) Création automatique du bucket si inexistant
# ────────────────────────────────────────────────────────────────
try:
    s3_client.head_bucket(Bucket=MINIO_BUCKET)
except s3_client.exceptions.ClientError as e:
    # Bucket inexistant → on le crée
    print(f"[MinIO] Bucket '{MINIO_BUCKET}' introuvable. Création en cours...")
    s3_client.create_bucket(Bucket=MINIO_BUCKET)
    print(f"[MinIO] Bucket '{MINIO_BUCKET}' créé avec succès.")
except Exception as e:
    print(f"[MinIO] ❌ Erreur inattendue lors de la vérification du bucket : {e}")
    raise
