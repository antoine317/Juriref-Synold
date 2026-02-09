import sys
from pathlib import Path


from src.generate_full_site import LegalEngine, inject_links, HTML_HEADER, HTML_FOOTER, DIR_CODES, DIR_OUTPUT

f = DIR_CODES / "instruments_monetaires_medailles.md"
if not f.exists():
    print("Source file not found:", f)
    raise SystemExit(1)

engine = LegalEngine()
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

outdir = DIR_OUTPUT / "codes"
outdir.mkdir(parents=True, exist_ok=True)
out_file = outdir / f.name.replace('.md', '.html')
with open(out_file, 'w', encoding='utf-8') as fout:
    fout.write(HTML_HEADER.replace('{title}', f.name) + html + HTML_FOOTER)
print('Wrote', out_file)
