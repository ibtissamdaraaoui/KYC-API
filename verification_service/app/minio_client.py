# app/minio_client.py

import os
import boto3
from botocore.client import Config



# ─────────── Paramètres MinIO (S3-compatible) ───────────
MINIO_ENDPOINT   = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET     = os.getenv("MINIO_DOCS_BUCKET")

# --- AJOUT DE LA VÉRIFICATION CRITIQUE ---
if not all([MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET]):
    raise ValueError("Une ou plusieurs variables d'environnement MinIO sont manquantes.")

# ─────────── Création du client Boto3 pour MinIO ───────────
s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
    config=Config(signature_version="s3v4")
)
