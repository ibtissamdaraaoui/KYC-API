# app/router/case.py
# MODIFICATION: Ajouter HTTPException à l'import
from fastapi import APIRouter, Depends, HTTPException 
from sqlalchemy.orm import Session
from uuid import uuid4
from app.database import SessionLocal
from app import models, schemas
from app.security import get_current_client_id

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.KycCaseCreate)
def create_case(
    db: Session = Depends(get_db),
    client_id: str = Depends(get_current_client_id)
    ):
    """
    Crée un nouveau cas KYC avec un kyc_case_id garanti unique.
    """
    
    # --- DÉBUT DE LA MODIFICATION ---

    kyc_case_id = None
    # On boucle tant qu'on n'a pas trouvé un ID unique.
    # En pratique, cette boucle ne s'exécutera qu'une seule fois 99.999999% du temps.
    while True:
        # 1. On génère un ID potentiel
        potential_id = f"KYC-{uuid4().hex[:8].upper()}"
        
        # 2. On vérifie s'il existe déjà en BDD
        # .first() est très efficace car il s'arrête dès qu'il trouve un résultat.
        existing_case = db.query(models.KycCase).filter(models.KycCase.kyc_case_id == potential_id).first()
        
        # 3. S'il n'existe pas (le résultat est None), on a notre ID !
        if not existing_case:
            kyc_case_id = potential_id
            break # On sort de la boucle

    # --- FIN DE LA MODIFICATION ---

    # Le reste du code utilise maintenant l'ID garanti unique
    new_case = models.KycCase(
        kyc_case_id=kyc_case_id,
        owner_id=client_id
        )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    return new_case



@router.get("/{kyc_case_id}/status", response_model=schemas.KycCaseStatusResponse)
def get_case_status(
    kyc_case_id: str,
    db: Session = Depends(get_db),
    client_id: str = Depends(get_current_client_id)
    ):
    """
    Récupère le statut actuel d'un cas KYC.
    Le client peut appeler cette route en boucle (polling) pour obtenir le résultat final.
    """
    case = db.query(models.KycCase).filter(
        models.KycCase.kyc_case_id == kyc_case_id,
        models.KycCase.owner_id == client_id 
    ).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="KYC Case not found")
        
    return case