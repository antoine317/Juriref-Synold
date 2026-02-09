import spacy
from spacy.tokens import DocBin
import json
import random

def convert_and_split(json_file, train_path, dev_path, split_ratio=0.9):
    nlp = spacy.blank("fr")
    
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # On mélange les données pour éviter les biais (ex: tous les codes au début)
    random.shuffle(data)
    
    split_point = int(len(data) * split_ratio)
    train_data = data[:split_point]
    dev_data = data[split_point:]

    for set_data, output_path in [(train_data, train_path), (dev_data, dev_path)]:
        db = DocBin()
        count = 0
        for text, annot in set_data:
            doc = nlp.make_doc(text)
            ents = []
            for start, end, label in annot["entities"]:
                span = doc.char_span(start, end, label=label, alignment_mode="contract")
                if span:
                    ents.append(span)
            
            if ents:
                doc.ents = ents
                db.add(doc)
                count += 1
        db.to_disk(output_path)
        print(f" Fichier {output_path} avec {count} exemples.")

if __name__ == "__main__":
    # On limite à 100 000 exemples
    convert_and_split("training_data.json", "train.spacy", "dev.spacy")