# Fichier: document_service/app/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentResponse(BaseModel):
    id: int
    kyc_case_id: str 
    recto_path: str
    verso_path: Optional[str]
    vault_key_path: str
    created_at: datetime

    class Config:
        from_attributes = True