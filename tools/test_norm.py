import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.generate_full_site import LegalEngine

engine = LegalEngine()
lines = [
    "article 209quater",
    "article 209 quater",
    "article 209 quater le texte",
    "articles L. 111-2 et L. 111-3",
]
for line in lines:
    ents = engine.extract(line, None)
    print('LINE:', line)
    print('ENTITIES:', ents)
    print('---')
