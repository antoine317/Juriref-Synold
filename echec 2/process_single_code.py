#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Process a single code markdown file with LegalReferenceLinker (test)"""
from inference_and_linking import LegalReferenceLinker
from pathlib import Path

infile = Path('data/codes/action_sociale_familles.md')
outfile = Path('results_v2/codes/action_sociale_familles.md')

linker = LegalReferenceLinker()
text = infile.read_text(encoding='utf-8')
processed = linker.process_text(text, infile.name)
outfile.parent.mkdir(parents=True, exist_ok=True)
outfile.write_text(processed, encoding='utf-8')
linker.print_stats()
linker.save_report()
print('\nFichier traité:', outfile)
