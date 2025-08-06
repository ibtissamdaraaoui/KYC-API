from pydantic import BaseModel

class SelfieResponse(BaseModel):
    id: int
    kyc_case_id: str
    file_key: str
    encryption_key_id: str

    class Config:
        from_attributes = True
