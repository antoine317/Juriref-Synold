#Extraction de 500 lignes au hasard pour me faire une idée des données


import json
import random
from pathlib import Path

# Config
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_FILE = DATA_DIR / "processed" / "corpus_brut.jsonl"
OUTPUT_FILE = DATA_DIR / "processed" / "500lignes.jsonl"

def sample_data(total_target=500):
    jorf_lines = []
    code_lines = []
        
    # Lecture optimisée pour ne pas tout charger 
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            # Petit filtre : on ne garde que les phrases assez longues pour être intéressantes
            if len(entry['text']) > 50: 
                if entry['meta']['type'] == 'JORF':
                    jorf_lines.append(entry)
                else:
                    code_lines.append(entry)
    
    print(f" il y a : {len(jorf_lines)} JORF, {len(code_lines)} CODES")
    
    target_per_type = total_target // 2
    
    selected = random.sample(jorf_lines, target_per_type) + \
               random.sample(code_lines, target_per_type)
    
    # Mélange final
    random.shuffle(selected)
    
    # Sauvegarde
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for entry in selected:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Fichier {OUTPUT_FILE} de {len(selected)} lignes.")

if __name__ == "__main__":
    sample_data()