import re
import os
import json
import pandas as pd

def generate_robust_dataset(data_folder):
    dataset = []
    
    # 1. Regex Articles : Capte L.123, R123, L*123 ou 123 (quand précédé de Art.)
    # On autorise les astérisques facultatifs autour pour le Markdown
    re_art = r"Art\.\s+([\*]*[L|R|D]?[\*]?[\s]*\d+[\-\d+]*)[\*]*"
    
    # 2. Regex Lois (pour le JORF) : Capte "loi n° 92-1376" ou "loi du 30 décembre 1992"
    re_loi = r"(loi\s+n°\s+[\d\-]+|loi\s+du\s+\d+\s+\w+\s+\d{4})"

    
    # On utilise os.walk pour descendre dans les sous-dossiers codes/ et jorf/
    for root, dirs, files in os.walk(data_folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            
            # --- TRAITEMENT DES CODES (MARKDOWN) ---
            if filename.endswith(".md"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # On découpe par paragraphe
                for para in content.split('\n\n'):
                    clean_para = para.replace('\n', ' ').strip()
                    if not clean_para: continue
                    
                    entities = []
                    for match in re.finditer(re_art, clean_para):
                        # On récupère le groupe 1 (le numéro pur)
                        entities.append([match.start(1), match.end(1), "ID_ART"])
                    
                    if entities:
                        dataset.append([clean_para[:1000], {"entities": entities}])

            # --- TRAITEMENT DU JORF (CSV) ---
            elif filename.endswith(".csv"):
                try:
                    # On lit le CSV avec le délimiteur '|' (vu dans tes fichiers)
                    df = pd.read_csv(file_path, sep='|', header=None, on_bad_lines='skip')
                    # On analyse la colonne qui contient le texte (souvent l'index 5 ou 6)
                    for text in df.iloc[:, -1].dropna().astype(str):
                        entities = []
                        # On cherche les lois dans le JORF
                        for match in re.finditer(re_loi, text, re.IGNORECASE):
                            entities.append([match.start(), match.end(), "ID_LOI"])
                        
                        if entities:
                            dataset.append([text[:1000], {"entities": entities}])
    

    return dataset

if __name__ == "__main__":
    DATA_PATH = "data"
    final_data = generate_robust_dataset(DATA_PATH)
    
    with open("training_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
