#!/usr/bin/env python3
"""
Patch 7 voor Digichecker (index.html), na patch 6: werkhal beter bruikbaar op smartphone.

  * Zoomknoppen (-, % / "passend", +) bij de werkhal; op laptop ook Ctrl + scrollwiel
    (of trackpad-knijpen). Ingezoomd scrol je de plattegrond met je vinger/muis.
  * Bokken schalen mee met de breedte van de plattegrond (nooit kleiner dan 80%).
  * Is de plattegrond smal (< 700 px, bv. telefoon rechtop), dan tonen bokken alleen
    boknummer + vol/leeg + potlood. Zoom je in, dan komen B-nummer, project en
    leverancier vanzelf terug.
  * Knop 'schermvullend': verbergt de header en tabs (en gebruikt waar mogelijk
    de volledige-schermmodus van de browser).

Raakt de code van patch 6 niet aan (staat los ervan).

Gebruik:   python patch_digichecker_7.py [pad/naar/index.html]
Back-up:   <bestand>.bak7
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if 'id="btnZoomIn"' in html:
    sys.exit("Al gepatcht (zoomknoppen bestaan al). Niets gedaan.")
if "(patch 6" not in html:
    sys.exit("Patch 6 niet gevonden. Draai eerst patch_digichecker_6.py. Niets gewijzigd.")

ZBTN = ("bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 border border-zinc-200 "
        "dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 h-10 rounded-md text-sm font-semibold "
        "transition-colors flex items-center justify-center disabled:opacity-40")

CSS = r"""
        /* patch 7: zoom, schaal en schermvullend (werkhal) */
        #werkhalMap .bok { transform: translate(-50%, -50%) scale(var(--bok-scale, 1)); }
        #werkhalMap.bok-compact .bok { min-width: 0; }
        #werkhalMap.bok-compact .bok > div:not(:first-child) { display: none; }
        .werkhal-zoomed {
            max-height: calc(100vh - 150px);
            max-height: calc(100dvh - 150px);
        }
        .werkhal-full .werkhal-zoomed {
            max-height: calc(100vh - 80px);
            max-height: calc(100dvh - 80px);
        }
        .werkhal-full header, .werkhal-full nav { display: none; }
        .werkhal-full #werkhalView { padding: .5rem; gap: .5rem; }
    """

COUNTS_OLD = '<span id="bokCounts" class="ml-auto text-sm text-zinc-500 dark:text-zinc-400"></span>'
COUNTS_NEW = COUNTS_OLD + f"""
                <div class="flex items-center gap-1">
                    <button type="button" id="btnZoomOut" title="Uitzoomen" class="{ZBTN} w-10"><i class="fa-solid fa-magnifying-glass-minus"></i></button>
                    <button type="button" id="btnZoomFit" title="Hele plattegrond" class="{ZBTN} px-3" style="min-width:3.5rem"><span id="zoomLabel">100%</span></button>
                    <button type="button" id="btnZoomIn" title="Inzoomen" class="{ZBTN} w-10"><i class="fa-solid fa-magnifying-glass-plus"></i></button>
                    <button type="button" id="btnFullscreen" title="Schermvullend" class="{ZBTN} w-10"><i class="fa-solid fa-expand" id="fullIcon"></i></button>
                </div>"""

JS = r"""
        // ===== Werkhal: zoom, schaal en schermvullend (patch 7) =====
        (function setupWerkhalZoom() {
            const $ = (id) => document.getElementById(id);
            const map = $('werkhalMap');
            const wrap = map.parentElement;
            const STEPS = [1, 1.5, 2, 3, 4];
            const COMPACT_BELOW = 700;   // px breedte van de plattegrond
            const MIN_SCALE = 0.8;       // bokken worden nooit kleiner dan 80%
            const FULL_AT = 1100;        // vanaf deze breedte zijn bokken 100%
            let zoom = 1;
            let lastWheel = 0;

            // bokken meeschalen / compact maken op basis van de werkelijke breedte
            const ro = new ResizeObserver(() => {
                const w = map.getBoundingClientRect().width;
                const s = Math.min(1, Math.max(MIN_SCALE, w / FULL_AT));
                map.style.setProperty('--bok-scale', s.toFixed(3));
                map.classList.toggle('bok-compact', w < COMPACT_BELOW);
            });
            ro.observe(map);

            function updateUi() {
                $('zoomLabel').textContent = Math.round(zoom * 100) + '%';
                $('btnZoomOut').disabled = zoom <= STEPS[0];
                $('btnZoomIn').disabled = zoom >= STEPS[STEPS.length - 1];
            }

            function setZoom(z) {
                const mw = map.offsetWidth || 1, mh = map.offsetHeight || 1;
                const cx = (wrap.scrollLeft + wrap.clientWidth / 2) / mw;
                const cy = (wrap.scrollTop + wrap.clientHeight / 2) / mh;
                zoom = z;
                if (z > 1) {
                    map.style.maxWidth = 'none';
                    map.style.width = 'calc(min(100%, 2000px) * ' + z + ')';
                } else {
                    map.style.maxWidth = '2000px';
                    map.style.width = '';
                }
                wrap.classList.toggle('werkhal-zoomed', z > 1);
                if (z > 1) {
                    wrap.scrollLeft = cx * map.offsetWidth - wrap.clientWidth / 2;
                    wrap.scrollTop = cy * map.offsetHeight - wrap.clientHeight / 2;
                } else {
                    wrap.scrollLeft = 0;
                    wrap.scrollTop = 0;
                }
                updateUi();
            }

            function step(dir) {
                const i = STEPS.indexOf(zoom);
                const n = Math.min(STEPS.length - 1, Math.max(0, i + dir));
                if (n !== i) setZoom(STEPS[n]);
            }

            $('btnZoomIn').addEventListener('click', () => step(1));
            $('btnZoomOut').addEventListener('click', () => step(-1));
            $('btnZoomFit').addEventListener('click', () => setZoom(1));

            // laptop: Ctrl + scrollwiel (en trackpad-knijpen) op de plattegrond
            wrap.addEventListener('wheel', (e) => {
                if (!e.ctrlKey) return;
                e.preventDefault();
                const now = Date.now();
                if (now - lastWheel < 150) return;
                lastWheel = now;
                step(e.deltaY < 0 ? 1 : -1);
            }, { passive: false });

            // ---------- schermvullend ----------
            function setFull(on) {
                document.body.classList.toggle('werkhal-full', on);
                const ic = $('fullIcon');
                ic.classList.toggle('fa-expand', !on);
                ic.classList.toggle('fa-compress', on);
            }
            async function toggleFull() {
                const on = !document.body.classList.contains('werkhal-full');
                setFull(on);
                try {
                    if (on && document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
                    else if (!on && document.fullscreenElement) await document.exitFullscreen();
                } catch (_) { /* bv. iPhone: alleen de header verbergen */ }
            }
            $('btnFullscreen').addEventListener('click', toggleFull);
            document.addEventListener('fullscreenchange', () => {
                if (!document.fullscreenElement && document.body.classList.contains('werkhal-full')) setFull(false);
            });
            // werkhal verlaten (bv. tik op bok -> bord): schermvullend afsluiten
            new MutationObserver(() => {
                if ($('werkhalView').classList.contains('hidden') && document.body.classList.contains('werkhal-full')) {
                    setFull(false);
                    if (document.fullscreenElement) document.exitFullscreen().catch(() => { });
                }
            }).observe($('werkhalView'), { attributes: true, attributeFilter: ['class'] });

            updateUi();
        })();
"""

for needle in ("</style>", COUNTS_OLD):
    n = html.count(needle)
    if n != 1:
        sys.exit(f"Aanpassingspunt {n}x gevonden (verwacht 1x), niets gewijzigd:\n  {needle[:70]!r}")

idx = html.rfind("</script>")
mod = html.rfind('<script type="module">')
if idx == -1 or mod == -1 or mod > idx:
    sys.exit("Module-script niet gevonden, niets gewijzigd.")

html = html.replace("</style>", CSS + "</style>", 1)
html = html.replace(COUNTS_OLD, COUNTS_NEW, 1)
idx = html.rfind("</script>")
html = html[:idx] + JS + "    " + html[idx:]

shutil.copy(path, path.with_suffix(path.suffix + ".bak7"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak7")
