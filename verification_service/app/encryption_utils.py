# Fichier: /verification_service/app/encryption_utils.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# On récupère la clé "maîtresse" depuis l'environnement.
# C'est un mot de passe, pas directement la clé de chiffrement.
ENCRYPTION_PASSWORD = os.getenv("DB_DATA_ENCRYPTION_KEY")
if not ENCRYPTION_PASSWORD:
    raise ValueError("La clé de chiffrement DB_DATA_ENCRYPTION_KEY n'est pas définie dans le .env !")

# Le "sel" doit être fixe et stocké avec le code. Ne le changez jamais.
SALT = b'kyc_salt_for_db_data_encryption'

def _get_fernet_key() -> bytes:
    """Génère une clé de chiffrement stable à partir du mot de passe de l'environnement."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
        backend=default_backend()
    )
    # On encode la clé de l'env pour la transformer en bytes
    key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_PASSWORD.encode()))
    return key

# On crée une instance Fernet une seule fois pour la réutiliser.
_fernet = Fernet(_get_fernet_key())

def encrypt_data(data: str) -> str:
    """Chiffre une chaîne de caractères et la retourne en format base64."""
    if not data:
        return data
    encrypted_bytes = _fernet.encrypt(data.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_data(encrypted_data: str) -> str:
    """Déchiffre une chaîne de caractères depuis le format base64."""
    if not encrypted_data:
        return encrypted_data
    decrypted_bytes = _fernet.decrypt(encrypted_data.encode('utf-8'))
    return decrypted_bytes.decode('utf-8')