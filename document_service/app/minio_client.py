import boto3
import os

# ────────────────────────────────────────────────────────────────
# 1) Paramètres MinIO (récupérés depuis les variables d’environnement)
# ────────────────────────────────────────────────────────────────
MINIO_ENDPOINT     = os.getenv("MINIO_ENDPOINT", "localhost:9000")      # Hôte MinIO
MINIO_ACCESS_KEY   = os.getenv("MINIO_ACCESS_KEY", "minioadmin")        # Clé d’accès
MINIO_SECRET_KEY   = os.getenv("MINIO_SECRET_KEY", "minioadmin")        # Clé secrète
MINIO_BUCKET       = os.getenv("MINIO_BUCKET", "kyc-docs")              # Nom du bucket par défaut

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
