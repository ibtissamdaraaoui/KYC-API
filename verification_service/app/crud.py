from sqlalchemy.orm import Session
from app.models import VerificationResult
from app.schemas import VerificationResultCreate

def create_verification_result(db: Session, result: VerificationResultCreate):
    """
    Insère un résultat OCR structuré dans la base de données.
    """
    db_result = VerificationResult(
        kyc_case_id=result.kyc_case_id,
        document_id=result.document_id,
        raw_text=result.raw_text,
        structured_data=result.structured_data,
        status=result.status
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result
