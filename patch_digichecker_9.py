#!/usr/bin/env python3
"""
Patch 9 voor Digichecker (index.html), na patch 6 (patch 7 mag al gedraaid zijn).
Vervangt de werkhal-code van patch 6 en het bok-venster.

  1. Tik op een bok op de plattegrond -> bok komt naar de voorgrond, op volle grootte,
     met alle details (ook op smal scherm). Tik nogmaals op dezelfde bok -> naar het
     project (bij meerdere projecten: keuzelijstje). Tik naast de bok of Esc -> terug.
  2. Status is nu BEZET / LEEG (oude waarde 'vol' wordt automatisch als bezet gelezen).
     Status staat zichtbaar op de bok: grote rode/groene knop + dikke gekleurde rand
     links. Tik op de knop om te wisselen.
  3. Het zijn bokken (niet alleen glas): teksten aangepast ("Bok", "Bokken").
  4. Leveranciers in een dropdown (hard-gecodeerd, zie LEVERANCIERS bovenaan het script),
     met logo op de kaart en de kaart in de kleur van de leverancier.
     Logo-bestanden: <leveranciersnaam>.png of .jpg in dezelfde map als index.html,
     bv. "AID Glass Bv.png". Er wordt eerst .png, dan .jpg geprobeerd.

De Firestore-collectie blijft 'glasbokken' heten (geen nieuwe regels nodig).

Gebruik:   python patch_digichecker_9.py [pad/naar/index.html]
Back-up:   <bestand>.bak9
Bij een afwijkend bestand wordt er niets gewijzigd.
"""
import shutil
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not path.exists():
    sys.exit(f"Bestand niet gevonden: {path}")

html = path.read_text(encoding="utf-8")

if "(patch 9)" in html:
    sys.exit("Al gepatcht (patch 9). Niets gedaan.")
P6 = "// ===== Werkhal / glasbokken (patch 6: meerdere projecten per bok, vaste plattegrond) ====="
if P6 not in html:
    sys.exit("Patch 6 niet gevonden. Draai eerst patch_digichecker_6.py. Niets gewijzigd.")

INPUT = ("w-full p-2 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 "
         "text-zinc-900 dark:text-white rounded-md outline-none "
         "focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white")
LABEL = "block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1"
BTN2 = ("bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 border border-zinc-200 "
        "dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 px-3 py-1.5 rounded-md font-medium text-sm "
        "transition-colors flex items-center gap-2")

# ------------------------------------------------------------------ CSS
CSS = r"""
        /* patch 9: bok naar voorgrond, status, leveranciers */
        #werkhalMap .bok.is-dragging { z-index: 70; }
        #werkhalMap .bok.bok-selected {
            --bok-scale: 1;
            z-index: 60;
            min-width: 230px;
            max-width: 320px;
            box-shadow: 0 0 0 3px #3b82f6, 0 12px 28px rgba(0,0,0,.45);
        }
        #werkhalMap.bok-compact .bok.bok-selected > div:not(:first-child) { display: block; }
        #werkhalMap .bok.bok-selected .truncate { white-space: normal; overflow: visible; text-overflow: clip; }
        #werkhalMap .bok:not(.bok-selected) .bok-extra { display: none; }
        .bok.bok-static .bok-extra { display: none; }
        #werkhalMap .bok.bok-selected > .bok-more { display: none !important; }
        .bok .bok-hint { display: none; }
        #werkhalMap .bok.bok-selected .bok-hint { display: block; }
        .bok-logo {
            background: rgba(255,255,255,.92); border-radius: 4px; padding: 1px 4px;
            display: inline-flex; align-items: center;
        }
        .bok-logo img { height: 20px; max-width: 96px; object-fit: contain; display: block; }
    """

