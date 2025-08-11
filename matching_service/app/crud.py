# Fichier: matching_service/app/crud.py
from sqlalchemy.orm import Session
from . import models

def get_or_create_task(db: Session, kyc_case_id: str) -> models.MatchingTask:
    task = db.query(models.MatchingTask).filter_by(kyc_case_id=kyc_case_id).first()
    if not task:
        task = models.MatchingTask(kyc_case_id=kyc_case_id)
        db.add(task)
        db.commit()
        db.refresh(task)
    return task

def update_task_with_document(db: Session, task: models.MatchingTask, doc_id: int):
    task.document_id = doc_id
    
    print(f"[{task.kyc_case_id}] Tâche de matching mise à jour avec document ID: {doc_id}")

def update_task_with_selfie(db: Session, task: models.MatchingTask, selfie_id: int):
    task.selfie_id = selfie_id
    
    print(f"[{task.kyc_case_id}] Tâche de matching mise à jour avec selfie ID: {selfie_id}")

def create_matching_result(db: Session, result_data: dict):
    new_result = models.MatchingResult(**result_data)
    db.add(new_result)
    
    return new_result