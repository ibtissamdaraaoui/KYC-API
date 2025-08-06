from pydantic import BaseModel
from datetime import datetime
from typing import Optional # MODIFICATION: Importer Optional
from .models import KycCaseStatus # MODIFICATION: Importer l'Enum depuis models

class KycCaseCreate(BaseModel):
    kyc_case_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class KycCaseStatusResponse(BaseModel):
    kyc_case_id: str
    status: KycCaseStatus # Utilise votre Enum
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True