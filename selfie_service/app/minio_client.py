from minio import Minio
import os


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_SELFIES_BUCKET")

# --- AJOUT DE LA VÉRIFICATION CRITIQUE ---
if not all([MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET]):
    raise ValueError("Une ou plusieurs variables d'environnement MinIO pour le service Selfie sont manquantes.")

s3_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Assure le bucket
if not s3_client.bucket_exists(MINIO_BUCKET):
    s3_client.make_bucket(MINIO_BUCKET)
