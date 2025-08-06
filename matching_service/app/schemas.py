# Fichier: matching_service/app/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# =====================================================================
# SCHÉMAS POUR LES PAYLOADS DES MESSAGES KAFKA ENTRANTS
# Ces schémas valident la structure des messages que votre service consomme.
# =====================================================================

class DocumentLocations(BaseModel):
    """
    Sous-schéma pour les chemins des fichiers de document dans le message
    du verification_service.
    """
    recto_path: str
    verso_path: Optional[str] = None

class DocumentVerifiedPayload(BaseModel):
    """
    Structure attendue pour un message sur le topic 'document_verified'.
    """
    kyc_case_id: str
    document_id: int
    document_locations: DocumentLocations

class SelfieUploadedPayload(BaseModel):
    """
    Structure attendue pour un message sur le topic 'selfie_uploaded'.
    Note : il n'y a pas d'informations sensibles comme le chemin de la clé Vault.
    """
    kyc_case_id: str
    id: int  # L'ID du selfie dans la table 'selfies'
    file_key: str  # Le chemin vers le fichier du selfie dans MinIO


# =====================================================================
# SCHÉMAS POUR LES OPÉRATIONS EN BASE DE DONNÉES (CRUD)
# Ces schémas sont utilisés par vos fonctions CRUD pour créer ou retourner des objets.
# =====================================================================

class MatchingTaskBase(BaseModel):
    """
    Schéma de base pour une tâche de matching. Contient les champs
    qui peuvent être fournis lors de la création ou de la mise à jour.
    """
    kyc_case_id: str
    document_verified_received: bool = False
    selfie_uploaded_received: bool = False
    document_id: Optional[int] = None
    recto_path: Optional[str] = None
    selfie_id: Optional[int] = None
    selfie_path: Optional[str] = None

class MatchingTaskCreate(MatchingTaskBase):
    """
    Schéma utilisé spécifiquement pour créer une nouvelle tâche.
    Dans notre cas, on ne crée qu'avec le kyc_case_id, le reste est mis à jour.
    """
    pass # Hérite de tous les champs de MatchingTaskBase

class MatchingTaskResponse(MatchingTaskBase):
    """
    Schéma pour retourner une tâche de matching depuis la BDD ou une API.
    """
    class Config:
        from_attributes = True # Permet de créer ce schéma depuis un objet SQLAlchemy (MatchingTask)


class MatchingResultBase(BaseModel):
    """
    Schéma de base contenant les champs nécessaires pour créer un résultat de matching.
    """
    kyc_case_id: str
    is_match: bool
    distance: float
    model_name: str
    details: Optional[Dict[str, Any]] = None

class MatchingResultCreate(MatchingResultBase):
    """Schéma utilisé pour insérer un nouveau résultat dans la base de données."""
    pass

class MatchingResultResponse(MatchingResultBase):
    """
    Schéma utilisé pour retourner un résultat de matching complet depuis la base de données.
    """
    id: int
    created_at: datetime

    class Config:
        from_attributes = True