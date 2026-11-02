#!/usr/bin/env python3
"""
Patch 2 voor Digichecker (index.html):
  1. Subitem naar hoofditem maken door te slepen (rand van een hoofditem)
  2. Items samenvoegen: sleep item A midden op item B en laat los
     -> B behoudt tekst en status; subitems van A gaan mee naar B
        (dubbele subitems met dezelfde tekst worden overgeslagen)

Gebruik:   python patch_digichecker_2.py [pad/naar/index.html]
Maakt eerst een back-up (<bestand>.bak2). Bij een afwijkend bestand
wordt er niets gewijzigd.
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if "cl-drop-merge" in html:
    sys.exit("Al gepatcht (cl-drop-merge bestaat al). Niets gedaan.")

CSS = r"""
        /* patch 2: slepen van checklist-items (voor/na/samenvoegen) */
        .cl-main.cl-drop-before, .cl-sub.cl-drop-before { box-shadow: 0 -3px 0 0 #3b82f6; }
        .cl-main.cl-drop-after,  .cl-sub.cl-drop-after  { box-shadow: 0 3px 0 0 #3b82f6; }
        .cl-main.cl-drop-merge > div:first-child,
        .cl-sub.cl-drop-merge > div:first-child {
            outline: 2px solid #3b82f6;
            background-color: rgba(59, 130, 246, .12);
        }
    """

NEW_JS = r"""// Slepen via handvat: volgorde, subitem -> hoofditem, samenvoegen (patch 2)
        (function setupChecklistSort() {
            const list = document.getElementById('liveChecklist');
            const scroller = list.closest('.overflow-y-auto');
            let drag = null;

            const norm = (s) => ((s && s.text) || '').trim().toLowerCase();

            function clearMarks() {
                list.querySelectorAll('.cl-drop-before, .cl-drop-after, .cl-drop-merge')
                    .forEach(n => n.classList.remove('cl-drop-before', 'cl-drop-after', 'cl-drop-merge'));
            }

            // Bepaalt waar het gesleepte item zou landen: bovenste 25% = ervoor,
            // onderste 25% = erna, midden = samenvoegen.
            function computeDrop(e) {
                const hit = document.elementFromPoint(e.clientX, e.clientY);
                const el = hit && hit.closest ? hit.closest('.cl-main, .cl-sub') : null;
                if (!el || !list.contains(el)) return null;
                if (el === drag.el || drag.el.contains(el)) return null;
                const r = el.firstElementChild.getBoundingClientRect();
                if (e.clientY < r.top || e.clientY > r.bottom) return null;
                const ratio = (e.clientY - r.top) / r.height;
                const zone = ratio < 0.25 ? 'before' : ratio > 0.75 ? 'after' : 'merge';
                // hoofditem op een subitem: alleen samenvoegen toegestaan
                if (!drag.isSub && el.classList.contains('cl-sub') && zone !== 'merge') return null;
                return { el, zone, targetId: el.dataset.id };
            }

            list.addEventListener('pointerdown', (e) => {
                const grip = e.target.closest('.cl-grip');
                if (!grip) return;
                const el = grip.closest('.cl-main, .cl-sub');
                if (!el) return;
                e.preventDefault();
                try { grip.setPointerCapture(e.pointerId); } catch (_) { }
                drag = { el, id: el.dataset.id, isSub: el.classList.contains('cl-sub'), drop: null };
                el.classList.add('is-sorting');
                document.body.style.cursor = 'grabbing';
            });

            list.addEventListener('pointermove', (e) => {
                if (!drag) return;
                if (scroller) {
                    const sr = scroller.getBoundingClientRect();
                    if (e.clientY < sr.top + 40) scroller.scrollTop -= 12;
                    else if (e.clientY > sr.bottom - 40) scroller.scrollTop += 12;
                }
                clearMarks();
                drag.drop = computeDrop(e);
                if (drag.drop) drag.drop.el.classList.add('cl-drop-' + drag.drop.zone);
            });

            const end = async (e) => {
                if (!drag) return;
                const d = drag;
                drag = null;
                d.el.classList.remove('is-sorting');
                document.body.style.cursor = '';
                clearMarks();
                if (e.type === 'pointercancel' || !d.drop) return;
                await applyDrop(d.id, d.drop.targetId, d.drop.zone);
            };
            list.addEventListener('pointerup', end);
            list.addEventListener('pointercancel', end);

            async function applyDrop(dragId, targetId, zone) {
                if (!currentUser || !activeProject) return;
                const projectId = activeProject.id;
                const cl = JSON.parse(JSON.stringify(activeProject.checklist || []));

                const find = (id) => {
                    for (let i = 0; i < cl.length; i++) {
                        if (cl[i].id === id) return { item: cl[i], parent: null, arr: cl, index: i };
                        const subs = cl[i].subitems || [];
                        for (let j = 0; j < subs.length; j++) {
                            if (subs[j].id === id) return { item: subs[j], parent: cl[i], arr: subs, index: j };
                        }
                    }
                    return null;
                };

                const d = find(dragId), t = find(targetId);
                if (!d || !t || d.item === t.item) return;
                if (t.parent && t.parent.id === d.item.id) return;      // hoofditem niet in eigen subitem
                if (!d.parent && t.parent && zone !== 'merge') return;  // geen hoofditem -> subitem via randen

                const dragged = d.item;
                const movedSubs = d.parent ? [] : (dragged.subitems || []);

                // 1. gesleepte item eruit
                d.arr.splice(d.index, 1);
                // 2. doel opnieuw zoeken (indexen kunnen verschoven zijn)
                const t2 = find(targetId);
                if (!t2) return;

                if (zone === 'merge') {
                    // doel behoudt tekst/status; alleen subitems van het gesleepte item komen erbij
                    if (!t2.parent) {
                        const subs = t2.item.subitems = t2.item.subitems || [];
                        const seen = new Set(subs.map(norm));
                        movedSubs.forEach(s => { if (!seen.has(norm(s))) { subs.push(s); seen.add(norm(s)); } });
                    } else {
                        const subs = t2.parent.subitems;
                        const seen = new Set(subs.map(norm));
                        let at = t2.index + 1;
                        movedSubs.forEach(s => { if (!seen.has(norm(s))) { subs.splice(at++, 0, s); seen.add(norm(s)); } });
                    }
                } else {
                    const at = t2.index + (zone === 'after' ? 1 : 0);
                    if (!t2.parent) {
                        if (d.parent) dragged.subitems = [];   // subitem wordt hoofditem
                        cl.splice(at, 0, dragged);
                    } else {
                        t2.parent.subitems.splice(at, 0, dragged);
                    }
                }

                if (JSON.stringify(cl) === JSON.stringify(activeProject.checklist || [])) return;
                try {
                    await updateDoc(projectDoc(projectId), { checklist: cl });
                    if (zone === 'merge') showToast('Items samengevoegd', 'success');
                } catch (err) {
                    showToast('Fout bij opslaan', 'error');
                    renderActiveProjectLiveChecklist();
                }
            }
        })();

        """

START = "// Volgorde wijzigen via sleephandvat (werkt met muis en touch)"
END = "window.toggleItemStatus = async function"

checks = [("</style>", 1), (START, 1), (END, 1), ("function setupChecklistSort()", 1)]
for needle, expected in checks:
    n = html.count(needle)
    if n != expected:
        sys.exit(f"Aanpassingspunt {n}x gevonden (verwacht {expected}x), niets gewijzigd:\n  {needle!r}")

s = html.index(START)
e = html.index(END, s)
html = html[:s] + NEW_JS + html[e:]
html = html.replace("</style>", CSS + "</style>", 1)

shutil.copy(path, path.with_suffix(path.suffix + ".bak2"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak2")
