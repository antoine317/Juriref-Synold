import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.generate_full_site import LegalEngine

engine = LegalEngine()
lines = [
    "Décret des 3 et 20 septembre 1792.",
    "Loi du 31 juillet 1879.",
    "Loi n° 58-346 du 3 avril 1958 a attribué valeur législative au code des instruments monétaires et des médailles."
]
for line in lines:
    ents = engine.extract(line, None)
    print('LINE:', line)
    print('ENTITIES:', ents)
    print('---')
