# Fichier: selfie_service/app/schemas.py

from pydantic import BaseModel
from datetime import datetime

# =====================================================================
# SCHÉMAS POUR LA TABLE `Selfie`
# =====================================================================

class SelfieBase(BaseModel):
    """
    Champs partagés pour un selfie.
    """
    kyc_case_id: str
    file_key: str
    encryption_key_id: str

class SelfieCreate(SelfieBase):
    """
    Schéma utilisé par le CRUD pour créer un nouveau selfie en BDD.
    Les données viennent de l'endpoint d'upload.
    """
    pass

class SelfieResponse(SelfieBase):
    """
    Schéma utilisé pour la réponse de l'API.
    Il inclut les champs générés automatiquement par la base de données.
    """
    id: int
    created_at: datetime

    class Config:
        from_attributes = True