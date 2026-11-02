#!/usr/bin/env python3
"""
Patch 4 voor Digichecker (index.html), na patch 2 (en eventueel 3):
Een item of subitem dat je midden op een bestaand item loslaat, komt nu als
subitem BINNEN dat item terecht (met behoud van eigen tekst, afvinkstatus en
'Geleverd'). Het wordt dus niet meer weggegooid.

- Doel = hoofditem: nieuw subitem komt onderaan de subitems.
- Doel = subitem: nieuw subitem komt direct na dat subitem (zelfde hoofditem).
- Had het gesleepte item zelf subitems, dan komen die er (plat) achter.
- Subitems met exact dezelfde tekst als al aanwezig worden overgeslagen.

Gebruik:   python patch_digichecker_4.py [pad/naar/index.html]
Back-up: <bestand>.bak4
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if "patch 4:" in html:
    sys.exit("Al gepatcht. Niets gedaan.")

START = "// doel behoudt tekst/status; alleen subitems van het gesleepte item komen erbij"
END = "const at = t2.index + (zone === 'after' ? 1 : 0);"
TOAST = "Items samengevoegd"

for needle in (START, END, TOAST):
    n = html.count(needle)
    if n != 1:
        sys.exit(f"Aanpassingspunt {n}x gevonden (verwacht 1x). Is patch 2 doorgevoerd? Niets gewijzigd:\n  {needle!r}")

s = html.index(START)
e = html.index(END)
if s > e:
    sys.exit("Onverwachte volgorde in het bestand, niets gewijzigd.")

NEW = r"""// patch 4: gesleepte item komt als subitem BINNEN het doel terecht
                    const own = (dragged.subitems || []).filter(x => x.id !== dragged.id);
                    const asSub = {
                        id: dragged.id,
                        text: dragged.text,
                        checked: !!dragged.checked,
                        ...(dragged.delivered ? { delivered: true } : {})
                    };
                    const host = t2.parent || t2.item;
                    const subs = host.subitems = host.subitems || [];
                    const seen = new Set(subs.map(norm));
                    seen.add(norm(host));
                    let at = t2.parent ? t2.index + 1 : subs.length;
                    [asSub, ...own].forEach(x => {
                        const k = norm(x);
                        if (!seen.has(k)) { subs.splice(at++, 0, x); seen.add(k); }
                    });
                } else {
                    """

html = html[:s] + NEW + html[e:]
html = html.replace(TOAST, "Toegevoegd als subitem", 1)

shutil.copy(path, path.with_suffix(path.suffix + ".bak4"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak4")