# ------------------------------------------------------------------ modal-HTML
BOK_MODAL = """<!-- Bok Modal (patch 9) -->
    <div id="bokModal"
        class="fixed inset-0 modal-overlay z-50 flex items-center justify-center hidden opacity-0 transition-opacity duration-300">
        <div
            class="bg-white dark:bg-zinc-900 rounded-md border border-zinc-200 dark:border-zinc-800 shadow-2xl p-6 max-w-lg w-full mx-4 transform scale-95 transition-transform duration-300 flex flex-col max-h-[90vh] overflow-y-auto">
            <div class="flex justify-between items-center mb-4">
                <h2 id="bokModalTitle" class="text-xl font-bold text-zinc-900 dark:text-white">Bok</h2>
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
                    <select id="bokLeverancier" class="{INPUT}"></select>
                </div>
                <div>
                    <label class="{LABEL}">Status</label>
                    <select id="bokStatus" class="{INPUT}">
                        <option value="leeg">Leeg</option>
                        <option value="bezet">Bezet</option>
                    </select>
                </div>
                <div>
                    <label class="{LABEL}">Projecten + B-nummer</label>
                    <div id="bokKoppelingen" class="space-y-2"></div>
                    <datalist id="bokBList"></datalist>
                    <button id="btnAddKoppeling" type="button" class="{BTN2} mt-2">
                        <i class="fa-solid fa-plus"></i><span>Project toevoegen</span>
                    </button>
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

    """.replace("{LABEL}", LABEL).replace("{INPUT}", INPUT).replace("{BTN2}", BTN2)

