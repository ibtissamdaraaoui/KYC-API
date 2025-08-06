# Fichier: workflow_service/app/schemas.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# --- CORRECTION ---
# On importe l'Enum depuis son emplacement réel : le fichier models.py
from .models import KycCaseStatus

class KycCaseCreate(BaseModel):
    kyc_case_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class KycCaseStatusResponse(BaseModel):
    kyc_case_id: str
    
    # --- CORRECTION ---
    # Le type du statut est maintenant l'Enum 'KycCaseStatus' pour correspondre au modèle.
    status: KycCaseStatus 
    
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True