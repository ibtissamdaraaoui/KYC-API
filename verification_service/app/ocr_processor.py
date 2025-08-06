import cv2
import easyocr
import numpy as np

# Seuil minimal de confiance pour accepter un texte détecté
CONF_THRESHOLD = 0.20
TARGET_WIDTH = 1200

# Initialiser EasyOCR une seule fois pour performance
reader = easyocr.Reader(['fr'], gpu=False)

def run_ocr_on_image_bytes(image_bytes: bytes) -> list[str]:
    """
    Reçoit les données binaires d'une image, effectue OCR après traitement couleur.
    Retourne une liste de lignes détectées avec une confiance >= seuil.
    """
    # Décoder les bytes en tableau d’image OpenCV (couleur)
    image_np = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Impossible de décoder l'image pour l'OCR.")

    # Redimensionner si nécessaire
    h, w = img.shape[:2]
    if w < TARGET_WIDTH:
        scale = TARGET_WIDTH / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # Convertir en RGB pour EasyOCR
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Lancer EasyOCR
    results = reader.readtext(img_rgb)

    # Retourner uniquement les textes avec une confiance suffisante
    return [text for (_, text, conf) in results if conf >= CONF_THRESHOLD]
