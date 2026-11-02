#!/usr/bin/env python3
"""
Patch 3 voor Digichecker (index.html), na patch 2:
Bij samenvoegen verdwijnt een bestelnummer (bv. B261342) nooit meer.
Staat het nummer van het gesleepte item nog niet bij het doel (tekst of
subitems), dan wordt het gesleepte item als afvinkbaar subitem van het
doel bewaard (met afvinkstatus en 'Geleverd').

Gebruik:   python patch_digichecker_3.py [pad/naar/index.html]
Back-up: <bestand>.bak3
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if "const BNR =" in html:
    sys.exit("Al gepatcht. Niets gedaan.")

ANCHOR = "const movedSubs = d.parent ? [] : (dragged.subitems || []);"
n = html.count(ANCHOR)
if n != 1:
    sys.exit(f"Aanpassingspunt {n}x gevonden (verwacht 1x). Is patch 2 doorgevoerd? Niets gewijzigd.")

NEW = ANCHOR + r"""

                // bestelnummers (B + 6 cijfers) mogen nooit verloren gaan bij samenvoegen
                if (zone === 'merge') {
                    const BNR = /\bB\d{6}\b/gi;
                    const nums = (s) => (String(s || '').match(BNR) || []).map(x => x.toUpperCase());
                    const block = t.parent || t.item;
                    const have = new Set([block.text, ...(block.subitems || []).map(s => s.text), ...movedSubs.map(s => s.text)].flatMap(nums));
                    if (nums(dragged.text).some(x => !have.has(x))) {
                        movedSubs.unshift({
                            id: dragged.id,
                            text: dragged.text,
                            checked: !!dragged.checked,
                            ...(dragged.delivered ? { delivered: true } : {})
                        });
                    }
                }"""

html = html.replace(ANCHOR, NEW, 1)

shutil.copy(path, path.with_suffix(path.suffix + ".bak3"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak3")
