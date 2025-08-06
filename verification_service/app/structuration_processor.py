import sys
import json
import requests
import re
from datetime import datetime
import pytz
import os 


OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
# --------------------------------------------------------------------------------
# 1. FONCTION DE STRUCTURATION (Ollama - inchangée)
# --------------------------------------------------------------------------------
def structure_ocr_text(raw_text: str, model_name: str = "llama3") -> dict:
    prompt = f"""
Tu es un assistant expert en extraction d'informations à partir de documents d'identité.
La tâche consiste à analyser le texte OCR suivant, extrait d'une Carte Nationale d'Identité marocaine,
et à le structurer dans un format JSON précis.

Voici le texte extrait par l'OCR :
--- OCR TEXT START ---
{raw_text}
--- OCR TEXT END ---

Instructions pour la structuration JSON :
1.  Extrais les informations suivantes et retourne-les dans un objet JSON.
2.  Les clés JSON doivent être exactement comme spécifié ci-dessous. N'ajoute aucune autre clé.
3.  Assure-toi qu'il n'y a pas de clés dupliquées dans le JSON.
4.  Si une information n'est pas présente ou ne peut pas être clairement identifiée dans le texte OCR, utilise la valeur `null` ou une chaîne vide "" pour le champ correspondant.
5.  Les dates doivent être au format "JJ/MM/AAAA".
6.  Le champ "nom" correspond au nom de famille.
7.  Le champ "prenom" correspond au(x) prénom(s).
8.  Le champ "numero_cin" peut parfois avoir des lettres avant les chiffres (ex: "U123456", "FA186965") ou être un numéro comme "CAN 123457". Essaie de capturer le numéro d'identification principal.

Format JSON attendu :
{{
    "pays": "ROYAUME DU MAROC",
    "document_type": "CARTE NATIONALE D'IDENTITE",
    "nom": "string",
    "prenom": "string",
    "date_naissance": "JJ/MM/AAAA",
    "lieu_naissance": "string",
    "numero_cin": "string",
    "date_validite": "JJ/MM/AAAA"
}}

Maintenant, analyse le texte OCR fourni ci-dessus et génère l'objet JSON correspondant.
Assure-toi que ta réponse est UNIQUEMENT l'objet JSON, sans texte explicatif avant ou après.
""".strip()
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 1024},
        "format": "json"
    }
    try:
        response = requests.post(url, json=payload)
        #Envoie la requête HTTP POST à Ollama en local.
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Erreur de connexion à Ollama : {e}")

    try:
        generated_data = response.json()
        json_str = generated_data.get("response", "")
        #Récupère la réponse textuelle, extrait l'objet JSON brut.

        if not json_str.strip().startswith("{"):
            start = json_str.find("{")
            end = json_str.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError(f"Aucun JSON valide trouvé dans la réponse d'Ollama :\n{json_str}")
            json_str = json_str[start:end]
        
        parsed_json = json.loads(json_str)
        #Convertit le JSON en dictionnaire Python.

        expected_keys = {"pays", "document_type", "nom", "prenom", "date_naissance", "lieu_naissance", "numero_cin", "date_validite"}
        missing_keys = expected_keys - parsed_json.keys()
        for key in missing_keys:
            parsed_json[key] = ""
        return parsed_json
        #Ajoute les champs manquants avec "" pour éviter des erreurs plus tard.

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Erreur de décodage JSON de la réponse Ollama : {e}\nRéponse reçue : {json_str}")
    except ValueError as e:
        raise RuntimeError(str(e))
