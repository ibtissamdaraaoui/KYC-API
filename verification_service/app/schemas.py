from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ─────────────────────────────────────────────
# Schéma utilisé lors de la création d'un résultat OCR structuré
# (par exemple : après que le service ait fait OCR + structuration via Ollama)
# ─────────────────────────────────────────────
class VerificationResultCreate(BaseModel):
    # Identifiant unique du dossier KYC (généré dans workflow_service)
    kyc_case_id: str

    # Référence au document (clé étrangère vers la table 'documents')
    document_id: int

    # Texte brut extrait par OCR (EasyOCR)
    raw_text: str

    # Données structurées retournées par Ollama, sous forme de JSON converti en string
    structured_data: str

    # Statut global de validation du document, par exemple : "VALIDÉ", "NON_VALIDÉ"
    status: str


# ─────────────────────────────────────────────
# Schéma utilisé pour renvoyer un résultat stocké depuis la base de données
# ─────────────────────────────────────────────
class VerificationResultResponse(BaseModel):
    # Identifiant unique en base (auto-incrémenté)
    id: int

    # Répétition des mêmes champs que dans la création
    kyc_case_id: str
    document_id: int
    raw_text: str
    structured_data: str
    status: str

    # Date de création de l'entrée (automatique dans le modèle SQLAlchemy)
    created_at: datetime

    # Permet de convertir automatiquement les objets SQLAlchemy en réponse JSON
    class Config:
        from_attributes = True  # Équivaut à orm_mode=True dans FastAPI 2.x
