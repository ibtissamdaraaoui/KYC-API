# Fichier: verification_service/app/schemas.py

from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

# =====================================================================
# SCHÉMA POUR LA CRÉATION D'UN RÉSULTAT DE VÉRIFICATION
# =====================================================================
class VerificationResultCreate(BaseModel):
    """
    Schéma utilisé pour insérer un nouveau résultat de vérification dans la BDD.
    Note : kyc_case_id n'est plus ici car il n'est pas une colonne directe de la table.
    """
    # Clé étrangère vers le document qui a été analysé
    document_id: int

    # Le statut final de la vérification (ex: "VALIDÉ", "NON_VALIDÉ")
    status: str

    # Texte brut extrait par l'outil OCR
    raw_text: str

    # Données structurées et rapport de validation complet (de l'IA), stocké en JSON
    structured_data: Dict[str, Any]


# =====================================================================
# SCHÉMA POUR LA RÉPONSE API (RETOURNER UN RÉSULTAT)
# =====================================================================
class VerificationResultResponse(BaseModel):
    """
    Schéma pour retourner un résultat de vérification complet depuis la BDD.
    """
    id: int
    document_id: int
    status: str
    raw_text: str
    structured_data: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True # Permet de créer ce schéma depuis un objet SQLAlchemy