# ------------------------------------------------------------------ JS
JS = r"""// ===== Werkhal / bokken (patch 9) =====
        (function setupWerkhal() {
            const $ = (id) => document.getElementById(id);
            const bokCol = () => collection(db, 'workspaces', WORKSPACE_ID, 'glasbokken');
            const bokDoc = (id) => doc(db, 'workspaces', WORKSPACE_ID, 'glasbokken', id);
            const PLAN_URL = 'Plattegrond.png';
            const FIELD = '{INPUT}';

            // ===== LEVERANCIERS (hard-gecodeerd) =====
            // Nieuwe leverancier toevoegen = een regel erbij. 'naam' is ook de bestandsnaam
            // van het logo (naam + .png of .jpg, in dezelfde map als index.html).
            const LEVERANCIERS = [
                { naam: 'AID Glass Bv',   kleur: '#bbdb0b' },
                { naam: 'Mosa Glas',      kleur: '#a9233e' },
                { naam: 'Group Ceyssens', kleur: '#f28d01' },
                { naam: 'AD Megatec',     kleur: '#75b726' }
            ];
            const STATUS = {
                bezet: { label: 'BEZET', kleur: '#dc2626' },
                leeg:  { label: 'LEEG',  kleur: '#16a34a' }
            };

            let bokken = [];
            let planImage = null;
            let unsubBokken = null;
            let dragging = false, pendingRender = false;
            let editBok = null;
            let chooserOutside = null;
            let selectedBokId = null;
            const logoUrl = {};   // naam -> url (of null als er geen logo is)

            const isPlaced = (b) => typeof b.posX === 'number' && typeof b.posY === 'number';
            const clampPct = (n) => Math.min(100, Math.max(0, n));
            const round2 = (n) => Math.round(n * 100) / 100;
            const projectById = (id) => projects.find(p => p.id === id) || null;
            const koppelingenOf = (b) => Array.isArray(b.koppelingen)
                ? b.koppelingen
                : (b.projectId ? [{ projectId: b.projectId, bNummer: b.bNummer || '' }] : []);
            const isBezet = (b) => b.status === 'bezet' || b.status === 'vol';   // 'vol' = oude waarde
            const statusKey = (b) => isBezet(b) ? 'bezet' : 'leeg';
            const supplierOf = (naam) => LEVERANCIERS.find(l => l.naam === String(naam || '').trim()) || null;

            // zwart of wit tekst, afhankelijk van welke het meeste contrast geeft
            function textOn(hex) {
                const c = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
                    .map(v => v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
                const L = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
                return (1.05 / (L + 0.05)) > ((L + 0.05) / 0.06) ? '#ffffff' : '#18181b';
            }

            // ---------- logo's zoeken (.png, anders .jpg) ----------
            function probeLogos() {
                LEVERANCIERS.forEach(l => {
                    const exts = ['png', 'jpg'];
                    const attempt = (i) => {
                        if (i >= exts.length) { logoUrl[l.naam] = null; return; }
                        const url = encodeURIComponent(l.naam) + '.' + exts[i];
                        const im = new Image();
                        im.onload = () => { logoUrl[l.naam] = url; renderWerkhal(); renderGlasStrip(); };
                        im.onerror = () => attempt(i + 1);
                        im.src = url;
                    };
                    attempt(0);
                });
            }
            probeLogos();

            // ---------- plattegrond: vast bestand naast index.html ----------
            $('werkhalEmpty').textContent = 'Plattegrond laden...';
            const probe = new Image();
            probe.onload = () => { planImage = PLAN_URL; renderWerkhal(); };
            probe.onerror = () => {
                $('werkhalEmpty').textContent = 'Plattegrond.png niet gevonden. Zet het bestand in dezelfde map als index.html en laad de pagina opnieuw.';
            };
            probe.src = PLAN_URL;

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

            // ---------- selectie (bok naar voorgrond) ----------
            function markSelected() {
                let found = false;
                document.querySelectorAll('#werkhalMap .bok').forEach(n => {
                    const on = n.dataset.bokId === selectedBokId;
                    if (on) found = true;
                    n.classList.toggle('bok-selected', on);
                });
                if (!found) selectedBokId = null;
            }
            function selectBok(id) { selectedBokId = id; markSelected(); }

            $('werkhalMap').addEventListener('click', (e) => { if (!e.target.closest('.bok')) selectBok(null); });
            document.addEventListener('keydown', (e) => { if (e.key === 'Escape') selectBok(null); });

            // ---------- marker bouwen ----------
            function buildMarker(b) {
                const st = STATUS[statusKey(b)];
                const sup = supplierOf(b.leverancier);
                const ks = koppelingenOf(b);
                const el = document.createElement('div');
                el.dataset.bokId = b.id;
                el.className = 'bok rounded-md shadow-md px-2 py-1' +
                    (sup ? '' : ' bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100');
                el.style.border = '2px solid rgba(0,0,0,.35)';
                el.style.borderLeft = '8px solid ' + st.kleur;
                if (sup) { el.style.background = sup.kleur; el.style.color = textOn(sup.kleur); }

                const lines = ks.map((k, i) => {
                    const p = projectById(k.projectId);
                    return '<div class="text-[11px] leading-tight truncate font-medium' + (i >= 2 ? ' bok-extra' : '') + '">' +
                        (k.bNummer ? esc(k.bNummer) + ' \u00b7 ' : '') + esc(p ? p.title : 'Onbekend project') + '</div>';
                }).join('');
                const more = ks.length > 2
                    ? '<div class="bok-more text-[10px] leading-tight opacity-70">+' + (ks.length - 2) + ' meer</div>' : '';
                const none = ks.length === 0 ? '<div class="text-[11px] leading-tight opacity-70">Geen project</div>' : '';

                let supHtml = '';
                if (b.leverancier) {
                    const url = sup && logoUrl[sup.naam];
                    supHtml = '<div class="mt-1 flex items-center gap-1.5">' + (url
                        ? '<span class="bok-logo"><img src="' + esc(url) + '" alt="' + esc(b.leverancier) + '"></span>'
                        : '<span class="text-[10px] font-semibold leading-tight truncate">' + esc(b.leverancier) + '</span>') + '</div>';
                }
                const hint = ks.length > 0
                    ? '<div class="bok-hint text-[10px] leading-tight opacity-80 mt-1">Tik nogmaals om naar het project te gaan</div>' : '';

                el.innerHTML =
                    '<div class="flex items-center gap-1.5">' +
                        '<span class="font-bold text-xs truncate flex-grow">' + esc(b.boknummer || 'Bok') + '</span>' +
                        '<button type="button" class="bok-status text-[11px] font-extrabold tracking-wide px-2.5 py-1 rounded-sm" ' +
                            'style="background:' + st.kleur + ';color:#fff" title="Wisselen tussen bezet en leeg">' + st.label + '</button>' +
                        '<button type="button" class="bok-edit p-1.5 rounded-sm hover:bg-black/10" title="Bewerken"><i class="fa-solid fa-pen text-[10px]"></i></button>' +
                    '</div>' + lines + more + none + supHtml + hint;
                return el;
            }

            function wireButtons(el, b) {
                el.querySelector('.bok-status').addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (!currentUser) return;
                    updateDoc(bokDoc(b.id), { status: isBezet(b) ? 'leeg' : 'bezet' })
                        .catch(() => showToast('Fout bij wijzigen status', 'error'));
                });
                el.querySelector('.bok-edit').addEventListener('click', (e) => {
                    e.stopPropagation();
                    openBokModal(b);
                });
            }

            // ---------- naar het project ----------
            function goProject(p) { switchView('bord'); openProjectModal(p); }

            function closeChooser() {
                const c = $('bokChooser');
                if (c) c.remove();
                if (chooserOutside) { document.removeEventListener('pointerdown', chooserOutside, true); chooserOutside = null; }
            }

            function showChooser(items, x, y) {
                closeChooser();
                const box = document.createElement('div');
                box.id = 'bokChooser';
                box.className = 'fixed z-[120] bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded-md shadow-2xl p-1';
                box.style.minWidth = '220px';
                box.style.maxWidth = '320px';
                const head = document.createElement('div');
                head.className = 'px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400';
                head.textContent = 'Ga naar project';
                box.appendChild(head);
                items.forEach(it => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'w-full text-left text-sm px-3 py-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-900 dark:text-zinc-100';
                    btn.innerHTML = (it.k.bNummer ? '<span class="font-bold">' + esc(it.k.bNummer) + '</span> \u00b7 ' : '') + esc(it.p.title);
                    btn.addEventListener('click', () => { closeChooser(); goProject(it.p); });
                    box.appendChild(btn);
                });
                document.body.appendChild(box);
                box.style.left = Math.max(8, Math.min(x, window.innerWidth - box.offsetWidth - 8)) + 'px';
                box.style.top = Math.max(8, Math.min(y, window.innerHeight - box.offsetHeight - 8)) + 'px';
                chooserOutside = (ev) => { if (!box.contains(ev.target)) closeChooser(); };
                setTimeout(() => document.addEventListener('pointerdown', chooserOutside, true), 0);
            }

            function tapBok(b, e) {
                const items = koppelingenOf(b).map(k => ({ k, p: projectById(k.projectId) })).filter(x => x.p);
                if (items.length === 0) openBokModal(b);
                else if (items.length === 1) goProject(items[0].p);
                else showChooser(items, e ? e.clientX : 40, e ? e.clientY : 40);
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
                        // 1e tik: naar de voorgrond; 2e tik op dezelfde bok: naar het project
                        if (selectedBokId !== b.id) selectBok(b.id);
                        else tapBok(b, e);
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
                            if (!planImage) showToast('Plattegrond is nog niet geladen', 'error');
                            renderWerkhal();
                        }
                    } else {
                        if (pendingRender) { pendingRender = false; renderWerkhal(); }
                        tapBok(b, e);
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
                let nBezet = 0, nLeeg = 0;
                bokken.forEach(b => {
                    if (isBezet(b)) nBezet++; else nLeeg++;
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
                markSelected();
                $('bokTray').style.display = tray.children.length ? '' : 'none';
                $('bokCounts').textContent = bokken.length
                    ? nBezet + ' bezet \u00b7 ' + nLeeg + ' leeg \u00b7 ' + bokken.length + ' totaal' : '';
            }

            // ---------- Bokken-rij in het projectvenster ----------
            function renderGlasStrip() {
                const box = $('glasStrip');
                if (!box) return;
                box.innerHTML = '';
                if (!activeProject) return;
                const label = document.createElement('span');
                label.className = 'text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mr-1';
                label.innerHTML = '<i class="fa-solid fa-border-all mr-1"></i>Bokken';
                box.appendChild(label);
                bokken.forEach(b => {
                    const ks = koppelingenOf(b);
                    const mine = ks.find(k => k.projectId === activeProject.id);
                    if (!mine) return;
                    const st = STATUS[statusKey(b)];
                    const sup = supplierOf(b.leverancier);
                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.title = 'Toon op plattegrond';
                    chip.className = 'text-xs font-medium px-2.5 py-1.5 rounded-md flex items-center gap-2 transition-colors' +
                        (sup ? '' : ' bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100');
                    chip.style.border = '1px solid rgba(0,0,0,.25)';
                    chip.style.borderLeft = '6px solid ' + st.kleur;
                    if (sup) { chip.style.background = sup.kleur; chip.style.color = textOn(sup.kleur); }
                    chip.innerHTML =
                        '<span class="font-bold">' + esc(b.boknummer || 'Bok') + '</span>' +
                        (b.leverancier ? '<span>' + esc(b.leverancier) + '</span>' : '') +
                        (mine.bNummer ? '<span>' + esc(mine.bNummer) + '</span>' : '') +
                        (ks.length > 1 ? '<span class="opacity-70">+' + (ks.length - 1) + '</span>' : '') +
                        '<span class="font-bold">' + st.label + '</span>';
                    chip.addEventListener('click', () => goToBok(b.id));
                    box.appendChild(chip);
                });
                const add = document.createElement('button');
                add.type = 'button';
                add.className = 'text-xs font-medium px-2.5 py-1.5 rounded-md border border-zinc-300 dark:border-zinc-700 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 flex items-center gap-1 transition-colors';
                add.innerHTML = '<i class="fa-solid fa-plus"></i> Bok';
                add.addEventListener('click', () => openBokModal(null, activeProject.id));
                box.appendChild(add);
            }

            function goToBok(id) {
                hideModal('projectModal');
                selectedBokId = id;
                switchView('werkhal');
                setTimeout(() => {
                    const el = document.querySelector('#werkhalMap [data-bok-id="' + id + '"], #bokTrayList [data-bok-id="' + id + '"]');
                    if (!el) return;
                    el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
                    el.classList.add('bok-flash');
                    setTimeout(() => el.classList.remove('bok-flash'), 3200);
                }, 150);
            }

            // ---------- bok-venster ----------
            function supplierOptionsHtml(current) {
                let h = '<option value="">\u2014 kies leverancier \u2014</option>' +
                    LEVERANCIERS.map(l => '<option value="' + esc(l.naam) + '">' + esc(l.naam) + '</option>').join('');
                // bestaande, niet-gecodeerde leverancier (uit eerdere versies) niet kwijtraken
                if (current && !supplierOf(current)) h += '<option value="' + esc(current) + '">' + esc(current) + ' (overig)</option>';
                return h;
            }

            function projectOptionsHtml(selectedId) {
                const list = projects
                    .filter(p => p.status !== 'archive' || p.id === selectedId)
                    .sort((a, b) => (a.title || '').localeCompare(b.title || '', 'nl', { numeric: true }));
                return '<option value="">\u2014 kies project \u2014</option>' +
                    list.map(p => '<option value="' + esc(p.id) + '">' + esc(p.title || 'Project') + '</option>').join('');
            }

            function refreshBNummerList() {
                const found = new Set();
                const scan = (t) => (String(t || '').match(/\bB\d{6}\b/gi) || []).forEach(x => found.add(x.toUpperCase()));
                document.querySelectorAll('#bokKoppelingen .kopp-project').forEach(sel => {
                    const p = projectById(sel.value);
                    if (p) (p.checklist || []).forEach(i => { scan(i.text); (i.subitems || []).forEach(s => scan(s.text)); });
                });
                $('bokBList').innerHTML = Array.from(found).map(x => '<option value="' + x + '"></option>').join('');
            }

            function addKoppelingRow(k) {
                const row = document.createElement('div');
                row.className = 'bok-kopp flex gap-2 items-center';
                row.innerHTML =
                    '<select class="kopp-project flex-grow min-w-0 ' + FIELD + '"></select>' +
                    '<input type="text" class="kopp-b ' + FIELD + '" style="width:8rem" list="bokBList" placeholder="B261342">' +
                    '<button type="button" class="kopp-del text-red-500 hover:text-red-700 p-2 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20" title="Verwijderen"><i class="fa-solid fa-xmark"></i></button>';
                const sel = row.querySelector('.kopp-project');
                sel.innerHTML = projectOptionsHtml(k && k.projectId);
                sel.value = (k && k.projectId) || '';
                row.querySelector('.kopp-b').value = (k && k.bNummer) || '';
                row.querySelector('.kopp-del').addEventListener('click', () => { row.remove(); refreshBNummerList(); });
                $('bokKoppelingen').appendChild(row);
            }

            $('bokKoppelingen').addEventListener('change', (e) => {
                if (e.target.classList.contains('kopp-project')) refreshBNummerList();
            });
            $('btnAddKoppeling').addEventListener('click', () => addKoppelingRow(null));

            function openBokModal(b, presetProjectId) {
                editBok = b ? { id: b.id } : { id: null };
                $('bokModalTitle').textContent = b ? 'Bok bewerken' : 'Nieuwe bok';
                $('bokNummer').value = b ? (b.boknummer || '') : '';
                const cur = b ? (b.leverancier || '') : '';
                $('bokLeverancier').innerHTML = supplierOptionsHtml(cur);
                $('bokLeverancier').value = cur;
                $('bokStatus').value = b ? statusKey(b) : 'leeg';
                $('bokKoppelingen').innerHTML = '';
                let ks = b ? koppelingenOf(b) : (presetProjectId ? [{ projectId: presetProjectId, bNummer: '' }] : []);
                if (ks.length === 0) ks = [null];
                ks.forEach(addKoppelingRow);
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
                const koppelingen = Array.from(document.querySelectorAll('#bokKoppelingen .bok-kopp')).map(r => ({
                    projectId: r.querySelector('.kopp-project').value,
                    bNummer: r.querySelector('.kopp-b').value.trim().toUpperCase()
                })).filter(k => k.projectId);
                const data = {
                    boknummer,
                    leverancier: $('bokLeverancier').value,
                    status: $('bokStatus').value === 'bezet' ? 'bezet' : 'leeg',
                    koppelingen
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
                    title: 'Bok verwijderen',
                    message: 'Deze bok definitief verwijderen?',
                    type: 'confirm', isDanger: true, confirmText: 'Verwijderen'
                });
                if (!ok) return;
                try {
                    await deleteDoc(bokDoc(editBok.id));
                    hideModal('bokModal');
                } catch (e) { showToast('Fout bij verwijderen: ' + (e.code || e.message), 'error'); }
            });

            // ---------- Firestore ----------
            function stopGlas() {
                if (unsubBokken) { unsubBokken(); unsubBokken = null; }
                bokken = [];
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
                }, (err) => showToast('Bokken: ' + err.code, 'error'));
            }
            onAuthStateChanged(auth, (u) => { if (u) startGlas(); else stopGlas(); });

            // ---------- inhaken op bestaande functies ----------
            const _openProject = openProjectModal;
            openProjectModal = function (p) { _openProject(p); renderGlasStrip(); };
            const _renderBoard = renderBoard;
            renderBoard = function () { _renderBoard(); renderWerkhal(); renderGlasStrip(); };

            switchView(location.hash === '#werkhal' ? 'werkhal' : 'bord');
        })();

        """.replace("{INPUT}", INPUT)

