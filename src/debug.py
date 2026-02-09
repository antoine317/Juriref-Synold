# Ce fichier n'est pas intéressant, il me servait pour débuguer le code avec l'IA

import sys
from generate_full_site import LegalReferenceExtractor, inject_links, slugify

def main():
    print("🕵️‍♂️ DIAGNOSTIC HTML & LIENS")
    
    # 1. Test du Moteur
    print("\n--- 1. TEST DU MOTEUR (RULE ENGINE) ---")
    engine = LegalReferenceExtractor()
    
    # On simule une phrase typique d'un Code
    text_code = "L'article L. 123-1 dispose que..."
    meta_code = {"source": "minier.md", "type": "CODE"}
    
    print(f"Phrase : '{text_code}'")
    print(f"Contexte : {meta_code}")
    
    refs = engine.extract(text_code, meta_context=meta_code)
    
    if not refs:
        print("❌ LE MOTEUR NE TROUVE RIEN. Le problème vient de rule_engine.py (regex ou logique).")
        return
    else:
        print(f"✅ Le moteur a trouvé {len(refs)} entités :")
        for r in refs:
            print(f"   - Tag: {r.get('tag')} | Val: {r.get('article') or r.get('val')} | Code associé: {r.get('code')}")

    # 2. Test du Slugify
    print("\n--- 2. TEST DU SLUGIFY ---")
    for r in refs:
        code_raw = r.get('code') or r.get('val')
        slug = slugify(code_raw)
        print(f"   Original: '{code_raw}' -> Slug: '{slug}'")
        
        if slug is None:
            print("   ⚠️ ATTENTION : Si le Slug est None, aucun lien ne sera créé !")
            if code_raw == "INCONNU":
                print("      -> C'est normal pour INCONNU. Mais pourquoi est-ce INCONNU si on est dans minier.md ?")

    # 3. Test de l'Injection
    print("\n--- 3. TEST DE L'INJECTION HTML ---")
    html_result = inject_links(text_code, refs)
    print(f"HTML Final : {html_result}")
    
    if "<a data=" in html_result:
        print("✅ SUCCÈS : La balise <a> a été créée.")
    else:
        print("❌ ÉCHEC : Aucune balise <a> n'a été insérée.")
        
    # 4. Test sur un JORF (Cas plus dur)
    print("\n--- 4. TEST SUR UNE PHRASE JORF ---")
    text_jorf = "Vu le code général des impôts et son article 209."
    print(f"Phrase : '{text_jorf}'")
    refs_jorf = engine.extract(text_jorf, meta_context={"source": "jorf.csv", "type": "JORF"})
    
    print(f"Entités trouvées : {len(refs_jorf)}")
    for r in refs_jorf:
        print(f"   - {r}")
        
    html_jorf = inject_links(text_jorf, refs_jorf)
    print(f"HTML JORF : {html_jorf}")

if __name__ == "__main__":
    main()