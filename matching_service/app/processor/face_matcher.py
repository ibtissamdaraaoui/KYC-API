# Fichier: matching_service/app/processor/face_matcher.py

import cv2
import numpy as np
from deepface import DeepFace
from typing import Dict, Optional

# --- (Fonction utilitaire _bytes_to_cv2_image inchangée) ---

def extract_face_from_image(image_bytes: bytes, detector_backend: str = "mtcnn") -> Optional[bytes]:
    """Détecte le visage principal, le recadre et le retourne en bytes."""
    
    print(f"   - [Face Extractor] Démarrage de l'extraction de visage avec le backend '{detector_backend}'...")
    
    image = _bytes_to_cv2_image(image_bytes)
    if image is None:
        print("   - [Face Extractor] ❌ ERREUR: Impossible de décoder l'image source.")
        return None

    try:
        print("   - [Face Extractor] -> Appel à DeepFace.extract_faces...")
        extracted_faces = DeepFace.extract_faces(
            img_path=image,
            detector_backend=detector_backend,
            enforce_detection=True
        )
        
        print(f"   - [Face Extractor] -> DeepFace a trouvé {len(extracted_faces)} visage(s). Traitement du premier.")
        face_image_np = (extracted_faces[0]['face'] * 255).astype(np.uint8)
        face_image_bgr = cv2.cvtColor(face_image_np, cv2.COLOR_RGB2BGR)
        
        is_success, buffer = cv2.imencode(".jpg", face_image_bgr)
        if not is_success:
            print("   - [Face Extractor] ❌ ERREUR: Échec de l'encodage de l'image du visage.")
            return None
        
        print(f"   - [Face Extractor] ✅ SUCCÈS : Visage extrait ({len(buffer.tobytes())} bytes).")
        return buffer.tobytes()

    except ValueError:
        print(f"   - [Face Extractor] 🟡 AVERTISSEMENT: Aucun visage n'a été détecté par '{detector_backend}'.")
        return None
    except Exception as e:
        print(f"   - [Face Extractor] ❌ ERREUR inattendue lors de l'extraction: {e}")
        return None

def verify_faces(img1_bytes: bytes, img2_bytes: bytes) -> Dict:
    """Effectue la comparaison faciale entre deux images en bytes."""
    
    print("   - [Face Matcher] Démarrage de la comparaison faciale (Selfie vs Visage Extrait)...")

    img1 = _bytes_to_cv2_image(img1_bytes) # Visage extrait
    img2 = _bytes_to_cv2_image(img2_bytes) # Selfie complet
    
    if img1 is None or img2 is None:
        print("   - [Face Matcher] ❌ ERREUR: Impossible de décoder une des images pour la comparaison.")
        return {"verified": False, "error": "Erreur de décodage d'image."}

    try:
        print("   - [Face Matcher] -> Appel à DeepFace.verify (Modèle: VGG-Face, Détecteur: mtcnn)...")
        result = DeepFace.verify(
            img1_path=img1,
            img2_path=img2,
            model_name="VGG-Face",
            detector_backend="mtcnn",
            enforce_detection=True # Force la détection sur les deux images
        )
        print(f"   - [Face Matcher] ✅ SUCCÈS : Résultat DeepFace obtenu.")
        # Ajout d'un log très clair sur le verdict
        print(f"   - [Face Matcher] -> Verdict: {'MATCH' if result['verified'] else 'NO MATCH'} | Distance: {result['distance']:.4f} | Seuil: {result['threshold']}")
        return result

    except Exception as e:
        print(f"   - [Face Matcher] ❌ ERREUR lors de la comparaison: {e}")
        return {"verified": False, "distance": 999.0, "error": str(e)}

# --- (Fonction utilitaire _bytes_to_cv2_image à ajouter si elle n'est pas déjà là) ---
def _bytes_to_cv2_image(image_bytes: bytes) -> Optional[np.ndarray]:
    try:
        image_np = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        return image
    except Exception:
        return None