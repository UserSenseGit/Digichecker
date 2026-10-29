#!/usr/bin/env python3
"""
Patch 3 voor Digichecker: nieuwe projecten komen onderaan in de kolom.
Vereist patch 2 (kanban-volgorde).

Gebruik:  python patch_digichecker_nieuw_onderaan.py index.html
Maakt eerst een back-up (<bestand>.bak3). Faalt een patch, dan wordt niets gewijzigd.
"""
import sys
import shutil

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
with open(path, encoding="utf-8", newline="") as f:
    src = f.read()

if "saveBoardOrder" not in src:
    sys.exit("Patch 2 (kanban-volgorde) ontbreekt. Draai die eerst. Niets gewijzigd.")
if "nextOrder" in src:
    sys.exit("Dit bestand lijkt al gepatcht te zijn. Niets gewijzigd.")


def patch(old, new, label):
    global src
    n = src.count(old)
    if n != 1:
        sys.exit(f"[FOUT] '{label}': {n} matches gevonden (verwacht 1). Niets gewijzigd.")
    src = src.replace(old, new)


patch(
    "const btn = document.getElementById('btnSaveNewProject');",
    "const nextOrder = projects.reduce((m, p) => typeof p.order === 'number' ? Math.max(m, p.order) : m, -1) + 1;\n            const btn = document.getElementById('btnSaveNewProject');",
    "nextOrder berekenen",
)

patch(
    "createdAt: serverTimestamp()",
    "createdAt: serverTimestamp(),\n                    order: nextOrder",
    "order opslaan",
)

shutil.copyfile(path, path + ".bak3")
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(src)
print(f"Klaar. Back-up: {path}.bak3")
