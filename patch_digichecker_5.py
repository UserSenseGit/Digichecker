#!/usr/bin/env python3
"""
Patch 5 voor Digichecker (index.html): module "Werkhal / glasbokken".

  * Tabs "Bord" | "Werkhal" onder de header (ook direct te openen via index.html#werkhal,
    bv. in een tweede venster; beide vensters blijven live gesynchroniseerd).
  * Werkhal: plattegrond-afbeelding (uploadbaar), glasbokken slepen/plaatsen,
    op elke bok: boknummer, vol/leeg-knop, B-nummer + projectnaam, leverancier.
  * Tik op een bok  -> springt naar het Bord en opent het gekoppelde project.
  * Sleep een bok   -> verplaatst (positie in %, schaalt mee met de afbeelding).
  * Nog niet geplaatste bokken staan in een bakje boven de plattegrond.
  * In het projectvenster: rij "Glas" met de bokken van dat project; klik = toon op
    plattegrond; "+ Glasbok" = nieuwe bok voor dit project (leverancier + boknummer).

Opslag (Firestore, workspace 'a-frames'):
  glasbokken/{id}   {boknummer, leverancier, projectId, bNummer, status, posX, posY}
  config/werkhal    {image}   (plattegrond als gecomprimeerde JPEG data-URL)

Gebruik:   python patch_digichecker_5.py [pad/naar/index.html]
Back-up:   <bestand>.bak5
Bij een afwijkend bestand wordt er niets gewijzigd.
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if 'id="werkhalView"' in html:
    sys.exit("Al gepatcht (werkhalView bestaat al). Niets gedaan.")

INPUT = ("w-full p-2 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 "
         "text-zinc-900 dark:text-white rounded-md outline-none "
         "focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white")
LABEL = "block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
BTN2 = ("bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 border border-zinc-200 "
        "dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 px-4 py-2 rounded-md font-medium text-sm "
        "transition-colors flex items-center gap-2")

# ------------------------------------------------------------------ CSS
CSS = r"""
        /* patch 5: werkhal / glasbokken */
        .view-tab {
            padding: .65rem 1rem; font-size: .875rem; font-weight: 500; color: #71717a;
            border-bottom: 2px solid transparent; background: transparent;
        }
        .view-tab:hover { color: #18181b; }
        .dark .view-tab:hover { color: #fff; }
        .view-tab.active { color: #18181b; border-bottom-color: #18181b; }
        .dark .view-tab.active { color: #fff; border-bottom-color: #fff; }
        #bokModal { z-index: 75 !important; }
        .bok {
            position: absolute; transform: translate(-50%, -50%); touch-action: none; cursor: grab;
            user-select: none; -webkit-user-select: none; min-width: 130px; max-width: 200px; z-index: 10;
        }
        .bok.bok-static { position: relative; transform: none; left: auto; top: auto; }
        .bok.is-dragging { cursor: grabbing; z-index: 40; box-shadow: 0 8px 20px rgba(0,0,0,.35); }
        .bok-flash { animation: bokflash 1s ease-in-out 3; }
        @keyframes bokflash {
            0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0); }
            50% { box-shadow: 0 0 0 8px rgba(59,130,246,.65); }
        }
    """

# ------------------------------------------------------------------ HTML
NAV = """</header>

    <nav class="bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 px-4 sm:px-6">
        <div class="max-w-7xl mx-auto flex gap-2">
            <button type="button" class="view-tab active" data-view="bord"><i class="fa-solid fa-table-columns mr-2"></i>Bord</button>
            <button type="button" class="view-tab" data-view="werkhal"><i class="fa-solid fa-warehouse mr-2"></i>Werkhal</button>
        </div>
    </nav>"""

WERKHAL_VIEW = """</main>

        <!-- Werkhal: glasbokken op plattegrond -->
        <main id="werkhalView" class="hidden flex-grow p-4 sm:p-6 max-w-full flex flex-col gap-4">
            <div class="flex flex-wrap items-center gap-2">
                <button id="btnAddBok" type="button"
                    class="bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 px-4 py-2 rounded-md shadow-sm font-medium transition-colors flex items-center gap-2 text-sm">
                    <i class="fa-solid fa-plus"></i><span>Glasbok</span>
                </button>
                <button id="btnPickPlan" type="button" class="{BTN2}">
                    <i class="fa-regular fa-image"></i><span>Plattegrond kiezen</span>
                </button>
                <input id="planFileInput" type="file" accept="image/*" class="hidden">
                <span id="bokCounts" class="ml-auto text-sm text-zinc-500 dark:text-zinc-400"></span>
            </div>

            <div id="bokTray" class="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md p-3" style="display:none">
                <div class="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2">Nog niet geplaatst &ndash; sleep naar de plattegrond</div>
                <div id="bokTrayList" class="flex flex-wrap gap-3"></div>
            </div>

            <div class="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md p-2 overflow-auto">
                <div id="werkhalMap" class="relative mx-auto" style="max-width:1600px;">
                    <img id="werkhalImg" alt="Plattegrond werkhal" draggable="false" style="display:none; width:100%; height:auto; user-select:none;">
                    <div id="werkhalEmpty" class="p-10 text-center text-sm text-zinc-500 dark:text-zinc-400">
                        Nog geen plattegrond. Kies een afbeelding van de werkhal via "Plattegrond kiezen".
                    </div>
                </div>
            </div>
        </main>""".replace("{BTN2}", BTN2)

STRIP = '<div id="glasStrip" class="mb-4 flex flex-wrap items-center gap-2"></div>\n                    <div id="liveChecklist" class="space-y-2 flex-grow pb-8">'

BOK_MODAL = """<!-- Glasbok Modal -->
    <div id="bokModal"
        class="fixed inset-0 modal-overlay z-50 flex items-center justify-center hidden opacity-0 transition-opacity duration-300">
        <div
            class="bg-white dark:bg-zinc-900 rounded-md border border-zinc-200 dark:border-zinc-800 shadow-2xl p-6 max-w-md w-full mx-4 transform scale-95 transition-transform duration-300 flex flex-col max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-4">
                <h2 id="bokModalTitle" class="text-xl font-bold text-zinc-900 dark:text-white">Glasbok</h2>
                <button type="button" onclick="hideModal('bokModal')" class="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300">
                    <i class="fa-solid fa-xmark text-xl"></i>
                </button>
            </div>
            <div class="space-y-3">
                <div>
                    <label class="{LABEL}">Boknummer</label>
                    <input id="bokNummer" type="text" class="{INPUT}">
                </div>
                <div>
                    <label class="{LABEL}">Leverancier</label>
                    <input id="bokLeverancier" type="text" list="bokLevList" class="{INPUT}">
                    <datalist id="bokLevList"></datalist>
                </div>
                <div>
                    <label class="{LABEL}">Project</label>
                    <select id="bokProject" class="{INPUT}"></select>
                </div>
                <div>
                    <label class="{LABEL}">B-nummer</label>
                    <input id="bokBNummer" type="text" list="bokBList" placeholder="bv. B261342" class="{INPUT}">
                    <datalist id="bokBList"></datalist>
                </div>
                <div>
                    <label class="{LABEL}">Status</label>
                    <select id="bokStatus" class="{INPUT}">
                        <option value="leeg">Leeg</option>
                        <option value="vol">Vol</option>
                    </select>
                </div>
            </div>
            <div class="mt-6 pt-4 border-t border-zinc-200 dark:border-zinc-800 flex flex-wrap justify-between gap-2">
                <div class="flex gap-2">
                    <button id="btnBokDelete" type="button" title="Verwijderen"
                        class="text-red-500 hover:text-red-700 dark:text-red-400 p-2.5 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                        <i class="fa-regular fa-trash-can text-lg"></i>
                    </button>
                    <button id="btnBokUnplace" type="button" class="{BTN2}" style="display:none">
                        <i class="fa-solid fa-eject"></i><span>Van plattegrond halen</span>
                    </button>
                </div>
                <div class="flex gap-2">
                    <button type="button" onclick="hideModal('bokModal')"
                        class="px-4 py-2 border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-sm font-medium">Annuleren</button>
                    <button id="btnBokSave" type="button"
                        class="bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 px-5 py-2 rounded-md text-sm font-medium shadow transition-colors">Opslaan</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Notification Toast -->""".replace("{LABEL}", LABEL).replace("{INPUT}", INPUT).replace("{BTN2}", BTN2)

# ------------------------------------------------------------------ JS
JS = r"""
        // ===== Werkhal / glasbokken (patch 5) =====
        (function setupWerkhal() {
            const $ = (id) => document.getElementById(id);
            const bokCol = () => collection(db, 'workspaces', WORKSPACE_ID, 'glasbokken');
            const bokDoc = (id) => doc(db, 'workspaces', WORKSPACE_ID, 'glasbokken', id);
            const planDoc = () => doc(db, 'workspaces', WORKSPACE_ID, 'config', 'werkhal');

            let bokken = [];
            let planImage = null;
            let unsubBokken = null, unsubPlan = null;
            let dragging = false, pendingRender = false;
            let editBok = null;

            const isPlaced = (b) => typeof b.posX === 'number' && typeof b.posY === 'number';
            const clampPct = (n) => Math.min(100, Math.max(0, n));
            const round2 = (n) => Math.round(n * 100) / 100;
            const projectOf = (b) => projects.find(p => p.id === b.projectId) || null;

            // ---------- weergave wisselen ----------
            function switchView(v) {
                document.querySelector('main:not(#werkhalView)').classList.toggle('hidden', v !== 'bord');
                $('werkhalView').classList.toggle('hidden', v !== 'werkhal');
                document.querySelectorAll('.view-tab').forEach(t => t.classList.toggle('active', t.dataset.view === v));
                try { history.replaceState(null, '', v === 'werkhal' ? '#werkhal' : location.pathname + location.search); } catch (_) { }
                if (v === 'werkhal') renderWerkhal();
            }
            document.querySelectorAll('.view-tab').forEach(t => t.addEventListener('click', () => switchView(t.dataset.view)));
            window.addEventListener('hashchange', () => switchView(location.hash === '#werkhal' ? 'werkhal' : 'bord'));

            // ---------- marker bouwen ----------
            function buildMarker(b) {
                const p = projectOf(b);
                const vol = b.status === 'vol';
                const el = document.createElement('div');
                el.dataset.bokId = b.id;
                el.className = 'bok rounded-md border-2 shadow-md px-2 py-1 ' + (vol
                    ? 'bg-amber-500 border-amber-600 text-zinc-900'
                    : 'bg-white border-emerald-500 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100');
                el.innerHTML =
                    '<div class="flex items-center gap-1.5">' +
                        '<span class="font-bold text-xs truncate flex-grow">' + esc(b.boknummer || 'Bok') + '</span>' +
                        '<button type="button" class="bok-status text-[10px] font-bold px-2 py-1 rounded-sm border ' +
                            (vol ? 'bg-zinc-900 text-white border-zinc-900' : 'bg-emerald-500 text-white border-emerald-600') +
                            '" title="Wisselen tussen vol en leeg">' + (vol ? 'VOL' : 'LEEG') + '</button>' +
                        '<button type="button" class="bok-edit p-1.5 rounded-sm hover:bg-black/10" title="Bewerken"><i class="fa-solid fa-pen text-[10px]"></i></button>' +
                    '</div>' +
                    '<div class="text-[11px] leading-tight truncate font-medium">' +
                        (b.bNummer ? esc(b.bNummer) + ' \u00b7 ' : '') + esc(p ? p.title : 'Geen project') + '</div>' +
                    (b.leverancier ? '<div class="text-[10px] leading-tight opacity-70 truncate">' + esc(b.leverancier) + '</div>' : '');
                return el;
            }

            function wireButtons(el, b) {
                el.querySelector('.bok-status').addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (!currentUser) return;
                    updateDoc(bokDoc(b.id), { status: b.status === 'vol' ? 'leeg' : 'vol' })
                        .catch(() => showToast('Fout bij wijzigen status', 'error'));
                });
                el.querySelector('.bok-edit').addEventListener('click', (e) => {
                    e.stopPropagation();
                    openBokModal(b);
                });
            }

            // tik op bok: naar het project op het bord
            function tapBok(b) {
                const p = projectOf(b);
                if (p) { switchView('bord'); openProjectModal(p); }
                else openBokModal(b);
            }

            // ---------- slepen op de plattegrond ----------
            function wireMarker(el, b) {
                wireButtons(el, b);
                let st = null;
                el.addEventListener('pointerdown', (e) => {
                    if (e.target.closest('button')) return;
                    e.preventDefault();
                    try { el.setPointerCapture(e.pointerId); } catch (_) { }
                    const r = el.getBoundingClientRect();
                    st = {
                        sx: e.clientX, sy: e.clientY,
                        offX: e.clientX - (r.left + r.width / 2),
                        offY: e.clientY - (r.top + r.height / 2),
                        moved: false, x: b.posX, y: b.posY
                    };
                });
                el.addEventListener('pointermove', (e) => {
                    if (!st) return;
                    if (!st.moved && Math.hypot(e.clientX - st.sx, e.clientY - st.sy) < 6) return;
                    st.moved = true; dragging = true;
                    el.classList.add('is-dragging');
                    const mr = $('werkhalMap').getBoundingClientRect();
                    st.x = clampPct(((e.clientX - st.offX) - mr.left) / mr.width * 100);
                    st.y = clampPct(((e.clientY - st.offY) - mr.top) / mr.height * 100);
                    el.style.left = st.x + '%';
                    el.style.top = st.y + '%';
                });
                const finish = (e) => {
                    if (!st) return;
                    const s = st; st = null;
                    el.classList.remove('is-dragging');
                    dragging = false;
                    if (e.type === 'pointercancel') { pendingRender = false; renderWerkhal(); return; }
                    if (s.moved) {
                        pendingRender = false;
                        updateDoc(bokDoc(b.id), { posX: round2(s.x), posY: round2(s.y) })
                            .catch(() => { showToast('Fout bij opslaan positie', 'error'); renderWerkhal(); });
                    } else {
                        if (pendingRender) { pendingRender = false; renderWerkhal(); }
                        tapBok(b);
                    }
                };
                el.addEventListener('pointerup', finish);
                el.addEventListener('pointercancel', finish);
            }

            // ---------- slepen vanuit het bakje (nog niet geplaatst) ----------
            function wireTray(el, b) {
                wireButtons(el, b);
                let st = null, ghost = null;
                el.addEventListener('pointerdown', (e) => {
                    if (e.target.closest('button')) return;
                    e.preventDefault();
                    try { el.setPointerCapture(e.pointerId); } catch (_) { }
                    st = { sx: e.clientX, sy: e.clientY, moved: false };
                });
                el.addEventListener('pointermove', (e) => {
                    if (!st) return;
                    if (!st.moved) {
                        if (Math.hypot(e.clientX - st.sx, e.clientY - st.sy) < 6) return;
                        st.moved = true; dragging = true;
                        ghost = buildMarker(b);
                        ghost.style.position = 'fixed';
                        ghost.style.pointerEvents = 'none';
                        ghost.style.zIndex = '200';
                        document.body.appendChild(ghost);
                    }
                    ghost.style.left = e.clientX + 'px';
                    ghost.style.top = e.clientY + 'px';
                });
                const finish = (e) => {
                    if (!st) return;
                    const s = st; st = null;
                    if (ghost) { ghost.remove(); ghost = null; }
                    dragging = false;
                    if (e.type === 'pointercancel') { pendingRender = false; renderWerkhal(); return; }
                    if (s.moved) {
                        pendingRender = false;
                        const mr = $('werkhalMap').getBoundingClientRect();
                        const inside = planImage && e.clientX >= mr.left && e.clientX <= mr.right &&
                                       e.clientY >= mr.top && e.clientY <= mr.bottom;
                        if (inside) {
                            const x = clampPct((e.clientX - mr.left) / mr.width * 100);
                            const y = clampPct((e.clientY - mr.top) / mr.height * 100);
                            updateDoc(bokDoc(b.id), { posX: round2(x), posY: round2(y) })
                                .catch(() => showToast('Fout bij opslaan positie', 'error'));
                        } else {
                            if (!planImage) showToast('Kies eerst een plattegrond', 'error');
                            renderWerkhal();
                        }
                    } else {
                        if (pendingRender) { pendingRender = false; renderWerkhal(); }
                        tapBok(b);
                    }
                };
                el.addEventListener('pointerup', finish);
                el.addEventListener('pointercancel', finish);
            }

            // ---------- renderen ----------
            function renderWerkhal() {
                if (dragging) { pendingRender = true; return; }
                const map = $('werkhalMap'), img = $('werkhalImg');
                if (planImage) {
                    if (img.getAttribute('src') !== planImage) img.setAttribute('src', planImage);
                    img.style.display = 'block';
                    $('werkhalEmpty').style.display = 'none';
                } else {
                    img.removeAttribute('src');
                    img.style.display = 'none';
                    $('werkhalEmpty').style.display = '';
                }
                map.querySelectorAll('.bok').forEach(n => n.remove());
                const tray = $('bokTrayList');
                tray.innerHTML = '';
                let nVol = 0, nLeeg = 0;
                bokken.forEach(b => {
                    if (b.status === 'vol') nVol++; else nLeeg++;
                    const el = buildMarker(b);
                    if (planImage && isPlaced(b)) {
                        el.style.left = clampPct(b.posX) + '%';
                        el.style.top = clampPct(b.posY) + '%';
                        wireMarker(el, b);
                        map.appendChild(el);
                    } else {
                        el.classList.add('bok-static');
                        wireTray(el, b);
                        tray.appendChild(el);
                    }
                });
                $('bokTray').style.display = tray.children.length ? '' : 'none';
                $('bokCounts').textContent = bokken.length
                    ? nVol + ' vol \u00b7 ' + nLeeg + ' leeg \u00b7 ' + bokken.length + ' totaal' : '';
                refreshBokLists();
            }

            // ---------- Glas-rij in het projectvenster ----------
            function renderGlasStrip() {
                const box = $('glasStrip');
                if (!box) return;
                box.innerHTML = '';
                if (!activeProject) return;
                const label = document.createElement('span');
                label.className = 'text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mr-1';
                label.innerHTML = '<i class="fa-solid fa-border-all mr-1"></i>Glas';
                box.appendChild(label);
                bokken.filter(b => b.projectId === activeProject.id).forEach(b => {
                    const vol = b.status === 'vol';
                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.title = 'Toon op plattegrond';
                    chip.className = 'text-xs font-medium px-2.5 py-1.5 rounded-md border flex items-center gap-2 transition-colors ' + (vol
                        ? 'bg-amber-100 border-amber-400 text-amber-900 dark:bg-amber-900/30 dark:border-amber-600 dark:text-amber-200'
                        : 'bg-emerald-50 border-emerald-400 text-emerald-900 dark:bg-emerald-900/20 dark:border-emerald-600 dark:text-emerald-200');
                    chip.innerHTML =
                        '<span class="font-bold">' + esc(b.boknummer || 'Bok') + '</span>' +
                        (b.leverancier ? '<span>' + esc(b.leverancier) + '</span>' : '') +
                        (b.bNummer ? '<span>' + esc(b.bNummer) + '</span>' : '') +
                        '<span class="font-bold">' + (vol ? 'VOL' : 'LEEG') + '</span>';
                    chip.addEventListener('click', () => goToBok(b.id));
                    box.appendChild(chip);
                });
                const add = document.createElement('button');
                add.type = 'button';
                add.className = 'text-xs font-medium px-2.5 py-1.5 rounded-md border border-zinc-300 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 flex items-center gap-1 transition-colors';
                add.innerHTML = '<i class="fa-solid fa-plus"></i> Glasbok';
                add.addEventListener('click', () => openBokModal(null, activeProject.id));
                box.appendChild(add);
            }

            function goToBok(id) {
                hideModal('projectModal');
                switchView('werkhal');
                setTimeout(() => {
                    const el = document.querySelector('[data-bok-id="' + id + '"]');
                    if (!el) return;
                    el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
                    el.classList.add('bok-flash');
                    setTimeout(() => el.classList.remove('bok-flash'), 3200);
                }, 150);
            }

            // ---------- glasbok-venster ----------
            function refreshBokLists() {
                const lev = new Set(bokken.map(b => (b.leverancier || '').trim()).filter(Boolean));
                $('bokLevList').innerHTML = Array.from(lev).map(x => '<option value="' + esc(x) + '"></option>').join('');
            }

            function fillProjectSelect(selectedId) {
                const list = projects
                    .filter(p => p.status !== 'archive' || p.id === selectedId)
                    .sort((a, b) => (a.title || '').localeCompare(b.title || '', 'nl', { numeric: true }));
                const s = $('bokProject');
                s.innerHTML = '<option value="">\u2014 geen project \u2014</option>' +
                    list.map(p => '<option value="' + esc(p.id) + '">' + esc(p.title || 'Project') + '</option>').join('');
                s.value = selectedId || '';
            }

            // suggesties voor B-nummer: alle B-nummers uit de checklist van het gekozen project
            function refreshBNummerList() {
                const p = projects.find(x => x.id === $('bokProject').value);
                const found = new Set();
                const scan = (t) => (String(t || '').match(/\bB\d{6}\b/gi) || []).forEach(x => found.add(x.toUpperCase()));
                if (p) (p.checklist || []).forEach(i => { scan(i.text); (i.subitems || []).forEach(s => scan(s.text)); });
                $('bokBList').innerHTML = Array.from(found).map(x => '<option value="' + x + '"></option>').join('');
            }
            $('bokProject').addEventListener('change', refreshBNummerList);

            function openBokModal(b, presetProjectId) {
                editBok = b ? { id: b.id } : { id: null };
                $('bokModalTitle').textContent = b ? 'Glasbok bewerken' : 'Nieuwe glasbok';
                $('bokNummer').value = b ? (b.boknummer || '') : '';
                $('bokLeverancier').value = b ? (b.leverancier || '') : '';
                $('bokBNummer').value = b ? (b.bNummer || '') : '';
                $('bokStatus').value = b && b.status === 'vol' ? 'vol' : 'leeg';
                fillProjectSelect(b ? b.projectId : presetProjectId);
                refreshBNummerList();
                $('btnBokDelete').style.display = b ? '' : 'none';
                $('btnBokUnplace').style.display = b && isPlaced(b) ? '' : 'none';
                showModal('bokModal');
                setTimeout(() => $('bokNummer').focus(), 350);
            }

            $('btnAddBok').addEventListener('click', () => openBokModal(null));

            $('btnBokSave').addEventListener('click', async () => {
                if (!currentUser || !editBok) return;
                const boknummer = $('bokNummer').value.trim();
                if (!boknummer) { showToast('Vul een boknummer in', 'error'); return; }
                const data = {
                    boknummer,
                    leverancier: $('bokLeverancier').value.trim(),
                    projectId: $('bokProject').value || null,
                    bNummer: $('bokBNummer').value.trim().toUpperCase(),
                    status: $('bokStatus').value === 'vol' ? 'vol' : 'leeg'
                };
                try {
                    if (editBok.id) await updateDoc(bokDoc(editBok.id), data);
                    else await addDoc(bokCol(), { ...data, posX: null, posY: null, createdAt: serverTimestamp() });
                    hideModal('bokModal');
                } catch (e) { showToast('Fout bij opslaan: ' + (e.code || e.message), 'error'); }
            });

            $('btnBokUnplace').addEventListener('click', async () => {
                if (!currentUser || !editBok || !editBok.id) return;
                try {
                    await updateDoc(bokDoc(editBok.id), { posX: null, posY: null });
                    hideModal('bokModal');
                } catch (e) { showToast('Fout: ' + (e.code || e.message), 'error'); }
            });

            $('btnBokDelete').addEventListener('click', async () => {
                if (!currentUser || !editBok || !editBok.id) return;
                const ok = await window.openCustomDialog({
                    title: 'Glasbok verwijderen',
                    message: 'Deze glasbok definitief verwijderen?',
                    type: 'confirm', isDanger: true, confirmText: 'Verwijderen'
                });
                if (!ok) return;
                try {
                    await deleteDoc(bokDoc(editBok.id));
                    hideModal('bokModal');
                } catch (e) { showToast('Fout bij verwijderen: ' + (e.code || e.message), 'error'); }
            });

            // ---------- plattegrond uploaden ----------
            function compressPlan(file, maxDim, quality) {
                return new Promise((resolve, reject) => {
                    const fr = new FileReader();
                    fr.onerror = reject;
                    fr.onload = (ev) => {
                        const img = new Image();
                        img.onerror = reject;
                        img.onload = () => {
                            const s = Math.min(1, maxDim / Math.max(img.width, img.height));
                            const w = Math.round(img.width * s), h = Math.round(img.height * s);
                            const c = document.createElement('canvas');
                            c.width = w; c.height = h;
                            const ctx = c.getContext('2d');
                            ctx.fillStyle = '#fff';
                            ctx.fillRect(0, 0, w, h);
                            ctx.drawImage(img, 0, 0, w, h);
                            resolve(c.toDataURL('image/jpeg', quality));
                        };
                        img.src = ev.target.result;
                    };
                    fr.readAsDataURL(file);
                });
            }

            $('btnPickPlan').addEventListener('click', () => $('planFileInput').click());
            $('planFileInput').addEventListener('change', async (e) => {
                const f = e.target.files && e.target.files[0];
                e.target.value = '';
                if (!f || !currentUser) return;
                try {
                    let data = null;
                    for (const [dim, q] of [[1600, 0.75], [1400, 0.65], [1200, 0.55]]) {
                        data = await compressPlan(f, dim, q);
                        if (data.length < 900000) break;
                        data = null;
                    }
                    if (!data) { showToast('Afbeelding is te groot, gebruik een kleinere', 'error'); return; }
                    await setDoc(planDoc(), { image: data, updatedAt: serverTimestamp() }, { merge: true });
                    showToast('Plattegrond opgeslagen', 'success');
                } catch (err) { showToast('Fout bij opslaan plattegrond: ' + (err.code || err.message), 'error'); }
            });

            // ---------- Firestore ----------
            function stopGlas() {
                if (unsubBokken) { unsubBokken(); unsubBokken = null; }
                if (unsubPlan) { unsubPlan(); unsubPlan = null; }
                bokken = []; planImage = null;
                renderWerkhal(); renderGlasStrip();
            }
            function startGlas() {
                stopGlas();
                unsubBokken = onSnapshot(query(bokCol()), (snap) => {
                    const list = [];
                    snap.forEach(d => list.push({ id: d.id, ...d.data() }));
                    list.sort((a, b) => String(a.boknummer || '').localeCompare(String(b.boknummer || ''), 'nl', { numeric: true }));
                    bokken = list;
                    renderWerkhal(); renderGlasStrip();
                }, (err) => showToast('Glasbokken: ' + err.code, 'error'));
                unsubPlan = onSnapshot(planDoc(), (d) => {
                    planImage = d.exists() ? (d.data().image || null) : null;
                    renderWerkhal();
                }, (err) => showToast('Plattegrond: ' + err.code, 'error'));
            }
            onAuthStateChanged(auth, (u) => { if (u) startGlas(); else stopGlas(); });

            // ---------- inhaken op bestaande functies ----------
            const _openProject = openProjectModal;
            openProjectModal = function (p) { _openProject(p); renderGlasStrip(); };
            const _renderBoard = renderBoard;
            renderBoard = function () { _renderBoard(); renderWerkhal(); renderGlasStrip(); };

            switchView(location.hash === '#werkhal' ? 'werkhal' : 'bord');
        })();
