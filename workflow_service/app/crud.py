from sqlalchemy.orm import Session
from app.models import KycCase, KycCaseStatus
from fastapi import HTTPException

# --- DÉBUT DU NOUVEAU CODE ---
def get_and_validate_case_for_upload(db: Session, kyc_case_id: str) -> KycCase:
    """
    Récupère un cas KYC et valide s'il est apte à recevoir un upload.
    Lève une HTTPException en cas de problème.
    """
    # 1. Vérifier si le cas existe
    case = db.query(KycCase).filter(KycCase.kyc_case_id == kyc_case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"KYC Case '{kyc_case_id}' not found.")
        
    # 2. Vérifier si le statut permet l'upload
    if case.status != KycCaseStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot upload files for this case. Its current status is '{case.status.value}'."
        )
        
    return case
# --- FIN DU NOUVEAU CODE ---

def update_kyc_case_status(db: Session, kyc_case_id: str, status: KycCaseStatus, reason: str = None):
    """
    Met à jour le statut et la raison de l'échec d'un cas KYC.
    """
    db_case = db.query(KycCase).filter(KycCase.kyc_case_id == kyc_case_id).first()
    
    if db_case:
        db_case.status = status
        if reason:
            db_case.failure_reason = reason
        db.commit()
        db.refresh(db_case)
        print(f"Cas KYC '{kyc_case_id}' mis à jour avec le statut '{status.value}'.")
        return db_case
    else:
        print(f"[ERREUR] Cas KYC '{kyc_case_id}' non trouvé pour la mise à jour.")
        return None