# ------------------------------------------------------- controleren
P7 = "// ===== Werkhal: zoom, schaal en schermvullend (patch 7) ====="
MARK_M1 = "<!-- Glasbok Modal -->"
MARK_M2 = "<!-- Notification Toast -->"

for needle in ("</style>", P6, MARK_M1, MARK_M2):
    n = html.count(needle)
    if n != 1:
        sys.exit(f"Aanpassingspunt {n}x gevonden (verwacht 1x), niets gewijzigd:\n  {needle[:70]!r}")

js_s = html.index(P6)
js_e = html.index(P7) if html.count(P7) == 1 else html.rfind("</script>")
region = html[js_s:js_e]
if js_e < js_s or not region.rstrip().endswith("})();") or region.count("setupWerkhal") != 1:
    sys.exit("Werkhal-script heeft een onverwachte vorm (is het gewijzigd na patch 6?). Niets gewijzigd.")

m_s = html.index(MARK_M1)
m_e = html.index(MARK_M2)
if m_e < m_s:
    sys.exit("Onverwachte volgorde van het bok-venster. Niets gewijzigd.")

# ---------------------------------------------------------- doorvoeren
# (van achter naar voor, zodat de indexen geldig blijven)
if m_s > js_s:
    html = html[:m_s] + BOK_MODAL + html[m_e:]
    html = html[:js_s] + JS + html[js_e:]
else:
    html = html[:js_s] + JS + html[js_e:]
    m_s = html.index(MARK_M1)
    m_e = html.index(MARK_M2)
    html = html[:m_s] + BOK_MODAL + html[m_e:]

html = html.replace("</style>", CSS + "</style>", 1)

# knoptekst in de werkhal-werkbalk (niet fataal als hij niet gevonden wordt)
if html.count("<span>Glasbok</span>") >= 1:
    html = html.replace("<span>Glasbok</span>", "<span>Bok</span>")
else:
    print("Opmerking: knop '+ Glasbok' in de werkbalk niet gevonden; tekst niet aangepast.")

shutil.copy(path, path.with_suffix(path.suffix + ".bak9"))
path.write_text(html, encoding="utf-8")
print(f"Klaar. Back-up: {path.name}.bak9")
print("Zet de logo's (bv. 'AID Glass Bv.png') in dezelfde map als index.html.")