# --------------------------------------------------------------------------------
# 2. FONCTION D’EXTRACTION DU MRZ TD1 (3x30) À PARTIR DU TEXTE VERSO
# --------------------------------------------------------------------------------
def extract_mrz_td1_from_text(verso_text: str) -> tuple[str | None, str | None, str | None]:
    lines = verso_text.splitlines()
    #Découpe le texte en lignes.

    cleaned_lines = []
    for line in lines:
        cleaned = re.sub(r"[^A-Z0-9<]", "", line.upper())
        #Nettoie chaque ligne pour ne garder que lettres majuscules, chiffres et chevrons.
        if len(cleaned) > 25 : 
            cleaned_lines.append(cleaned)

    if not cleaned_lines:
        return None, None, None

    mrz_l1, mrz_l2, mrz_l3 = None, None, None
    
    for i, cl_line1_candidate in enumerate(cleaned_lines):
        match_l1 = re.search(r"^(I<MAR[A-Z0-9<]{25})$", cl_line1_candidate[:30])
        #Cherche des lignes correspondant au format MRZ TD1 (3 lignes de 30 caractères).

        if match_l1:
            potential_l1 = match_l1.group(1).ljust(30, '<')
            if i + 1 < len(cleaned_lines):
                cl_line2_candidate = cleaned_lines[i+1]
                match_l2 = re.search(r"^([0-9<]{6}[A-Z0-9<][A-Z0-9<][0-9<]{6}[A-Z0-9<][A-Z<]{3}[A-Z0-9<]{0,11}[A-Z0-9<])$", cl_line2_candidate[:30])
                if match_l2:
                    potential_l2 = match_l2.group(1).ljust(30, '<')
                    if i + 2 < len(cleaned_lines):
                        cl_line3_candidate = cleaned_lines[i+2]
                        if "<<" in cl_line3_candidate and len(cl_line3_candidate) >=28 : 
                             potential_l3 = cl_line3_candidate[:30].ljust(30, '<')
                             mrz_l1 = potential_l1
                             mrz_l2 = potential_l2
                             mrz_l3 = potential_l3
                             return mrz_l1, mrz_l2, mrz_l3
    return None, None, None


# --------------------------------------------------------------------------------
# 3. VALIDATION SANS MRZ (recto seul)
# --------------------------------------------------------------------------------
def validate_without_mrz(structured: dict) -> dict:
    erreurs = []
    #Chaque erreur est ajoutée à une liste erreurs. c'est pour ca on cree une liste des erreurs 
    tz = pytz.timezone("Africa/Casablanca") 
    #fixer le temps selon la région 
    today = datetime.now(tz).date()
    #fixer la date d'aujourd'hui 

    pays_val = (structured.get("pays") or "").strip().upper()
    if pays_val != "ROYAUME DU MAROC":
        erreurs.append(f"Champ 'pays' invalide : « {structured.get('pays')} ».")
    doc_type_val = (structured.get("document_type") or "").strip().upper()
    if not ("CARTE" in doc_type_val and "NATIONALE" in doc_type_val and "IDENTITE" in doc_type_val):
        erreurs.append(f"Champ 'document_type' invalide : « {structured.get('document_type')} ».")
    
    nom_val = (structured.get("nom") or "").strip()
    if not nom_val: erreurs.append("Champ 'nom' est vide.")
    else:
        mots_nom = nom_val.split()
        if not (1 <= len(mots_nom) <= 4): 
            erreurs.append(f"Nom « {nom_val} » doit contenir 1 à 4 mots.")
        for m in mots_nom:
            if len(m) < 2 and len(nom_val) > 1: erreurs.append(f"Mot « {m} » du nom trop court.")
            if re.search(r"\d", m): erreurs.append(f"Nom « {nom_val} » contient un chiffre non autorisé.")
    
    prenom_val = (structured.get("prenom") or "").strip()
    if not prenom_val: erreurs.append("Champ 'prenom' est vide.")
    else:
        mots_prenom = prenom_val.split()
        if not (1 <= len(mots_prenom) <= 4): 
            erreurs.append(f"Prénom « {prenom_val} » doit contenir 1 à 4 mots.")
        for m in mots_prenom:
            if len(m) < 2 and len(prenom_val) > 1: erreurs.append(f"Mot « {m} » du prénom trop court.")
            if re.search(r"\d", m): erreurs.append(f"Prénom « {prenom_val} » contient un chiffre non autorisé.")
    
    date_naiss_str = (structured.get("date_naissance") or "").strip()
    try:
        d_naiss = datetime.strptime(date_naiss_str, "%d/%m/%Y").date()
        if d_naiss >= today: erreurs.append(f"Date de naissance ({date_naiss_str}) future.")
        if (today - d_naiss).days > 120 * 365.25: erreurs.append(f"Date de naissance ({date_naiss_str}) suspecte (> 120 ans).")
        # if (today - d_naiss).days < 16 * 365.25: erreurs.append(f"Date de naissance ({date_naiss_str}) suspecte (< 16 ans pour CNI).") # Optionnel
    except ValueError: erreurs.append(f"Date de naissance « {date_naiss_str} » mal formatée (attendu JJ/MM/AAAA).")
    
    lieu_val = (structured.get("lieu_naissance") or "").strip()
    if not lieu_val: erreurs.append("Champ 'lieu_naissance' est vide.")
    elif re.search(r"\d", lieu_val) and not re.search(r"\d{1,2}(ER|EME|ARRONDISSEMENT)", lieu_val.upper()):
        erreurs.append(f"Lieu naissance « {lieu_val} » contient des chiffres non justifiés.")
    
    cin_val = (structured.get("numero_cin") or "").strip().replace(" ", "").upper()
    if not cin_val:
        erreurs.append("Champ 'numero_cin' est vide.")
    elif not re.fullmatch(r"[A-Z]{1,2}\d{5,8}", cin_val) and not re.fullmatch(r"CAN\d{6,8}", cin_val):
        erreurs.append(f"Format 'numero_cin' « {cin_val} » invalide.")
    
    date_valid_str = (structured.get("date_validite") or "").strip()
    if not date_valid_str:
        erreurs.append("Champ 'date_validite' est vide.")
    else:
        try:
            d_valid = datetime.strptime(date_valid_str, "%d/%m/%Y").date()
            if d_valid < today: 
                erreurs.append(f"Date de validité ({date_valid_str}) dépassée.")
        except ValueError: 
            erreurs.append(f"Date de validité « {date_valid_str} » mal formatée (attendu JJ/MM/AAAA).")

    if erreurs: return {"status": "NON_VALIDÉ", "erreurs": erreurs}
    return {"status": "VALIDÉ", "erreurs": []}

