# Fichier: matching_service/app/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# =====================================================================
# SCHÉMAS POUR LES PAYLOADS DES MESSAGES KAFKA (Validation des entrées)
# =====================================================================

class DocumentVerifiedPayload(BaseModel):
    """
    Structure attendue pour un message sur le topic 'document_verified'.
    """
    kyc_case_id: str
    document_id: int

class SelfieUploadedPayload(BaseModel):
    """
    Structure attendue pour un message sur le topic 'selfie_uploaded'.
    """
    kyc_case_id: str
    id: int = Field(..., alias='selfie_id') # Permet de parser 'id' et de l'utiliser comme 'selfie_id'

    class Config:
        populate_by_name = True # Active l'utilisation de l'alias

# =====================================================================
# SCHÉMAS POUR LA TABLE `MatchingTask` (Le tableau de bord)
# =====================================================================

class MatchingTaskBase(BaseModel):
    """
    Schéma de base pour une tâche de matching.
    """
    kyc_case_id: str
    document_id: Optional[int] = None
    selfie_id: Optional[int] = None
    status: str
    updated_at: datetime

class MatchingTaskResponse(MatchingTaskBase):
    """
    Schéma utilisé pour retourner une tâche de matching depuis la BDD.
    """
    class Config:
        from_attributes = True

# =====================================================================
# SCHÉMAS POUR LA TABLE `MatchingResult` (L'archive)
# =====================================================================

class MatchingResultBase(BaseModel):
    """
    Champs de base pour un résultat de matching.
    """
    kyc_case_id: str
    document_id: int
    selfie_id: int
    match_result: str
    distance: Optional[float] = None
    model_details: Optional[Dict[str, Any]] = None

class MatchingResultCreate(MatchingResultBase):
    """
    Schéma utilisé par le CRUD pour créer une nouvelle entrée dans la BDD.
    """
    pass

class MatchingResultResponse(MatchingResultBase):
    """
    Schéma utilisé pour retourner un résultat complet depuis une API ou la BDD.
    """
    id: int
    created_at: datetime

    class Config:
        from_attributes = True