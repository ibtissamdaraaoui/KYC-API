# Fichier: matching_service/app/crud.py

from sqlalchemy.orm import Session
from . import models

def get_or_create_task(db: Session, kyc_case_id: str) -> models.MatchingTask:
    """
    Récupère une tâche de matching existante par son kyc_case_id.
    Si elle n'existe pas, la crée.
    """
    task = db.query(models.MatchingTask).filter_by(kyc_case_id=kyc_case_id).first()
    if not task:
        print(f"[{kyc_case_id}] Nouvelle tâche de matching créée en BDD.")
        task = models.MatchingTask(kyc_case_id=kyc_case_id)
        db.add(task)
        db.commit()
        db.refresh(task)
    return task

def update_task_with_doc_info(db: Session, task: models.MatchingTask, doc_id: int, recto_path: str):
    """Met à jour une tâche avec les informations du document vérifié."""
    task.document_id = doc_id
    task.recto_path = recto_path
    task.document_verified_received = True
    db.commit()
    print(f"[{task.kyc_case_id}] Tâche mise à jour avec les infos du document.")

def update_task_with_selfie_info(db: Session, task: models.MatchingTask, selfie_id: int, selfie_path: str):
    """Met à jour une tâche avec les informations du selfie uploadé."""
    task.selfie_id = selfie_id
    task.selfie_path = selfie_path
    task.selfie_uploaded_received = True
    db.commit()
    print(f"[{task.kyc_case_id}] Tâche mise à jour avec les infos du selfie.")