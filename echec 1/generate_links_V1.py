import spacy
import os
from pathlib import Path

nlp = spacy.load("./output/model-best")



def process_text(text):
    # pour la RAM
    CHUNK_SIZE = 500000 
    
    # Si le texte est court, on traite normalement
    if len(text) < CHUNK_SIZE:
        return _apply_model_to_chunk(text)
    
    # Sinon, on découpe par paragraphes pour ne pas couper une phrase au milieu
    chunks = text.split('\n\n')
    processed_chunks = []
    
    current_chunk = ""
    for p in chunks:
        if len(current_chunk) + len(p) < CHUNK_SIZE:
            current_chunk += p + '\n\n'
        else:
            processed_chunks.append(_apply_model_to_chunk(current_chunk))
            current_chunk = p + '\n\n'
    
    # On traite le dernier morceau
    if current_chunk:
        processed_chunks.append(_apply_model_to_chunk(current_chunk))
        
    return "".join(processed_chunks)

def _apply_model_to_chunk(text):
    doc = nlp(text)
    if not doc.ents:
        return text

    entities = sorted(doc.ents, key=lambda x: x.start_char, reverse=True)
    result = text
    for ent in entities:
        start, end = ent.start_char, ent.end_char
        label = ent.label_
        val = ent.text.strip()
        clean_val = val.replace(" ", "").replace(".", "").replace("*", "")

        if label == "ID_ART":
            context = text[end:end+100].lower()
            code_tech = "inconnu"
            for key, path in CODE_MAP.items():
                if key in context:
                    code_tech = path
                    break
            tag = f'<a data="fr_code_article:{code_tech}/{clean_val}">{val}</a>'
            result = result[:start] + tag + result[end:]
        elif label == "ID_LOI":
            tag = f'<a data="fr_loi:{clean_val}">{val}</a>'
            result = result[:start] + tag + result[end:]
    return result

def run_production():
    input_root = Path("data")
    output_root = Path("results")

    files_to_process = list(input_root.glob("**/*.md")) + list(input_root.glob("**/*.csv"))


    for file_path in files_to_process:
        # Calcul du chemin de sortie pour garder la même structure
        relative_path = file_path.relative_to(input_root)
        target_path = output_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        

if __name__ == "__main__":
    run_production()