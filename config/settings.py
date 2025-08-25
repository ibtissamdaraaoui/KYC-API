import os
from pathlib import Path
from dotenv import load_dotenv

def load_project_env():
    """
    Localise et charge le fichier .env de la racine du projet.

    Cette fonction remonte l'arborescence des fichiers à partir de ce
    module pour trouver un fichier nommé '.env' et le charge.
    """
    # Chemin vers le fichier actuel (config/settings.py)
    current_path = Path(__file__).resolve()
    
    # Remonter jusqu'à la racine du projet (qui contient le .env)
    # Dans notre cas, la racine est le parent du dossier 'config'
    project_root = current_path.parent.parent
    
    # Chemin complet vers le fichier .env
    env_path = project_root / ".env"

    if env_path.exists():
        print(f"✅ Chargement de la configuration depuis : {env_path}")
        load_dotenv(dotenv_path=env_path)
    else:
        print(f"⚠️  Attention : Fichier .env non trouvé à {env_path}. Utilisation des variables d'environnement système.")

# Appeler la fonction au moment où ce module est importé
load_project_env()

# Vous pouvez aussi définir ici des variables globales si vous le souhaitez,
# mais pour l'instant, on se contente de charger l'environnement.
# Par exemple :
# DATABASE_URL = os.getenv("DATABASE_URL")
# if not DATABASE_URL:
#    raise ValueError("DATABASE_URL n'est pas défini !")