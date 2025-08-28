# Fichier: app/router/proxy.py

from fastapi import APIRouter, UploadFile, File, Form, Depends 
from sqlalchemy.orm import Session 
import requests

from app.router.case import get_db 
from app.crud import get_and_validate_case_for_upload
from app.security import get_current_client_id  

router = APIRouter()

# URL des services (inchangé)
DOCUMENT_SERVICE_URL = "http://127.0.0.1:8003/upload"
SELFIE_SERVICE_URL = "http://127.0.0.1:8004/upload-selfie"

@router.post("/upload-cin")
async def proxy_upload(
    kyc_case_id: str = Form(...),
    recto: UploadFile = File(...),
    verso: UploadFile = File(...),
    db: Session = Depends(get_db), # <-- AJOUT DE LA DÉPENDANCE À LA BDD
    client_id: str = Depends(get_current_client_id)  
):
    """Transfère l'upload vers le document_service après validation du cas."""
    
    # --- AJOUT DE LA VALIDATION ---
    # Si le cas n'est pas valide, cette fonction lèvera une exception
    # et l'exécution s'arrêtera ici.
    get_and_validate_case_for_upload(db=db, kyc_case_id=kyc_case_id)
    # -----------------------------

    files = {
        "recto": (recto.filename, await recto.read(), recto.content_type),
        "verso": (verso.filename, await verso.read(), verso.content_type),
    }
    data = {"kyc_case_id": kyc_case_id, "document_type": "CNI"}
    r = requests.post(DOCUMENT_SERVICE_URL, data=data, files=files, timeout=60)
    r.raise_for_status()
    return r.json()

@router.post("/upload-selfie")
async def proxy_upload_selfie(
    kyc_case_id: str = Form(...),
    selfie: UploadFile = File(...),
    db: Session = Depends(get_db),# <-- AJOUT DE LA DÉPENDANCE À LA BDD
    client_id: str = Depends(get_current_client_id)  
):
    """Transfère l'upload vers le selfie_service après validation du cas."""
    
    # --- AJOUT DE LA VALIDATION ---
    get_and_validate_case_for_upload(db=db, kyc_case_id=kyc_case_id)
    # -----------------------------

    files = {
        "selfie": (selfie.filename, await selfie.read(), selfie.content_type),
    }
    data = {"kyc_case_id": kyc_case_id}

    r = requests.post(SELFIE_SERVICE_URL, data=data, files=files, timeout=60)
    r.raise_for_status()
    return r.json()