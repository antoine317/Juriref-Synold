import re
import os
import csv
import unicodedata
from pathlib import Path

# 1. Configuration pour obtenir les fichiers html avec un peu de css

BASE_DIR = Path(__file__).resolve().parent.parent
DIR_CODES = BASE_DIR / "data" / "codes"
DIR_JORF = BASE_DIR / "data" / "jorf_2023_1990"
DIR_OUTPUT = BASE_DIR / "data" / "html"

HTML_HEADER = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: auto; padding: 20px; line-height: 1.6; background: #f4f4f4; color: #333; }
        .container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; border-left: 5px solid #3498db; padding-left: 10px; }
        a { color: #2980b9; text-decoration: none; font-weight: 600; border-bottom: 1px dotted #2980b9; transition: all 0.2s; }
        a:hover { background-color: #eaf6ff; color: #1a5276; border-bottom: 1px solid #1a5276; cursor: pointer; }
        a[data]:hover::after {
            content: attr(data); position: absolute; background: #2c3e50; color: #ecf0f1;
            padding: 5px 10px; font-size: 11px; border-radius: 4px; margin-top: -30px;
            white-space: nowrap; box-shadow: 0 2px 5px rgba(0,0,0,0.2); z-index: 1000;
        }
        .jorf-article { background: white; padding: 20px; margin-bottom: 15px; border-radius: 5px; border-left: 4px solid #2ecc71; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    </style>
</head>
<body><div class="container">"""

HTML_FOOTER = """</div></body></html>"""

# 2. Définition des regexps

class LegalEngine:
    def __init__(self):
        self.latin_map = {'premier' : '1', 'bis':'-2','ter':'-3','quater':'-4','quinquies':'-5','sexies':'-6','septies':'-7','octies':'-8','nonies':'-9','decies':'-10', 'undecies':'11'}
        
        #Test avec les premiers
        code_names = {"civil", "penal", "travail", "commerce", "impots", "consommation", "artisanat", "education", "action sociale"}
        #Puis on continue en chargeant ceux compris dans les datas
        if DIR_CODES.exists():
            for p in DIR_CODES.glob("*.md"):
                clean = p.stem.lower().replace("code", "").replace("_", " ").strip()
                if clean: code_names.add(clean)
        
        # Regex Code
        fuzzy_names = [self._fuzzy(n) for n in code_names]
        fuzzy_names.sort(key=len, reverse=True)
        self.re_code = re.compile(r"(?i)\bcode\s+(?:général\s+)?(?:(?:des?|du|de\s+la|de\s+l['’])\s+|d['’]\s*)?(?P<val>" + "|".join(fuzzy_names) + r")\b")
        
        # Regex Sources (Lois, conventions, décrets...)
        # Le mot accord a été enlevé car il apparait dans trop de contextes différents
        # On accepte des dates plus variées (ex: "des 3 et 20 septembre 1792")
        # seulement si le type est précédé d'un espace ou du début de ligne
        self.re_source = re.compile(
            r"(?i)(?<!\S)(?P<type>loi|décret|ordonnance|arrêté|circulaire|convention|charte|traité)\s+"
            r"(?P<val>[^,;\n\.]{1,200})"
        )
        
        # Regex Livre (Strict pour éviter "délivrer" qui revenait souvent). ne marche pas trop
        self.re_livre = re.compile(r"(?i)\bLivre\s+(?P<val>I{1,3}|IV|V|VI|VII|VIII|IX|X|\d+(?:er)?|préliminaire)\b")

        # Regex Article (Plages et énumérations comprises)
        # Reconnaît les nombres préfixés par "article(s)"/"art." ou par des lettres types (L, D, R, A)
        # Autorise les séparateurs: virgule, point-virgule, 'et', 'à', 'au' (avec ou sans espaces)
        # Autorise également les suffixes latins (bis, ter, quater, ...), attachés ou séparés par un espace
        suffix_keys = sorted(self.latin_map.keys(), key=len, reverse=True)
        suffix_group = r"(?:" + "|".join(re.escape(k) for k in suffix_keys) + r")?"
        item = r"(?:[LDR]\.?|A\.?|\*)?\s*\d+(?:[\.-]\d+)*(?:-\d+)*(?:\s*" + suffix_group + r")?"
        self.re_art = re.compile(r"(?i)\b(?:articles?|art\.)\s+(?P<num>" + item + r"(?:\s*(?:,|;|et|à|au)\s*" + item + r")*)")

        self.re_anaphora = re.compile(r"(?i)(?:du|au|le|ce|de\s+la)\s+m[êe]me\s+(?:code|loi|décret|ordonnance|convention)")

    def _fuzzy(self, text):
        s = {'a':'[aàâä]','e':'[eéèêë]','i':'[iîï]','o':'[oôö]','u':'[uùûü]','c':'[cç]','y':'[yÿ]'}
        clean = "".join([c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)])
        return "".join([s[c] if c in s else (r"\s+" if c==' ' else re.escape(c)) for c in clean])

    def _is_year(self, text):
        """Détecte si un texte est une année pure (ex: 1996)"""
        return re.fullmatch(r"19\d{2}|20\d{2}", text.strip()) is not None

    def extract(self, text, meta=None):
        # 1. DÉTECTION BRUTE
        codes = [{'tag': 'CODE', 'val': m.group('val'), 'span': m.span(), 'code': None} for m in self.re_code.finditer(text)]
        
        # Filtrage des lois/conventions (on tronque la valeur après la date ou le numéro si présent)
        lois = []
        for m in self.re_source.finditer(text):
            raw_val = m.group('val').strip()
            # si année présente, tronquer après l'année
            ym = re.search(r"\b(19|20)\d{2}\b", raw_val)
            if ym:
                val = raw_val[:ym.end()]
                rel_end = ym.end()
            else:
                nm = re.search(r"n[°o]?\s*\d+", raw_val, flags=re.IGNORECASE)
                if nm:
                    val = raw_val[:nm.end()]
                    rel_end = nm.end()
                else:
                    val = raw_val
                    rel_end = len(raw_val)

            # ajuster la span pour que le lien ne recouvre que la partie pertinente
            try:
                whole = m.group(0)
                raw_idx = whole.lower().find(raw_val.lower())
                if raw_idx >= 0:
                    abs_end = m.start() + raw_idx + rel_end
                    span = (m.start(), abs_end)
                else:
                    span = m.span()
            except Exception:
                span = m.span()

            lois.append({'tag': 'LOI', 'val': f"{m.group('type').title()} {val}", 'span': span, 'code': None})
            
        livres = [{'tag': 'LIVRE', 'val': m.group('val'), 'span': m.span(), 'code': 'INCONNU'} for m in self.re_livre.finditer(text)]
        
        # Filtrage des articles (on ignore les chiffres isolés)
        articles = []
        for m in self.re_art.finditer(text):
            num = m.group('num').strip()
            if self._is_year(num) and "art" not in text[max(0, m.start()-10):m.start()].lower():
                continue

            # si énumération (séparateurs , ; ou mots 'et','à','au'), créer des entrées séparées avec spans précis
            if re.search(r"\b(?:,|;|et|à|au)\b", num, flags=re.IGNORECASE):
                subtext = num
                for sm in re.finditer(r"(?:[LDR]\.?|A\.?|\*)?\s*\d+(?:[\.-]\d+)*", subtext):
                    sub_num = sm.group(0).strip()
                    rel_pos = m.group(0).lower().find(m.group('num').lower())
                    if rel_pos >= 0:
                        abs_start = m.start() + rel_pos + sm.start()
                    else:
                        abs_start = m.start() + m.group(0).find(m.group('num')) + sm.start()
                    abs_end = abs_start + len(sm.group(0))
                    articles.append({'tag': 'ART', 'val': sub_num, 'span': (abs_start, abs_end), 'code': 'INCONNU', 'livre': 'INCONNU'})
            else:
                articles.append({'tag': 'ART', 'val': num, 'span': m.span(), 'code': 'INCONNU', 'livre': 'INCONNU'})

        # 2. HIÉRARCHIE LIVRE -> CODE
        for lv in livres:
            for c in codes:
                if 0 < (c['span'][0] - lv['span'][1]) < 100:
                    lv['code'] = c['val']; break
            if lv['code'] == 'INCONNU' and meta and meta.get('type') == 'CODE':
                lv['code'] = meta['source'].replace('.md','').replace('code','').strip('_')

        # 3. HIÉRARCHIE ARTICLE -> LIVRE/CODE
        parents = sorted(codes + lois + livres, key=lambda x: x['span'][0])
        linked_articles = []
        for art in articles:
            p_code, p_livre, p_tag = "INCONNU", "INCONNU", None
            snippet = text[art['span'][1]:art['span'][1]+150]
            
            # Parent direct: on accepte un parent proche avant ou après l'article
            for p in parents:
                after_dist = p['span'][0] - art['span'][1]
                before_dist = art['span'][0] - p['span'][1]
                if (0 < after_dist < 120) or (0 < before_dist < 120):
                    p_tag = p['tag']
                    if p['tag'] == 'LIVRE':
                        p_livre, p_code = p['val'], p['code']
                    else:
                        p_code = p['val']
                    break
            
            # Anaphore
            if p_code == "INCONNU" and self.re_anaphora.search(snippet) and linked_articles:
                p_code, p_livre = linked_articles[-1]['code'], linked_articles[-1]['livre']

            # Contexte fichier
            if p_code == "INCONNU" and meta and meta.get('type') == 'CODE':
                p_code = meta['source'].replace('.md','').replace('code','').strip('_')

            linked_articles.append({'tag': 'ART', 'article': self._norm(art['val']), 'code': p_code, 'livre': p_livre, 'span': art['span'], 'parent_tag': p_tag})

        # 4. PROPAGATION ARRIÈRE (Plages)
        for i in range(len(linked_articles)-2, -1, -1):
            if linked_articles[i]['code'] == "INCONNU" and linked_articles[i+1]['code'] != "INCONNU":
                if (linked_articles[i+1]['span'][0] - linked_articles[i]['span'][1]) < 600:
                    linked_articles[i]['code'] = linked_articles[i+1]['code']
                    linked_articles[i]['livre'] = linked_articles[i+1]['livre']

        res = linked_articles + livres + codes + lois
        res.sort(key=lambda x: x['span'][0])
        return res

    def _norm(self, v):
        # Normalise un identifiant d'article ou de suffixe latin:
        # - remplace "1er" par "1"
        # - convertit les suffixes latins (bis/ter/quater...) en codage numérique (-2,-3,-4...)
        # - supprime espaces et majuscules pour retourner une forme canonique (ex: "209 quater" -> "209-4")
        v = re.sub(r'\b1er\b','1', v, flags=re.IGNORECASE)
        # Remplacer les suffixes latins attachés à un nombre, avec ou sans espace,
        # ex: '209quater' ou '209 quater' -> '209-4'
        keys = sorted(self.latin_map.keys(), key=len, reverse=True)
        suf_pattern = r'(?i)(?P<num>\d+)\s*(?P<suf>' + '|'.join(re.escape(k) for k in keys) + r')\b'
        def _repl(m):
            num = m.group('num')
            suf = m.group('suf').lower()
            return num + self.latin_map.get(suf, '')

        v = re.sub(suf_pattern, _repl, v)
        # Pour régler quelques problèmes restants avec les suffixes latins 
        for k, vs in self.latin_map.items():
            v = re.sub(r'\b' + re.escape(k) + r'\b', vs, v, flags=re.IGNORECASE)
        return v.replace(" ","").replace("\xa0","").upper().strip(".")

# 3. Génération des liens hypertexte

def slugify(t):
    # Crée un slug sûr pour utiliser dans les identifiants de lien.
    # Extrait une version ascii/minuscule et remplace les séparateurs par des underscores.
    if not t or t == "INCONNU": return None
    t = "".join([c for c in unicodedata.normalize('NFKD', t.lower()) if not unicodedata.combining(c)])
    t = re.sub(r"\b(code|loi|decret|ordonnance|du|des|de|la|le|l|d|et|n|no)\b", "", t)
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")

def inject_links(text, entities):
    # Injecte des balises <a data="..."></a> autour des entités détectées.
    # Les entités doivent contenir des spans absolus pour pouvoir réécrire la chaîne.
    if not entities: return text
    entities.sort(key=lambda x: x['span'][0], reverse=True)
    curr, mask = text, []
    for e in entities:
        start, end = e['span']
        if any(not (end <= ms or start >= me) for ms, me in mask): continue
        
        seg, data = curr[start:end], None
        if e['tag'] == 'ART':
            s = slugify(e['code'])
            if s:
                if e.get('parent_tag') == 'LOI':
                    data = f"fr_loi_article:{s}/{e['article']}"
                else:
                    data = f"fr_code_article:{s}/{e['article']}"
        elif e['tag'] == 'CODE':
            s = slugify(e['val'])
            if s: data = f"fr_code:code/{s}"
        elif e['tag'] == 'LOI':
            s = slugify(e['val'])
            if s: data = f"fr_loi:loi/{s}"
        elif e['tag'] == 'LIVRE':
            s_lv, s_co = slugify(e['val']), slugify(e.get('code'))
            if s_lv: data = f"fr_livre:{s_lv}" + (f"/{s_co}" if s_co else "")

        if data:
            curr = curr[:start] + f'<a data="{data}">{seg}</a>' + curr[end:]
            mask.append((start, end))
    return curr

# 4. Fichier main.py que j'ai rentré ici car il n'arrivait pas à faire le lien 

def main():
    # Point d'entrée principal : parcourt les fichiers de `data/codes` et `data/jorf`,
    # extrait les entités et génère les fichiers html dans `data/html`.
    engine = LegalEngine()
    (DIR_OUTPUT / "codes").mkdir(parents=True, exist_ok=True)
    (DIR_OUTPUT / "jorf").mkdir(parents=True, exist_ok=True)

    # Traitement des codes juridique
    for f in DIR_CODES.glob("*.md"):
        html = ""
        meta = {'source': f.name, 'type': 'CODE'}
        with open(f, 'r', encoding='utf-8') as fin:
            for line in fin:
                if line.startswith('#'):
                    level = min(line.count('#'), 6)
                    html += f"<h{level}>{line.strip('# ')}</h{level}>"
                elif line.strip():
                    ents = engine.extract(line, meta)
                    html += f"<p>{inject_links(line, ents)}</p>"
        with open(DIR_OUTPUT / "codes" / f.name.replace('.md','.html'), 'w', encoding='utf-8') as fout:
            fout.write(HTML_HEADER.replace("{title}", f.name) + html + HTML_FOOTER)

    # Traitement JORF (1990-2023)
    for annee in range(1990, 2024):
        f = DIR_JORF / f"jorf_{annee}.csv"
        if not f.exists(): f = BASE_DIR / "data" / f"jorf_{annee}.csv"
        if not f.exists(): continue
        
        html_jorf, meta = f"<h1>Journal Officiel {annee}</h1>", {'source': f.name, 'type': 'JORF'}
        with open(f, 'r', encoding='utf-8', errors='ignore') as fin:
            reader = csv.reader(fin, delimiter='|')
            for row in reader:
                if not row: continue
                text = max(row, key=len)
                if len(text) < 30: continue
                ents = engine.extract(text, meta)
                html_jorf += f"<div class='jorf-article'>{inject_links(text, ents)}</div>"
        
        with open(DIR_OUTPUT / "jorf" / f.name.replace('.csv','.html'), 'w', encoding='utf-8') as fout:
            fout.write(HTML_HEADER.replace("{title}", f.name) + html_jorf + HTML_FOOTER)
        print(f"✅ JORF {annee} généré.")

if __name__ == "__main__":
    main()