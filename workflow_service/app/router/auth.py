# Fichier: workflow_service/app/router/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import uuid4

from app.database import SessionLocal
from app import models, security, kong_client

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ClientCreate(BaseModel):
    client_name: str
    password: str

class ClientLogin(BaseModel):
    application_id: str
    password: str

class TokenResponse(BaseModel):
    application_id: str
    api_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=TokenResponse, status_code=201)
def register_client(client: ClientCreate, db: Session = Depends(get_db)):
    """Enregistre un nouveau client, le provisionne sur Kong et retourne son premier token."""
    if db.query(models.ApiClient).filter(models.ApiClient.client_name == client.client_name).first():
        raise HTTPException(status_code=400, detail="Ce nom de client est déjà utilisé.")

    hashed_password = security.get_password_hash(client.password)
    application_id = f"app_{uuid4().hex[:12]}"

    try:
        client_jwt_secret = kong_client.provision_client_on_kong(application_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Échec de la communication avec la passerelle API: {e}")

    new_api_client = models.ApiClient(
        client_name=client.client_name,
        hashed_password=hashed_password,
        application_id=application_id,
        jwt_secret=client_jwt_secret
    )
    db.add(new_api_client)
    db.commit()

    api_token = security.create_access_token(
        data={"sub": application_id},
        secret_key=client_jwt_secret
    )
    return {"application_id": application_id, "api_token": api_token}

@router.post("/login", response_model=TokenResponse)
def login_for_token(form_data: ClientLogin, db: Session = Depends(get_db)):
    """Authentifie un client et retourne un nouveau token JWT."""
    api_client = db.query(models.ApiClient).filter(models.ApiClient.application_id == form_data.application_id).first()
    if not api_client or not security.verify_password(form_data.password, api_client.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID d'application ou mot de passe incorrect."
        )

    api_token = security.create_access_token(
        data={"sub": api_client.application_id},
        secret_key=api_client.jwt_secret
    )
    return {"application_id": api_client.application_id, "api_token": api_token}