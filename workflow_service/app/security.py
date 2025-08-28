# Fichier: workflow_service/app/security.py
import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Le secret global est une clé de secours ou pour des usages internes
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer()

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, secret_key: str):
    """Crée un token JWT signé avec le secret spécifique du client."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    # 'iss' (issuer) DOIT être l'application_id pour que Kong identifie le Consumer
    to_encode.update({"exp": expire, "iss": data.get("sub")})
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)

def get_current_client_id(request: Request) -> str:
    """
    Dépendance FastAPI pour protéger une route.
    Elle lit l'en-tête X-Consumer-Username ajouté par Kong APRES qu'il ait
    validé le JWT. C'est la méthode la plus sûre et performante.
    """
    client_id = request.headers.get("X-Consumer-Username")
    if not client_id:
        raise HTTPException(
            status_code=401,
            detail="En-tête de consommateur Kong non trouvé. Le plugin JWT est-il activé sur la route ?"
        )
    return client_id