# --------------------------------------------------------------------------------
# 4. FONCTIONS UTILITAIRES MRZ (inchangées)
# --------------------------------------------------------------------------------
def char_value_mrz(c):
    if '0' <= c <= '9': return int(c)
    if 'A' <= c <= 'Z': return ord(c) - ord('A') + 10 #Cela repose sur le code ASCII : ord('A') = 65, donc ord(c) - 65 + 10.
    if c == '<': return 0
    raise ValueError(f"Caractère MRZ invalide '{c}' pour calcul checksum.")
#char_value_mrz : convertit un caractère MRZ en valeur numérique pour le checksum.
####Cette fonction prend un caractère unique c extrait d'une ligne MRZ (Machine Readable Zone).
####Elle retourne sa valeur numérique, utilisée ensuite dans le calcul du checksum

def compute_mrz_checksum(seq: str) -> str | None:
    try:
        weights = [7, 3, 1]
        total = sum(char_value_mrz(ch) * weights[i % 3] for i, ch in enumerate(seq))
        return str(total % 10)
    except ValueError:
        return None
#compute_mrz_checksum : applique les poids [7, 3, 1] sur les caractères MRZ pour calculer le checksum (modulo 10).
####Pour chaque caractère ch à la position i dans la séquence seq :
####On le convertit en valeur numérique via char_value_mrz(ch)
#####On le multiplie par son poids correspondant : weights[i % 3]
#####On additionne tous les résultats avec sum(...).


