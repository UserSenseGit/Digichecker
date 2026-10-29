#!/usr/bin/env python3
"""
Patch 2 voor Digichecker: projecten op het kanban-bord ordenen.
  - Sleep een kaart binnen een kolom om de volgorde te wijzigen
  - Sleep een kaart naar een andere kolom op een specifieke plek (status + positie)
  - Volgorde wordt opgeslagen (veld 'order') en is zichtbaar voor iedereen
  - Nieuwe projecten komen bovenaan

Gebruik:  python patch_digichecker_kanban_volgorde.py index.html
Werkt op het originele bestand en op het bestand na de eerste patch.
Maakt eerst een back-up (<bestand>.bak2). Faalt een patch, dan wordt niets gewijzigd.
"""
import sys
import shutil

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
with open(path, encoding="utf-8", newline="") as f:
    src = f.read()

if "saveBoardOrder" in src:
    sys.exit("Dit bestand lijkt al gepatcht te zijn. Niets gewijzigd.")


def patch(old, new, label):
    global src
    n = src.count(old)
    if n != 1:
        sys.exit(f"[FOUT] '{label}': {n} matches gevonden (verwacht 1). Niets gewijzigd.")
    src = src.replace(old, new)


# 1. writeBatch importeren
patch(
    "query, serverTimestamp }",
    "query, serverTimestamp, writeBatch }",
    "import writeBatch",
)

# 2. sorteren op 'order' (projecten zonder order: nieuwste bovenaan)
patch(
    "projects.sort((a, b) => (b.createdAt?.toMillis() || Date.now()) - (a.createdAt?.toMillis() || Date.now()));",
    r"""const sortKey = (p) => typeof p.order === 'number' ? p.order : -(p.createdAt?.toMillis() || Date.now());
                projects.sort((a, b) => sortKey(a) - sortKey(b));""",
    "sorteren",
)

# 3. oude drop-logica (enkel status wijzigen) uitschakelen; vervangen door nieuwe
patch(
    "if (newStatus !== draggedCard.dataset.status) {",
    "if (false) { // vervangen door volgorde-logica (patch 2)",
    "oude drop uitschakelen",
)

# 4. nieuwe drag & drop logica voor volgorde
patch(
    "window.openStagingModal = function () {",
    r"""// ---- Kanban: volgorde via slepen (patch 2) ----
        const dropIndicator = document.createElement('div');
        dropIndicator.className = 'h-1 rounded bg-zinc-900 dark:bg-white shrink-0 pointer-events-none';

        document.addEventListener('dragend', () => dropIndicator.remove());

        document.querySelectorAll('.kanban-column').forEach(column => {
            const container = column.querySelector('.kanban-cards-container');

            column.addEventListener('dragover', (e) => {
                if (!draggedCard) return;
                e.preventDefault();
                const cards = Array.from(container.children).filter(c => c.classList.contains('kanban-card') && c !== draggedCard);
                let ref = null;
                for (const c of cards) {
                    const r = c.getBoundingClientRect();
                    if (e.clientY < r.top + r.height / 2) { ref = c; break; }
                }
                if (container.style.display !== 'none') container.insertBefore(dropIndicator, ref);
            });

            column.addEventListener('drop', async (e) => {
                if (!draggedCard) return;
                e.preventDefault();
                const dragged = draggedCard;
                const status = column.dataset.status;
                let ids = [];

                if (getComputedStyle(container).display === 'none') {
                    // ingeklapte kolom (archief): bovenaan plaatsen
                    ids = [dragged.dataset.id, ...projects.filter(p => (p.status || 'upcoming') === status && p.id !== dragged.dataset.id).map(p => p.id)];
                } else {
                    Array.from(container.children).forEach(k => {
                        if (k === dropIndicator) ids.push(dragged.dataset.id);
                        else if (k !== dragged && k.dataset && k.dataset.id) ids.push(k.dataset.id);
                    });
                    if (!ids.includes(dragged.dataset.id)) ids.push(dragged.dataset.id);
                }
                dropIndicator.remove();
                await saveBoardOrder(status, ids);
            });
        });

        async function saveBoardOrder(status, ids) {
            if (!currentUser) return;
            const batch = writeBatch(db);
            let changes = 0;
            ids.forEach((id, i) => {
                const p = projects.find(x => x.id === id);
                if (!p) return;
                const fields = {};
                if (p.order !== i) fields.order = i;
                if ((p.status || 'upcoming') !== status) fields.status = status;
                if (Object.keys(fields).length) { batch.update(projectDoc(id), fields); changes++; }
            });
            if (!changes) return;
            try { await batch.commit(); }
            catch (e) { showToast("Fout bij opslaan volgorde: " + (e.code || e.message), "error"); }
        }

        window.openStagingModal = function () {""",
    "kanban sorteren",
)

shutil.copyfile(path, path + ".bak2")
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(src)
print(f"Klaar. Back-up: {path}.bak2")
