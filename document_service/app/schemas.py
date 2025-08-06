from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    kyc_case_id: str 
    filename: str
    file_path: str
    upload_time: datetime
    vault_key_path: str   # <-- seulement si tu veux l’afficher côté client

    class Config:
        from_attributes = True