# --------------------------------------------------------------------------------
# 5. NOUVELLE FONCTION DE VÉRIFICATION MRZ (Format et Match - MODIFIÉE pour Nom/Prénom)
# --------------------------------------------------------------------------------
def check_new_cni_mrz_validity(structured_recto: dict, mrz_l1: str, mrz_l2: str, mrz_l3: str) -> tuple[list, list]:
## cette fonction compare les champs OCR avec les infos extraites du MRZ (3 lignes)
    errors_mrz_format = []
    errors_recto_mrz_match = []

    if len(mrz_l1) != 30: errors_mrz_format.append(f"MRZ Ligne 1 longueur != 30 (est {len(mrz_l1)}).")
    if len(mrz_l2) != 30: errors_mrz_format.append(f"MRZ Ligne 2 longueur != 30 (est {len(mrz_l2)}).")
    if len(mrz_l3) != 30: errors_mrz_format.append(f"MRZ Ligne 3 longueur != 30 (est {len(mrz_l3)}).")

    if errors_mrz_format: 
        return errors_mrz_format, errors_recto_mrz_match 

    # --- A. Vérification du format du MRZ ---
    doc_num_mrz1_part1 = mrz_l1[5:14]
    chk_doc_num_mrz1   = mrz_l1[14]
    if not chk_doc_num_mrz1.isdigit() and chk_doc_num_mrz1 != '<':
        errors_mrz_format.append(f"MRZ L1: Caractère Checksum Num Doc ('{chk_doc_num_mrz1}') n'est pas un chiffre valide.")
    else:
        calculated_chk = compute_mrz_checksum(doc_num_mrz1_part1)
        if calculated_chk is None: errors_mrz_format.append(f"MRZ L1: Caractères invalides dans séquence numéro doc '{doc_num_mrz1_part1}' pour checksum.")
        elif calculated_chk != chk_doc_num_mrz1:
            errors_mrz_format.append(f"MRZ L1: Checksum numéro doc ('{doc_num_mrz1_part1}' -> '{chk_doc_num_mrz1}') incorrect (attendu: {calculated_chk}).")

    dob_mrz2_str    = mrz_l2[0:6]
    chk_dob_mrz2    = mrz_l2[6]
    sex_mrz2        = mrz_l2[7]
    exp_date_mrz2_str = mrz_l2[8:14]
    chk_exp_date_mrz2 = mrz_l2[14]
    nationality_mrz2 = mrz_l2[15:18]

    if not chk_dob_mrz2.isdigit() and chk_dob_mrz2 != '<':
        errors_mrz_format.append(f"MRZ L2: Caractère Checksum Date Naissance ('{chk_dob_mrz2}') n'est pas un chiffre valide.")
    else:
        calculated_chk = compute_mrz_checksum(dob_mrz2_str)
        if calculated_chk is None: errors_mrz_format.append(f"MRZ L2: Caractères invalides dans date naissance '{dob_mrz2_str}' pour checksum.")
        elif calculated_chk != chk_dob_mrz2:
            errors_mrz_format.append(f"MRZ L2: Checksum date naissance ('{dob_mrz2_str}' -> '{chk_dob_mrz2}') incorrect (attendu: {calculated_chk}).")

    if sex_mrz2 not in ['M', 'F', 'X', '<']:
        errors_mrz_format.append(f"MRZ L2: Sexe ('{sex_mrz2}') invalide. Attendu M, F, ou <.")

    if not chk_exp_date_mrz2.isdigit() and chk_exp_date_mrz2 != '<':
        errors_mrz_format.append(f"MRZ L2: Caractère Checksum Date Expiration ('{chk_exp_date_mrz2}') n'est pas un chiffre valide.")
    else:
        calculated_chk = compute_mrz_checksum(exp_date_mrz2_str)
        if calculated_chk is None: errors_mrz_format.append(f"MRZ L2: Caractères invalides dans date expiration '{exp_date_mrz2_str}' pour checksum.")
        elif calculated_chk != chk_exp_date_mrz2:
            errors_mrz_format.append(f"MRZ L2: Checksum date expiration ('{exp_date_mrz2_str}' -> '{chk_exp_date_mrz2}') incorrect (attendu: {calculated_chk}).")
    
    if nationality_mrz2 != "MAR":
        errors_mrz_format.append(f"MRZ L2: Nationalité incorrecte ('{nationality_mrz2}', attendu 'MAR').")

    if "<<" not in mrz_l3:
        errors_mrz_format.append(f"MRZ L3: Séparateur '<<' pour nom/prénom manquant.")

    # --- B. Vérification de la correspondance Recto vs MRZ (toujours tentée pour information) ---
    date_naiss_ocr_str = (structured_recto.get("date_naissance") or "").strip()
    try:
        d_naiss_ocr = datetime.strptime(date_naiss_ocr_str, "%d/%m/%Y").date()
        if not re.fullmatch(r"[0-9<]{6}", dob_mrz2_str):
             errors_recto_mrz_match.append(f"Format date naissance MRZ ('{dob_mrz2_str}') incorrect pour comparaison.")
        elif dob_mrz2_str.count('<') == 0 and dob_mrz2_str != d_naiss_ocr.strftime("%y%m%d"):
            errors_recto_mrz_match.append(f"Discordance Date Naissance: OCR ('{d_naiss_ocr.strftime('%y%m%d')}') vs MRZ ('{dob_mrz2_str}').")
    except ValueError: errors_recto_mrz_match.append(f"Format OCR Date Naissance ('{date_naiss_ocr_str}') invalide pour comparaison MRZ.")

    date_valid_ocr_str = (structured_recto.get("date_validite") or "").strip()
    try:
        d_valid_ocr = datetime.strptime(date_valid_ocr_str, "%d/%m/%Y").date()
        if not re.fullmatch(r"[0-9<]{6}", exp_date_mrz2_str):
             errors_recto_mrz_match.append(f"Format date expiration MRZ ('{exp_date_mrz2_str}') incorrect pour comparaison.")
        elif exp_date_mrz2_str.count('<') == 0 and exp_date_mrz2_str != d_valid_ocr.strftime("%y%m%d"):
            errors_recto_mrz_match.append(f"Discordance Date Validité: OCR ('{d_valid_ocr.strftime('%y%m%d')}') vs MRZ ('{exp_date_mrz2_str}').")
    except ValueError: errors_recto_mrz_match.append(f"Format OCR Date Validité ('{date_valid_ocr_str}') invalide pour comparaison MRZ.")

    cin_ocr = (structured_recto.get("numero_cin") or "").strip().replace(" ", "").upper()
    cin_ocr_alphanum = "".join(filter(str.isalnum, cin_ocr))
    
    mrz_doc_num_part1_cleaned = mrz_l1[5:14].replace("<", "")
    mrz_doc_num_part2_optional_cleaned = mrz_l1[15:29].replace("<", "")

    if cin_ocr_alphanum:
        found_cin_in_mrz = False
        if cin_ocr_alphanum == mrz_doc_num_part1_cleaned or cin_ocr_alphanum == mrz_doc_num_part2_optional_cleaned:
            found_cin_in_mrz = True
        if not found_cin_in_mrz:
             errors_recto_mrz_match.append(f"Discordance Numero CIN: OCR ('{cin_ocr_alphanum}') non trouvé tel quel dans MRZ L1 partie doc ('{mrz_doc_num_part1_cleaned}') ou optionnelle ('{mrz_doc_num_part2_optional_cleaned}').")
    elif structured_recto.get("numero_cin") is not None:
        errors_recto_mrz_match.append("Numero CIN de l'OCR vide pour comparaison MRZ alors que le champ existe.")

    # MODIFICATION ICI POUR NOM ET PRÉNOM
    # Recto:
    nom_ocr_recto_raw = (structured_recto.get("nom") or "").strip().upper()
    prenom_ocr_recto_raw = (structured_recto.get("prenom") or "").strip().upper()

    # MRZ:
    mrz3_parts = mrz_l3.split("<<", 1)
    mrz_nom_part_raw = mrz3_parts[0] 
    mrz_prenom_part_raw_full = mrz3_parts[1] if len(mrz3_parts) > 1 else ""
    
    # Normalisation du Nom:
    nom_ocr_normalized = nom_ocr_recto_raw.replace(" ", "")
    mrz_nom_normalized = mrz_nom_part_raw.replace("<", "")

    if nom_ocr_normalized != mrz_nom_normalized:
        # Ajout des valeurs originales pour faciliter le débogage de l'erreur
        errors_recto_mrz_match.append(f"Discordance Nom: OCR normalisé ('{nom_ocr_normalized}') vs MRZ normalisé ('{mrz_nom_normalized}'). (Original OCR: '{nom_ocr_recto_raw}', Original MRZ part: '{mrz_nom_part_raw}')")
    
    # Normalisation du Prénom (stratégie: enlever tous les espaces/chevrons)
    prenom_ocr_normalized = prenom_ocr_recto_raw.replace(" ", "")
    # Pour le MRZ, on prend toute la partie prénom et on enlève les chevrons.
    # Cela gère les cas comme "PRENOM1<PRENOM2" qui deviendront "PRENOM1PRENOM2"
    mrz_prenom_normalized = mrz_prenom_part_raw_full.replace("<", "")

    if prenom_ocr_normalized != mrz_prenom_normalized:
        errors_recto_mrz_match.append(f"Discordance Prénom: OCR normalisé ('{prenom_ocr_normalized}') vs MRZ normalisé ('{mrz_prenom_normalized}'). (Original OCR: '{prenom_ocr_recto_raw}', Original MRZ part: '{mrz_prenom_part_raw_full}')")

    return errors_mrz_format, errors_recto_mrz_match

