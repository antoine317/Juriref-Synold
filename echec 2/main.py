"""
ÉTAPE 3 : Fine-tuning du modèle spaCy pour NER (Named Entity Recognition)
===========================================================================
Ce script entraîne ou fine-tune un modèle spaCy sur les données annotées.
"""

import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
import json
from pathlib import Path
import random
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class NERTrainer:
    """Entraîne un modèle spacy pour reconnaître les références juridiques"""
    
    def __init__(self):
        self.nlp = None
        self.training_data = []
        self.entity_types = {
            "ARTICLE_NUM": "Numéro d'article (123, L. 111-2, R. 444)",
            "CODE_NAME": "Nom du code juridique",
            "LOI_NUM": "Numéro de loi (2023-1380)",
            "LOI_NAME": "Titre de la loi",
            "ALINEA_NUM": "Numéro d'alinéa (1er, 3ème)",
        }
        
    def load_training_data(self, data_path="training_data_v2.json"):
        """Charge les données d'entraînement. Si un fichier rééquilibré existe,
        il est priorisé (training_data_rebalanced.json)."""
        # Si un dataset rééquilibré existe, le préférer
        preferred = "training_data_rebalanced.json" if Path("training_data_rebalanced.json").exists() else data_path
        with open(preferred, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
       
        return self.training_data
    
    def prepare_training_examples(self):
        """Convertit les données JSON en format spacy Example"""
        examples = []
        errors = 0
        
        for text, annotations in self.training_data:
            try:
                # Créer le doc prédiction (vide)
                doc_pred = self.nlp.make_doc(text)
                
                # Filtrer et valider les entités
                valid_entities = []
                for start_char, end_char, label in annotations.get("entities", []):
                    # Valider les positions
                    if not (0 <= start_char < end_char <= len(text)):
                        errors += 1
                        continue
                    
                    # Vérifier que le texte n'est pas vide
                    span_text = text[start_char:end_char].strip()
                    if not span_text:
                        errors += 1
                        continue
                    
                    # Label doit être dans notre liste de labels
                    if label not in self.entity_types:
                        errors += 1
                        continue
                    
                    valid_entities.append((start_char, end_char, label))
                
                # Créer l'exemple seulement s'il y a des entités valides
                if valid_entities:
                    # Créer l'Example correctement: from_dict s'attend à des annotations raw
                    # On lui passe le doc des prédictions (vide) et les annotations gold
                    try:
                        example = Example.from_dict(doc_pred, {"entities": valid_entities})
                        examples.append(example)
                    except ValueError as e:
                        # Si y'a un problème d'alignement, essayer avec char_span
                        doc_ref = self.nlp.make_doc(text)
                        has_ents = False
                        ents = []
                        
                        for start, end, label in valid_entities:
                            span = doc_ref.char_span(start, end, label=label, alignment_mode="strict")
                            if span is None:
                                span = doc_ref.char_span(start, end, label=label, alignment_mode="contract")
                            if span:
                                ents.append(span)
                                has_ents = True
                        
                        if has_ents:
                            doc_ref.ents = ents
                            example = Example(doc_pred, doc_ref)
                            examples.append(example)
                        else:
                            errors += 1
                
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"    Erreur: {type(e).__name__}: {e}")

                return examples
    
    def initialize_model(self, use_existing=False, model_path="./output/model-best"):
        """Initialise ou charge un modèle spacy"""
        
        if use_existing and Path(model_path).exists():
            self.nlp = spacy.load(model_path)

        else:
            self.nlp = spacy.blank("fr")
            
            # Ajouter le composant NER
            if "ner" not in self.nlp.pipe_names:
                ner = self.nlp.add_pipe("ner", last=True)
                print("   ✅ Pipeline NER créé")
        
        # Configuration du NER
        ner = self.nlp.get_pipe("ner")
        
        # Ajouter les labels AVANT l'entraînement
        for label in self.entity_types.keys():
            ner.add_label(label)
        
        return self.nlp
    
    def train(self, n_iterations=30, batch_size=8, drop_rate=0.5):
        """Entraîne le modèle sur les données"""
        
   
        
        # Préparer les données
        training_examples = self.prepare_training_examples()
    
        
        # Split: 80% train, 20% dev
        random.shuffle(training_examples)
        split = int(len(training_examples) * 0.8)
        train_examples = training_examples[:split]
        dev_examples = training_examples[split:]
        
        print(f"Données: {len(train_examples)} train + {len(dev_examples)} dev")
        
        # Configuration du pipeline
        ner = self.nlp.get_pipe("ner")
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]
        
        # === ÉTAPE CRUCIALE: Initialiser le modèle ===
        # Cela créé toutes les transitions nécessaires pour le NER
        self.nlp.initialize(lambda: train_examples[:200])
           
        
        # Désactiver les autres pipelines pendant l'entraînement
        with self.nlp.disable_pipes(*other_pipes):
            optimizer = self.nlp.create_optimizer()
            
            # Boucle d'entraînement
            for iteration in range(n_iterations):
                random.shuffle(train_examples)
                losses = {}
                batch_count = 0
                batch_errors = 0
                
                # Mini-batches
                for batch_start in range(0, len(train_examples), batch_size):
                    batch_end = min(batch_start + batch_size, len(train_examples))
                    batch = train_examples[batch_start:batch_end]
                    
                    try:
                        self.nlp.update(
                            batch,
                            drop=drop_rate,
                            sgd=optimizer,
                            losses=losses
                        )
                        batch_count += 1
                    except Exception as e:
                        batch_errors += 1
                        if batch_errors <= 2:
                            print(f"      ⚠️ Erreur batch: {str(e)[:80]}")
                
                # Afficher la perte tous les 5 iterations
                if (iteration + 1) % 5 == 0 or iteration == 0:
                    loss_value = losses.get('ner', 0.0) / batch_count if batch_count > 0 else 0
                    print(f"   Iteration {iteration+1:2d}: Loss={loss_value:.4f} ({batch_count} batches ok, {batch_errors} erreurs)")
        
        return self.nlp
    
        """Teste le modèle sur quelques phrases"""
        
        if test_sentences is None:
            test_sentences = [
                "Les dispositions de l'article L. 111-1 du code civil s'appliquent.",
                "Selon le premier alinéa de l'article R. 2122-19, le maire doit...",
                "La loi n° 2023-1380 du 30 décembre 2023 modifie le code.",
            ]
        
        
        for text in test_sentences:
            doc = self.nlp(text)
            print(f"\nTexte: {text}")
            if doc.ents:
                print("Entités reconnues:")
                for ent in doc.ents:
                    print(f"  - '{ent.text}' → {ent.label_}")
            else:
                print("  (Aucune entité reconnue)")
    
    def save_model(self, output_dir="./output/model-trained"):
        """Sauvegarde le modèle entraîné"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        self.nlp.to_disk(output_path)
        print(f"\n💾 Modèle sauvegardé: {output_path}")
        
        # Sauvegarder aussi les métadonnées
        metadata = {
            "date": datetime.now().isoformat(),
            "entity_types": self.entity_types,
            "training_examples": len(self.training_data),
        }
        
        with open(output_path / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return output_path