"""

# ------------------------------------------------------- aanpassingspunten
REPLACEMENTS = [
    ("updateDoc, deleteDoc, doc, onSnapshot,", "updateDoc, deleteDoc, setDoc, doc, onSnapshot,"),
    ("</style>", CSS + "</style>"),
    ("</header>", NAV),
    ("</main>", WERKHAL_VIEW),
    ('<div id="liveChecklist" class="space-y-2 flex-grow pb-8">', STRIP),
    ("<!-- Notification Toast -->", BOK_MODAL),
]

for old, _ in REPLACEMENTS:
    n = html.count(old)
    if n != 1:
        sys.exit(f"Aanpassingspunt {n}x gevonden (verwacht 1x), niets gewijzigd:\n  {old[:70]!r}")

idx = html.rfind("</script>")
mod = html.rfind('<script type="module">')
if idx == -1 or mod == -1 or mod > idx:
    sys.exit("Module-script niet gevonden, niets gewijzigd.")

for old, new in REPLACEMENTS:
    html = html.replace(old, new, 1)

idx = html.rfind("</script>")
html = html[:idx] + JS + "    " + html[idx:]

shutil.copy(path, path.with_suffix(path.suffix + ".bak5"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak5")
print("LET OP: voeg Firestore-regels toe voor 'glasbokken' en 'config' (zie uitleg).")
