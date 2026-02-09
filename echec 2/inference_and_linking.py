"""
Génération des hyperliens
"""

import spacy
from pathlib import Path
import re
import pandas as pd
from tqdm import tqdm
import json
from collections import defaultdict

class LegalReferenceLinker:
    """Détecte les références juridiques et crée les hyperliens"""
    
    def __init__(self, model_path="./output/model-trained-v2"):
        
        
        # Patterns pour extraire le contexte avec regex
        self.code_pattern = r'(?:code|Code)\s+(?:(?:du|de|des)\s+)?([a-zA-Zàâäéèêëïîôö\s\-]+?)(?:\s+(?:français|général|de\s+))?(?=\s|,|\.|\)|$)'
        self.loi_name_pattern = r'(?:loi|Loi)\s+(?:(?:du|de|des)\s+)?([a-zA-Zàâäéèêëïîôö\s\-]+?)(?:\s+(?:du|de)\s+\d{1,2}\s+\w+\s+\d{4})?(?=\s|,|\.|\)|$)'
        
        self.stats = defaultdict(int)
        self.code_history = {}  # Pour mémoriser le code pour une section
    
    def extract_code_context(self, text, article_position):
        """Extrait le code associé à un article"""
        # Chercher le code dans les ~200 caractères autour de l'article
        start = max(0, article_position - 200)
        end = min(len(text), article_position + 200)
        context = text[start:end].lower()
        
        # Chercher des mots comme "code civil", "code du travail", etc.
        code_pattern = r'(?:code|loi)\s+(?:(?:du|de|des)\s+)?([a-zàâäâéèêëïîôö\s\-]+?)(?:\s+(?:du|de|français|général))?(?:\s|,|\.)'
        matches = re.finditer(code_pattern, context)
        
        for match in matches:
            code_name = match.group(1).strip()
            if len(code_name) > 2:  # Ignorer les fragments
                return self.slugify_code(code_name)
        
        # Si on n'a rien trouvé, vérifier si on a un code connu pour le fichier en cours
        # (par ex. extrait depuis le frontmatter du fichier Markdown)
        if hasattr(self, 'current_file') and self.current_file in self.code_history:
            return self.code_history[self.current_file]
        # Sinon retourner inconnu
        return "inconnu"
    
    def slugify_code(self, code_name):
        """Convertit un nom de code en slug (ex: 'Code civil' → 'civil')"""
        # Créer un slug simple
        code_name = code_name.lower().strip()
        code_name = re.sub(r'code\s+(?:du|de)?\s+', '', code_name)
        code_name = re.sub(r'[^\w\s]', '', code_name)
        code_name = '_'.join(code_name.split())
        return code_name if code_name else "inconnu"
    
    def process_text(self, text, filename=""):
        """Traite un texte et génère les hyperliens"""
        if not text or len(text) < 10:
            return text
        
        # Limiter à 900K caractères (pour rester sous la limite de 1M de spacy)
        if len(text) > 900000:
            text = text[:900000]
        
        try:
            # === ÉTAPE 0: Détecter les articles par regex (le modèle les rate!) ===
            result_text = text
            
            # Pattern pour articles: L. 123, L.123-1, R. 444, D. 555-1, etc.
            article_pattern = r'\b([LRD])\.?\s*(\d+(?:\-\d+)?)\b'
            article_matches = []
            
            for match in re.finditer(article_pattern, result_text):
                start = match.start()
                end = match.end()
                entity_text = result_text[start:end]
                num = entity_text.replace(" ", "").replace(".", "")
                
                # Extraire le code du contexte
                code = self.extract_code_context(result_text, start)
                link = f'<a data="fr_code_article:{code}/{num}">{entity_text}</a>'
                article_matches.append((start, end, link))
                self.stats["ARTICLE_NUM"] += 1
            
            # Appliquer les remplacements d'articles (en reverse)
            for start, end, link in reversed(article_matches):
                result_text = result_text[:start] + link + result_text[end:]
            
            # === ÉTAPE 1: Détecter les noms de codes avec regex ===
            code_matches = []
            code_name_pattern = r'\bcode\s+(?:du|de|des)?\s+([a-zA-Zàâäéèêëïîôö\s\-]+?)(?=\s+\w+|\s*$|,|\.|\))'
            for match in re.finditer(code_name_pattern, result_text, re.IGNORECASE):
                code_text = match.group(0)
                code_name = match.group(1).strip()
                # Vérifier que ça fait sens
                if len(code_name) > 2 and len(code_name) < 100:
                    code_slug = self.slugify_code(code_name)
                    link = f'<a data="fr_code:{code_slug}">{code_text}</a>'
                    code_matches.append((match.start(), match.end(), link))
                    self.stats["CODE_NAME"] += 1
            
            # Appliquer les remplacements de code (en reverse pour pas perdre les indices)
            for start, end, link in reversed(code_matches):
                result_text = result_text[:start] + link + result_text[end:]
            
            # === ÉTAPE 2: Détecter les noms de loi avec regex ===
            loi_matches = []
            # Chercher "loi portant", "loi relative", "loi instituant", etc. suivi du titre
            loi_name_pattern = r'\bloi\s+(?:portant|relative|instituant|visant|abrogeant|modifiant)\s+([a-zA-Zàâäéèêëïîôö\s\-]+?)(?=\s+du\s+\d|\s*$|,|\.|loi\s+n°)'
            for match in re.finditer(loi_name_pattern, result_text, re.IGNORECASE):
                loi_text = match.group(0)
                loi_name = match.group(1).strip()
                if len(loi_name) > 2 and len(loi_name) < 200:
                    loi_slug = re.sub(r'[^\w\s]', '', loi_name).replace(' ', '_')[:50]
                    link = f'<span class="ref-loi-name">{loi_text}</span>'
                    loi_matches.append((match.start(), match.end(), link))
                    self.stats["LOI_NAME"] += 1
            
            # Appliquer les remplacements de loi (en reverse)
            for start, end, link in reversed(loi_matches):
                result_text = result_text[:start] + link + result_text[end:]
            
            # === ÉTAPE 3: Inférence avec le modèle NER ===
            # Le modèle reste utile pour les alinéas
            doc = self.nlp(result_text)
            
            # Trier les entités par position (inverse pour pas mélanger les indices)
            entities = sorted(doc.ents, key=lambda x: x.start_char, reverse=True)
            
            for ent in entities:
                start = ent.start_char
                end = ent.end_char
                label = ent.label_
                entity_text = result_text[start:end]
                
                # Ignorer si c'est déjà dans un lien
                if '<a' in result_text[max(0, start-10):start] or '<span' in result_text[max(0, start-10):start]:
                    continue
                
                # Générer le lien HTML selon le type d'entité
                if label == "ALINEA_NUM":
                    # Ne pas confondre "Chapitre IV" / numérotation de chapitres
                    # avec un véritable alinéa. Filtrer si le contexte contient
                    # 'chapitre' ou 'chap.' ou si l'entité ressemble à un
                    # numéro romain (souvent utilisé pour chapitres).
                    window = result_text[max(0, start-20):min(len(result_text), end+20)].lower()
                    ent_stripped = entity_text.strip()
                    if 'chapitre' in window or 'chap.' in window:
                        continue
                    if re.match(r'^[ivxlcdmIVXLCDM]+\.?$', ent_stripped):
                        continue
                    # L'alinéa doit aussi souvent être explicitement mentionné
                    # ("alinéa", "1er alinéa", "2ème alinéa"). Si le modèle
                    # a labellisé sans ce mot, vérifier la proximité.
                    context_has_alinea = 'alin' in window or 'alinéa' in window
                    if not context_has_alinea:
                        # si l'entité contient un tiret entre chiffres (ex: 112-4),
                        # il s'agit d'un article fragmenté (article L.112-4), pas d'un alinéa
                        if re.search(r'\d+-\d+', ent_stripped):
                            continue
                    link = f'<span class="ref-alinea">{entity_text}</span>'
                    self.stats["ALINEA_NUM"] += 1
                
                elif label == "LOI_NUM":
                    link = f'<a data="fr_loi:{entity_text}">{entity_text}</a>'
                    self.stats["LOI_NUM"] += 1
                
                else:
                    continue
                
                # Remplacer dans le texte (en inverse pour pas mélanger les indices)
                result_text = result_text[:start] + link + result_text[end:]
            
            return result_text
        
        except Exception as e:
            return text
    
    def process_codes(self, sample_size=5):
        """Traite les fichiers codes (Markdown)"""
        
        codes_path = Path("data/codes")
        output_path = Path("results_v2/codes")
        output_path.mkdir(parents=True, exist_ok=True)
        
        files = sorted(list(codes_path.glob("*.md")))
        if sample_size and isinstance(sample_size, int):
            files = files[:sample_size]
        
        for file_path in tqdm(files, desc="Codes"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Extraire si présent le titre dans le frontmatter (---) pour connaître le code
                code_slug = None
                if content.startswith('---'):
                    # frontmatter present
                    parts = content.split('---')
                    if len(parts) > 1:
                        fm = parts[1]
                        for line in fm.splitlines():
                            if line.lower().startswith('title:'):
                                title = line.split(':',1)[1].strip().lower()
                                # rechercher "code" dans le titre
                                m = re.search(r'code\s+de\s+([a-z\s\-]+)', title)
                                if m:
                                    code_slug = self.slugify_code(m.group(1))
                                else:
                                    # fallback: prendre dernier mot
                                    code_slug = self.slugify_code(title)
                                break
                if code_slug:
                    self.code_history[file_path.name] = code_slug
                # Définir fichier courant pour fallback
                self.current_file = file_path.name
                
                # Découper par sections (## ou ###) pour eviter les textes trop longs
                chunks = re.split(r'\n#+\s+', content)
                processed_chunks = []
                
                for chunk in chunks:
                    if len(chunk) > 900000:
                        # Si encore trop long, découper par paragraphes
                        sub_chunks = chunk.split('\n\n')
                        for sub_chunk in sub_chunks:
                            processed_chunks.append(self.process_text(sub_chunk, file_path.name))
                    else:
                        processed_chunks.append(self.process_text(chunk, file_path.name))
                
                # Reconstruire avec les séparateurs
                processed = '\n## '.join(processed_chunks)
                
                # Sauvegarder
                output_file = output_path / file_path.name
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(processed)
                
            except Exception as e:
                tqdm.write(f" Erreur  {file_path.name}: {e}")
    
    def process_jorf(self, sample_years=1):
        """Traite les fichiers JORF (CSV)"""
    
        
        jorf_path = Path("data/jorf_2023_1990")
        output_path = Path("results_v2/jorf_2023_1990")
        output_path.mkdir(parents=True, exist_ok=True)
        
        files = sorted(list(jorf_path.glob("*.csv")))[-sample_years:]
        
        for file_path in tqdm(files, desc="JORF files"):
            try:
                # Lire le CSV
                df = pd.read_csv(file_path, sep='|', header=None, 
                               on_bad_lines='skip', nrows=500)  # Limiter pour le test
                
                # Traiter chaque ligne
                processed_rows = []
                for row in tqdm(df.values, desc=f"  {file_path.name}", leave=False):
                    # Généralement la dernière colonne contient le texte principal
                    if len(row) > 0:
                        text = str(row[-1]) if pd.notna(row[-1]) else ""
                        processed_text = self.process_text(text, file_path.name)
                        # Remplacer le texte dans la ligne
                        row = list(row)
                        row[-1] = processed_text
                        processed_rows.append(row)
                
                # Sauvegarder en CSV
                output_file = output_path / file_path.name
                out_df = pd.DataFrame(processed_rows)
                out_df.to_csv(output_file, sep='|', header=False, index=False, 
                            encoding='utf-8', quoting=3)  # QUOTE_NONE
                
            except Exception as e:
                tqdm.write(f" Erreur  {file_path.name}: {e}")
    
    
    def save_report(self):
        """Sauvegarde un rapport JSON"""
        report = {
            "timestamp": str(pd.Timestamp.now()),
            "model_used": "model-trained-v2",
            "stats": dict(self.stats),
            "total_entities": sum(self.stats.values())
        }
        
        output_file = Path("results_v2/inference_report.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Rapport sauvegardé: {output_file}")


