#Ce fichier a converti les csv et markdown dans un unique fichier jsonl pour homgénéiser les formats

import os
import json
import re
import pandas as pd
from pathlib import Path

# Configuration des directions
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == 'src' else BASE_DIR
DATA_DIR = PROJECT_ROOT / "data"
RAW_JORF_DIR = DATA_DIR / "jorf_2023_1990"
RAW_CODES_DIR = DATA_DIR / "codes"
OUTPUT_FILE = DATA_DIR / "processed" / "corpus_brut.jsonl"

def clean_text(text):
    if not isinstance(text, str): return ""
    text = text.replace('\xa0', ' ').strip()
    return re.sub(r'\s+', ' ', text)

def stream_jorf_file(filepath):
    """Générateur pour lire les JORF ligne par ligne """
    try:
        # On utilise chunksize pour ne charger que 5000 lignes à la fois car ma ram saturait
        with pd.read_csv(filepath, sep='|', header=None, on_bad_lines='skip', 
                         engine='python', encoding='utf-8', chunksize=5000) as reader:
            for chunk in reader:
                for _, row in chunk.iterrows():
                    text_content = row.iloc[5] if len(row) > 5 else row.iloc[-1]
                    if isinstance(text_content, str) and len(text_content) > 30:
                        yield {
                            "text": clean_text(text_content),
                            "meta": {"source": filepath.name, "type": "JORF"}
                        }


def stream_code_file(filepath):
    """Générateur pour les fichiers Codes."""
    current_article = "Inconnu"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('**Art.'):
                    current_article = line.replace('**', '').strip()
                elif len(line) > 30 and not line.startswith('#'):
                    yield {
                        "text": clean_text(line),
                        "meta": {"source": filepath.name, "type": "CODE", "context": current_article}
                    }


def main():
    if not DATA_DIR.exists():
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    # On ouvre le fichier de sortie une seule fois en mode écriture
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        
        # 1. Traitement JORF
        jorf_files = list(RAW_JORF_DIR.glob("*.csv"))
        print(f"Traitement de {len(jorf_files)} fichiers JORF ")
        for f_path in jorf_files:
            for entry in stream_jorf_file(f_path):
                out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                count += 1
            print(f"vérif intermédiaire")

        # 2. Traitement CODES
        code_files = list(RAW_CODES_DIR.glob("*.md"))
        print(f"Traitement de {len(code_files)} fichiers CODES ")
        for f_path in code_files:
            for entry in stream_code_file(f_path):
                out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                count += 1

    print(f"Total lignes : {count}")

if __name__ == "__main__":
    main()