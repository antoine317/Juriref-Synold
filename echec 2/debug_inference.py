"""
Script de debug pour tester l'inférence du modèle sur des cas spécifiques
"""

import spacy

# Charger le modèle
nlp = spacy.load("./output/model-trained-v2")

# Textes de test
test_texts = [
    "Sous réserve des dispositions des articles L. 111-2 et L. 111-3, toute personne résidant en France bénéficie.",
    "Les articles L. 111-2 et L. 111-3 concernent les étrangers.",
    "L'article L. 111-1 s'applique aussi.",
    "Le premier alinéa de l'article L. 111-2 prévoit que...",
]

print("🔍 TEST D'INFÉRENCE DU MODÈLE\n" + "="*70)

for text in test_texts:
    print(f"\nTexte: {text}\n")
    
    doc = nlp(text)
    
    if doc.ents:
        print(f"Entités détectées ({len(doc.ents)}):")
        for ent in doc.ents:
            print(f"  [{ent.start_char}:{ent.end_char}] '{text[ent.start_char:ent.end_char]}' → {ent.label_}")
    else:
        print("❌ Aucune entité détectée")
    
    print()

print("\n" + "="*70)
print("💡 Analyse:")
print("  - Si peu d'ARTICLE_NUM détectés: le modèle a probablement du mal avec cette classe")
print("  - Si ALINEA_NUM en excès: c'est le déséquilibre du dataset")