# --------------------------------------------------------------------------------
# 6. MAIN (Logique de décision refondue)
# --------------------------------------------------------------------------------
def process_structuration(recto_text: str, verso_text: str) -> dict:
    recto_block = recto_text.strip()
    verso_block = verso_text.strip()

    if not recto_block:
        raise ValueError("Section RECTO vide.")

    structured_recto = structure_ocr_text(recto_block)
    recto_validation_result = validate_without_mrz(structured_recto)
    recto_intrinsic_errors = recto_validation_result.get("erreurs", [])
    is_recto_intrinsically_valid = not recto_intrinsic_errors

    mrz_l1, mrz_l2, mrz_l3 = None, None, None
    final_report = {
        "card_type": None,
        "status_validation": None,
        "reason_for_status": None,
        "recto_data": structured_recto, 
        "mrz_data_detected_raw": None,
        "errors_details": {
            "recto_intrinsic": recto_intrinsic_errors,
            "mrz_format": [],
            "recto_mrz_match": []
        }
    }

    if verso_block:
        mrz_l1, mrz_l2, mrz_l3 = extract_mrz_td1_from_text(verso_block)

    if mrz_l1 and mrz_l2 and mrz_l3:
        final_report["card_type"] = "NOUVELLE_CNI_DETECTEE"
        final_report["mrz_data_detected_raw"] = {"l1": mrz_l1, "l2": mrz_l2, "l3": mrz_l3}
        structured_recto["mrz_line1_detected"] = mrz_l1
        structured_recto["mrz_line2_detected"] = mrz_l2
        structured_recto["mrz_line3_detected"] = mrz_l3

        errors_mrz_format, errors_recto_mrz_match = check_new_cni_mrz_validity(structured_recto, mrz_l1, mrz_l2, mrz_l3)
        final_report["errors_details"]["mrz_format"] = errors_mrz_format
        final_report["errors_details"]["recto_mrz_match"] = errors_recto_mrz_match
        
        is_mrz_format_valid = not errors_mrz_format
        is_recto_mrz_match_valid = not errors_recto_mrz_match

        if not is_recto_intrinsically_valid:
            final_report["status_validation"] = "NON_VALIDÉ"
            final_report["reason_for_status"] = "RECTO_DONNÉES_INVALIDE"
        elif not is_mrz_format_valid:
            final_report["status_validation"] = "NON_VALIDÉ"
            final_report["reason_for_status"] = "MRZ_FORMAT_INVALIDE"
        elif not is_recto_mrz_match_valid:
            final_report["status_validation"] = "NON_VALIDÉ"
            final_report["reason_for_status"] = "DISCORDANCE_RECTO_MRZ"
        else: 
            final_report["status_validation"] = "VALIDÉ"
            final_report["reason_for_status"] = "NOUVELLE_CNI_CONFORME_ET_COHÉRENTE"
            
    else:
        final_report["card_type"] = "ANCIENNE_CNI_OU_MRZ_NON_DETECTE"
        if is_recto_intrinsically_valid:
            final_report["status_validation"] = "VALIDÉ"
            final_report["reason_for_status"] = "ANCIENNE_CNI_RECTO_CONFORME"
        else:
            final_report["status_validation"] = "NON_VALIDÉ"
            final_report["reason_for_status"] = "ANCIENNE_CNI_RECTO_DONNÉES_INVALIDE"

    return final_report

if __name__ == "__main__":
    process_structuration()