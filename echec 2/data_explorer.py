"""
 Exploration et identification des patterns de références juridiques
"""

import re
import json
from pathlib import Path
from collections import Counter
import pandas as pd

class DataExplorer:
    def __init__(self):
        self.patterns_found = {
            "article_refs": [],      # L. 123, R. 444-2, Art. 1, etc.
            "alinea_refs": [],       # 1er alinéa, 3ème alinéa, etc.
            "loi_refs": [],          # loi n° 2023-1380
            "code_names": [],        # Code civil, Code de commerce, etc.
            "complete_refs": [],     # Phrases avec plusieurs références
        }
        self.unique_codes = set()
    
    def extract_from_codes(self, sample_size=20):
        
        codes_path = Path("data/codes")
        files = list(codes_path.glob("*.md"))[:sample_size]
        
        for file_path in files:
            code_name = file_path.stem.replace("_", " ").title()
            self.unique_codes.add(code_name)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Cherche les articles avec contexte
            article_pattern = r'\*\*Art\.\s+([LRD]?[\d\-]+)\*\*\n\n(.{0,200})'
            matches = re.finditer(article_pattern, content)
            
            for i, match in enumerate(matches):
                if i >= 3:  # Max 3 exemples par fichier
                    break
                art_num = match.group(1)
                context = match.group(2).replace('\n', ' ')
                
                self.patterns_found["article_refs"].append({
                    "code": code_name,
                    "article_num": art_num,
                    "context": context[:150]
                })
                
                # Cherche les alinéas dans ce contexte
                alinea_pattern = r'(\d+(?:er|ème|e)?)\s+alinéa'
                if re.search(alinea_pattern, context, re.IGNORECASE):
                    self.patterns_found["alinea_refs"].append({
                        "code": code_name,
                        "text": context[:150]
                    })
    
    def extract_from_jorf(self, sample_size=3):
        """Extrait des phrases du JORF (CSV) - attention au format pipe"""
        
        jorf_path = Path("data/jorf_2023_1990")
        files = sorted(list(jorf_path.glob("*.csv")))[-sample_size:]
        
        for file_path in files:
            
            try:
                # Format très délicat: pipe-delimited
                df = pd.read_csv(file_path, sep='|', header=None, 
                                on_bad_lines='skip', nrows=50)
                
                # La colonne de texte est généralement la dernière
                text_col = df.iloc[:, -1]
                
                for idx, text in enumerate(text_col):
                    if pd.isna(text):
                        continue
                    
                    text = str(text)[:500]  # Limiter la taille
                    
                    # Cherche les références à des articles et lois
                    if any(keyword in text for keyword in ['article', 'loi', 'code', 'Art.']):
                        # Extraire références
                        art_matches = re.findall(r'([LRD]\.?\s*\d+(?:[-–]\d+)?)', text)
                        loi_matches = re.findall(r'loi\s+n°?\s*(\d+[-–]\d+)', text, re.IGNORECASE)
                        
                        if art_matches or loi_matches:
                            self.patterns_found["complete_refs"].append({
                                "year": file_path.stem.split('_')[1],
                                "text": text,
                                "articles": art_matches,
                                "lois": loi_matches
                            })
                            
                            if len(self.patterns_found["complete_refs"]) >= 15:
                                return
            
            except Exception as e:
                print(f"   Erreur: {e}")
    
   