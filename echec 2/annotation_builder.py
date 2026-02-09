"""
Construction du dataset annoté 

"""

import re
import json
from pathlib import Path
import pandas as pd
from collections import defaultdict
import random

class AnnotationBuilder:
    """Construit un dataset avec annotations structurées"""
    
    # Les classes que le modèle doit apprendre
    ENTITY_TYPES = {
        "ARTICLE_NUM": "Numéro d'article (ex: 123, L. 111-2, R. 444)",
        "CODE_NAME": "Nom du code juridique (ex: Code civil, Code de commerce)",
        "LOI_NUM": "Numéro de loi (ex: 2023-1380)",
        "LOI_NAME": "Titre de la loi (ex: 'loi relative à...')",
        "ALINEA_NUM": "Numéro ou ordre d'alinéa (ex: 1er, 3ème, I, II)",
    }
    
    def __init__(self):
        self.dataset = []
        self.stats = defaultdict(int)
    
    def normalize_article_num(self, match):
        """Extrait seulement le numéro, sans les lettres/points"""
        text = match.group(0)
        # L. 123-1 → 123-1
        num = re.sub(r'[LRD\.\s]', '', text)
        return num if num else None
    
    def extract_articles_from_code(self, file_path, code_name):
        """Extrait les articles d'un fichier code (Markdown)"""
        examples = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern: **Art. 123-1**\n\n[Contenu sur 2-3 lignes]
        article_pattern = r'\*\*Art\.\s+([LRD]?[\d\-]+(?:\-\d+)?)\*\*\n\n((?:[^\n]*\n?){1,4})'
        
        for match in re.finditer(article_pattern, content):
            article_num = match.group(1)
            context = match.group(2).replace('\n', ' ').strip()
            
            # Limiter la longueur pour ne pas surcharger le modèle
            if len(context) > 300:
                context = context[:300]
            
            if not context or len(context) < 20:
                continue
            
            # Créer la sentence avec annotations
            # Format spacy: (text, {"entities": [[start, end, label], ...]})
            
            entities = []
            
            # Chercher le numéro d'article dans le contexte
            # Pattern plus robuste pour éviter les problèmes d'alignement
            art_pattern = rf'[LRD]?\s*({re.escape(article_num)})'
            
            for match_art in re.finditer(art_pattern, context):
                # Récupérer juste le numéro (groupe 1)
                num_start = match_art.start(1)
                num_end = match_art.end(1)
                
                # Double-vérifer que c'est bien dans les limites
                if 0 <= num_start < num_end <= len(context):
                    annotated_text = context[num_start:num_end]
                    # Vérifier que ça correspond bien au pattern
                    if re.match(r'[\dL\-]+', annotated_text):
                        entities.append([num_start, num_end, "ARTICLE_NUM"])
                        self.stats["ARTICLE_NUM"] += 1
                        break  # Prendre seulement la première occurrence
            
            # Chercher les alinéas dans le contexte
            alinea_pattern = r'\b((?:premier|deuxième|troisième|quatrième|cinquième|sixième|septième|huitième|neuvième|dixième|1er|2e|3e|3ème|4ème)\s+alinéas?|[IVI]+)\b'
            for match_alinea in re.finditer(alinea_pattern, context, re.IGNORECASE):
                alinea_start = match_alinea.start()
                alinea_end = match_alinea.end()
                
                # Vérifier que ce n'est pas déjà couvert par une autre entité
                if not any(e[0] <= alinea_start < e[1] for e in entities):
                    annotated_text = context[alinea_start:alinea_end]
                    if annotated_text.strip():  # Vérifier que ce n'est pas vide
                        entities.append([alinea_start, alinea_end, "ALINEA_NUM"])
                        self.stats["ALINEA_NUM"] += 1
            
            if entities:  # Seulement si on a au moins une entité
                examples.append([context, {"entities": entities}])
        
        return examples
    
    def extract_from_jorf(self, file_path, year):
        """Extrait des textes du JORF avec annotations"""
        examples = []
        
    
        df = pd.read_csv(file_path, sep='|', header=None, 
                           on_bad_lines='skip', nrows=300)
            
            # La dernière colonne contient généralement le texte
        text_col = df.iloc[:, -1]
            
        for text in text_col:
            if pd.isna(text):
                continue
                
                text = str(text).strip()
                if len(text) < 50:  # Ignorer les textes trop courts
                    continue
                
                # Limiter à 400 caractères pour pas surcharger
                if len(text) > 400:
                    text = text[:400]
                
                entities = []
                
                # 1. Chercher ARTICLE_NUM: L. 123-1, R. 444-2, etc.
                # Pattern pour articles du code (L. 123 ou L. 123-1)
                art_pattern = r'([LRD])\.?\s*(\d+(?:\-\d+)?)\b'
                for match in re.finditer(art_pattern, text):
                    # Ne baliser QUE le numéro (groupe 2)
                    num_start = match.start(2)
                    num_end = match.end(2)
                    
                    # Double-vérifier les limites
                    if 0 <= num_start < num_end <= len(text):
                        span_text = text[num_start:num_end]
                        if re.match(r'^\d+(?:\-\d+)?$', span_text):
                            entities.append([num_start, num_end, "ARTICLE_NUM"])
                            self.stats["ARTICLE_NUM"] += 1
                
                # 2. Chercher LOI_NUM: numéro de loi (2023-1380)
                loi_num_pattern = r'\b(\d{4}\-\d{1,4})\b'
                for match in re.finditer(loi_num_pattern, text):
                    # S'assurer que ça précède "loi" ou un contexte de loi
                    start_context = max(0, match.start() - 50)
                    context_before = text[start_context:match.start()].lower()
                    
                    if 'loi' in context_before:
                        loi_start = match.start()
                        loi_end = match.end()
                        
                        # Vérifier que ce n'est pas déjà couvert
                        if not any(e[0] <= loi_start < e[1] for e in entities):
                            if 0 <= loi_start < loi_end <= len(text):
                                span_text = text[loi_start:loi_end]
                                if re.match(r'^\d{4}\-\d{1,4}$', span_text):
                                    entities.append([loi_start, loi_end, "LOI_NUM"])
                                    self.stats["LOI_NUM"] += 1
                
                # 3. Chercher ALINEA_NUM
                alinea_pattern = r'\b((?:premier|deuxième|troisième|quatrième|1er|2e|3e|3ème|4ème)\s+alinéas?|alinéa\s+(?:1er|2e|3e|[IVI]+))\b'
                for match in re.finditer(alinea_pattern, text, re.IGNORECASE):
                    alinea_start = match.start()
                    alinea_end = match.end()
                    
                    # Ne pas l'ajouter s'il y a déjà une entité au même endroit
                    if not any(e[0] <= alinea_start < e[1] for e in entities):
                        if 0 <= alinea_start < alinea_end <= len(text):
                            span_text = text[alinea_start:alinea_end]
                            if span_text.strip():
                                entities.append([alinea_start, alinea_end, "ALINEA_NUM"])
                                self.stats["ALINEA_NUM"] += 1
                
                if entities:
                    examples.append([text, {"entities": entities}])
  
        
        return examples
    
    def build_dataset(self):
        """Construit le dataset complet à partir de tous les fichiers"""
        
        
        # 1. Extraire des fichiers codes
        codes_path = Path("data/codes")
        
        for file_path in sorted(codes_path.glob("*.md"))[:30]:  # Limiter pour la rapidité
            code_name = file_path.stem.replace("_", " ").title()
            examples = self.extract_articles_from_code(file_path, code_name)
            self.dataset.extend(examples)
            
        
        # 2. Extraire du JORF
        jorf_path = Path("data/jorf_2023_1990")
        
        for file_path in sorted(jorf_path.glob("*.csv"))[-5:]:  # Just recent years
            examples = self.extract_from_jorf(file_path, file_path.stem)
            self.dataset.extend(examples)
            
        
        # 3. Mélanger le dataset
        random.shuffle(self.dataset)
        
        print(f" {len(self.dataset)} exemples")

    
    def validate_and_clean(self):
        """Valide que toutes les annotations sont correctes"""
        
        cleaned_dataset = []
        errors = 0
        
        for text, annotations in self.dataset:
            valid = True
            
            for start, end, label in annotations.get("entities", []):
                if start < 0 or end > len(text) or start >= end:
                    valid = False
                    errors += 1
                    break
                
                # Vérifier que l'annotation a du sens
                annotated_text = text[start:end]
                if not annotated_text.strip():
                    valid = False
                    errors += 1
                    break
            
            if valid:
                cleaned_dataset.append([text, annotations])
        
        self.dataset = cleaned_dataset
        print(f"   Exemples validés: {len(self.dataset)}")
        print(f"   Erreurs corrigées: {errors}")
        
        return self.dataset
    
    def save_dataset(self, output_path="training_data_v2.json"):
        """Sauvegarde le dataset en format spacy JSON"""
        
        output_data = {
            "version": "2.0",
            "metadata": {
                "entity_types": self.ENTITY_TYPES,
                "total_examples": len(self.dataset),
                "stats": dict(self.stats)
            },
            "data": self.dataset
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        return output_path
