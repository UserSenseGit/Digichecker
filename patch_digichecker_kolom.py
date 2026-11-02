#!/usr/bin/env python3
"""
Patch voor Digichecker (index.html):
  1. Projectnaam bewerkbaar (klik op de titel in het projectvenster)
  2. Nieuwe kolom 'Werf' tussen 'Gereed' en 'Archief'

Gebruik:   python patch_digichecker.py [pad/naar/index.html]
Er wordt eerst een back-up gemaakt (<bestand>.bak). Als één van de
aanpassingspunten niet gevonden wordt, wordt er NIETS gewijzigd.
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if 'id="col-werf"' in html:
    sys.exit("Al gepatcht (kolom 'Werf' bestaat al). Niets gedaan.")

# ---------------------------------------------------------------- onderdelen
CSS = r"""
        /* patch: Werf-kolom + bewerkbare projecttitel */
        #col-werf .kanban-column-header { border-top: 3px solid #8b5cf6; }
        #modalProjectTitle { cursor: pointer; }
        #modalProjectTitle::after {
            content: "\f303";
            font-family: "Font Awesome 6 Free";
            font-weight: 900;
            font-size: .55em;
            margin-left: .6rem;
            opacity: .35;
            vertical-align: middle;
        }
        #modalProjectTitle:hover::after { opacity: .8; }
    """

WERF_COLUMN = """<!-- Column: Werf -->
                <div class="kanban-column bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-md"
                    id="col-werf" data-status="werf">
                    <div
                        class="kanban-column-header p-3 font-semibold text-zinc-900 dark:text-white flex justify-between items-center bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 rounded-t-md">
                        <div class="flex items-center gap-2">
                            <span>Werf</span>
                            <span
                                class="bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-400 text-xs px-2 py-1 rounded-sm font-bold count-badge">0</span>
                        </div>
                    </div>
                    <div class="kanban-cards-container" data-status="werf"></div>
                </div>

                <!-- Column: Archief -->"""

TITLE_JS = r"""
        // ---- Projecttitel bewerken (patch) ----
        (function setupTitleEdit() {
            const h = document.getElementById('modalProjectTitle');
            h.title = 'Klik om de projectnaam te bewerken';
            h.addEventListener('click', async () => {
                if (!activeProject) return;
                const current = activeProject.title || '';
                const t = await window.openCustomDialog({
                    title: 'Projectnaam bewerken',
                    type: 'prompt',
                    defaultValue: current,
                    confirmText: 'Opslaan'
                });
                if (t === null) return;
                const name = t.trim();
                if (!name || name === current) return;
                h.innerText = name;
                await updateProjectField(activeProject.id, { title: name });
            });
        })();
"""

# ------------------------------------------------- (oud, nieuw) vervangingen
REPLACEMENTS = [
    # CSS
    ("</style>", CSS + "</style>"),
    # Werf-kolom in het bord
    ("<!-- Column: Archief -->", WERF_COLUMN),
    # Statusdropdown in projectvenster
    ('<option value="done">Gereed</option>',
     '<option value="done">Gereed</option>\n                            <option value="werf">Werf</option>'),
    # renderBoard: containers, tellers, badges
    ("'done': document.querySelector('#col-done .kanban-cards-container'),",
     "'done': document.querySelector('#col-done .kanban-cards-container'),\n"
     "                'werf': document.querySelector('#col-werf .kanban-cards-container'),"),
    ("const counts = { 'upcoming': 0, 'atelier': 0, 'done': 0, 'archive': 0 };",
     "const counts = { 'upcoming': 0, 'atelier': 0, 'done': 0, 'werf': 0, 'archive': 0 };"),
    ("document.querySelector('#col-done .count-badge').textContent = counts['done'];",
     "document.querySelector('#col-done .count-badge').textContent = counts['done'];\n"
     "            document.querySelector('#col-werf .count-badge').textContent = counts['werf'];"),
    # Niet automatisch terugzetten naar Gereed als project al op Werf staat
    ("activeProject.status !== 'done' && activeProject.status !== 'archive'",
     "activeProject.status !== 'done' && activeProject.status !== 'werf' && activeProject.status !== 'archive'"),
]

# ------------------------------------------------------------ controleren
for old, _ in REPLACEMENTS:
    n = html.count(old)
    if n != 1:
        sys.exit(f"Aanpassingspunt {n}x gevonden (verwacht 1x), niets gewijzigd:\n  {old[:80]!r}")

# ---------------------------------------------------------- doorvoeren
for old, new in REPLACEMENTS:
    html = html.replace(old, new, 1)

# Titel-JS vlak voor het laatste </script> (= einde van het module-script)
idx = html.rfind("</script>")
if idx == -1:
    sys.exit("Geen </script> gevonden, niets gewijzigd.")
html = html[:idx] + TITLE_JS + "    " + html[idx:]

shutil.copy(path, path.with_suffix(path.suffix + ".bak"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak")
