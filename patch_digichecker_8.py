#!/usr/bin/env python3
"""
Patch 8 voor Digichecker (index.html): ingeklapt archief.

Ingeklapt blijft de kolom een smalle balk met "Archief" en daarachter het aantal
projecten (de lijst zelf is verborgen). Alleen CSS; geen afhankelijkheid van
andere patches.

Gebruik:   python patch_digichecker_8.py [pad/naar/index.html]
Back-up:   <bestand>.bak8
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if "patch 8:" in html:
    sys.exit("Al gepatcht. Niets gedaan.")
if html.count("</style>") != 1 or "#col-archive.archive-collapsed" not in html:
    sys.exit("Verwachte opmaak niet gevonden, niets gewijzigd.")

CSS = r"""
        /* patch 8: ingeklapt archief toont titel + aantal */
        #col-archive.archive-collapsed { min-width: 180px; width: 180px; }
        #col-archive.archive-collapsed .archive-label { display: inline; }
        #col-archive.archive-collapsed .archive-title { flex-direction: row; }
        #col-archive.archive-collapsed .kanban-column-header { border-bottom: 0; border-radius: .375rem; }
    """

html = html.replace("</style>", CSS + "</style>", 1)

shutil.copy(path, path.with_suffix(path.suffix + ".bak8"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak8")
