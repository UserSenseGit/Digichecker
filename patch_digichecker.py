#!/usr/bin/env python3
"""
Patch voor Digichecker:
  1. Project aanmaken zonder fiche/AI
  2. Fiche(s) + AI-verwerking later toevoegen aan bestaand project
  3. Hoofdpunt afvinken -> subitems automatisch mee afvinken
  4. Items (en subitems) verslepen om de volgorde te wijzigen

Gebruik:  python patch_digichecker.py index.html
Er wordt eerst een back-up gemaakt (<bestand>.bak). Faalt een patch, dan wordt niets gewijzigd.
"""
import sys
import shutil

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
with open(path, encoding="utf-8", newline="") as f:
    src = f.read()

if "cl-grip" in src or "createEmptyProject" in src:
    sys.exit("Dit bestand lijkt al gepatcht te zijn. Niets gewijzigd.")


def patch(old, new, label):
    global src
    n = src.count(old)
    if n != 1:
        sys.exit(f"[FOUT] '{label}': {n} matches gevonden (verwacht 1). Niets gewijzigd.")
    src = src.replace(old, new)


# ---------------------------------------------------------------- CSS
patch(
    "</style>",
    r"""
        /* patch: modals boven projectmodal, sleep-handvat */
        #stagingModal, #reviewModal { z-index: 70 !important; }
        #processingModal { z-index: 80 !important; }
        .cl-grip { cursor: grab; touch-action: none; }
        .cl-main.is-sorting, .cl-sub.is-sorting { opacity: .5; }
    </style>""",
    "css",
)

# ---------------------------------------------------------------- HTML: staging modal
patch(
    '<h2 class="text-xl font-bold text-zinc-900 dark:text-white">Nieuw Project Toevoegen</h2>',
    '<h2 id="stagingTitle" class="text-xl font-bold text-zinc-900 dark:text-white">Nieuw Project Toevoegen</h2>',
    "staging titel",
)

patch(
    '<button id="btnProcessImages"',
    r"""<button id="btnEmptyProject" onclick="createEmptyProject()"
                    class="mr-3 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 px-4 py-2.5 rounded-md font-medium transition-colors flex items-center gap-2">
                    <i class="fa-regular fa-file"></i>
                    <span>Zonder fiche aanmaken</span>
                </button>
                """ + '<button id="btnProcessImages"',
    "knop leeg project",
)

# ---------------------------------------------------------------- HTML: knop in projectmodal
patch(
    '<h3 class="font-bold text-zinc-900 dark:text-white text-lg">Checklist</h3>',
    r"""<div class="flex items-center gap-3">
                            <h3 class="font-bold text-zinc-900 dark:text-white text-lg">Checklist</h3>
                            <button onclick="openStagingModalForProject()"
                                class="text-sm text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white flex items-center gap-1 font-medium bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 px-3 py-1.5 rounded-md transition-colors">
                                <i class="fa-solid fa-camera"></i> Fiche toevoegen
                            </button>
                        </div>""",
    "knop fiche toevoegen",
)

# ---------------------------------------------------------------- JS: state
patch(
    "let pendingProjectData = null;",
    "let pendingProjectData = null;\n        let stagingTargetProjectId = null;",
    "state",
)

patch(
    "window.openStagingModal = function () {",
    "window.openStagingModal = function () {\n            stagingTargetProjectId = null;\n            setStagingMode(false);",
    "openStagingModal reset",
)

patch(
    "pendingProjectData = { title: title, checklist: itemsArray, images: [...stagingImagesBase64] };",
    "pendingProjectData = { title: title, checklist: itemsArray, images: [...stagingImagesBase64], targetId: stagingTargetProjectId };",
    "pendingProjectData targetId",
)

# bij 'fiche toevoegen' de bestaande projectgegevens voorinvullen
patch(
    "document.getElementById('reviewLabel').value = 'aframes';",
    r"""document.getElementById('reviewLabel').value = 'aframes';
            if (stagingTargetProjectId) {
                const tp = projects.find(p => p.id === stagingTargetProjectId);
                if (tp) {
                    document.getElementById('reviewTitle').value = tp.title || '';
                    document.getElementById('reviewWeek').value = tp.weekNumber || '';
                    document.getElementById('reviewLabel').value = tp.label || '';
                }
            }""",
    "review voorinvullen",
)

# ---------------------------------------------------------------- JS: nieuwe functies (staging)
patch(
    "function compressImage(file, callback) {",
    r"""function setStagingMode(append) {
            document.getElementById('stagingTitle').textContent = append ? 'Fiche toevoegen aan project' : 'Nieuw Project Toevoegen';
            document.getElementById('btnEmptyProject').style.display = append ? 'none' : '';
        }

        window.openStagingModalForProject = function () {
            if (!activeProject) return;
            stagingImagesBase64 = [];
            stagingTargetProjectId = activeProject.id;
            setStagingMode(true);
            renderStagingImages();
            showModal('stagingModal');
        }

        window.createEmptyProject = function () {
            stagingTargetProjectId = null;
            stagingImagesBase64 = [];
            pendingProjectData = { title: '', checklist: [], images: [], targetId: null };
            document.getElementById('reviewImagesContainer').innerHTML = '';
            document.getElementById('reviewTitle').value = '';
            document.getElementById('reviewWeek').value = '';
            document.getElementById('reviewLabel').value = 'aframes';
            renderReviewChecklist();
            hideModal('stagingModal');
            showModal('reviewModal');
            setTimeout(() => document.getElementById('reviewTitle').focus(), 350);
        }

        function compressImage(file, callback) {""",
    "staging functies",
)

# ---------------------------------------------------------------- JS: opslaan (nieuw of toevoegen)
patch(
    "if (label === 'extern' && !hasSteekrubber(cleanedChecklist)) cleanedChecklist.push(newSteekrubberItem());",
    "if (label === 'extern' && !hasSteekrubber(cleanedChecklist) && !(pendingProjectData.targetId && hasSteekrubber((projects.find(p => p.id === pendingProjectData.targetId) || {}).checklist || []))) cleanedChecklist.push(newSteekrubberItem());",
    "steekrubber bij toevoegen",
)

patch(
    "const approxSize = JSON.stringify({ checklist: cleanedChecklist, images: pendingProjectData.images }).length;",
    r"""const targetProject = pendingProjectData.targetId ? projects.find(p => p.id === pendingProjectData.targetId) : null;
            if (pendingProjectData.targetId && !targetProject) { showToast("Project niet meer gevonden", "error"); return; }
            let finalChecklist = cleanedChecklist;
            let finalImages = pendingProjectData.images;
            if (targetProject) {
                finalChecklist = [...(targetProject.checklist || []), ...cleanedChecklist];
                finalImages = [...(targetProject.images || (targetProject.imageBase64 ? [targetProject.imageBase64] : [])), ...pendingProjectData.images];
            }
            const approxSize = JSON.stringify({ checklist: finalChecklist, images: finalImages }).length;""",
    "approxSize",
)

patch(
    "await addDoc(projectsCol(), {",
    r"""if (targetProject) {
                    const upd = { checklist: finalChecklist, images: finalImages };
                    if (finalTitle !== (targetProject.title || '')) upd.title = finalTitle;
                    if (weekNumber !== String(targetProject.weekNumber || '')) upd.weekNumber = weekNumber;
                    if (label !== (targetProject.label || '')) upd.label = label;
                    await updateDoc(projectDoc(targetProject.id), upd);
                } else await addDoc(projectsCol(), {""",
    "addDoc/updateDoc",
)

patch(
    'showToast("Project aangemaakt!", "success");',
    'showToast(targetProject ? "Fiche toegevoegd!" : "Project aangemaakt!", "success");\n                stagingTargetProjectId = null;',
    "toast",
)

# ---------------------------------------------------------------- JS: afbeeldingen live verversen
patch(
    "activeProject = updatedActive;",
    "activeProject = updatedActive;\n                        renderActiveProjectImages();",
    "snapshot images",
)

patch(
    "document.getElementById('modalProjectTitle').innerText = project.title;",
    "document.getElementById('modalProjectTitle').innerText = project.title;\n            document.getElementById('modalProjectImagesContainer').dataset.key = '';",
    "openProjectModal key",
)

patch(
    "showModal('projectModal');",
    "renderActiveProjectImages();\n            showModal('projectModal');",
    "openProjectModal render",
)

# ---------------------------------------------------------------- JS: sleephandvat + data-attributen
patch(
    '<label class="flex-grow flex items-start gap-3 cursor-pointer min-w-0">',
    r"""<span class="cl-grip shrink-0 text-zinc-300 hover:text-zinc-700 dark:text-zinc-600 dark:hover:text-zinc-300 px-1.5 pt-1 select-none" title="Slepen om te verplaatsen"><i class="fa-solid fa-grip-vertical text-xs"></i></span>
                    <label class="flex-grow flex items-start gap-3 cursor-pointer min-w-0">""",
    "grip",
)

patch(
    "itemDiv.innerHTML = createCheckboxHTML(item, false);",
    "itemDiv.className = 'cl-main';\n                itemDiv.dataset.id = item.id;\n                itemDiv.innerHTML = createCheckboxHTML(item, false);",
    "cl-main",
)

patch(
    'subContainer.className = "ml-7 space-y-1 mt-1 pl-2 border-l-2 border-zinc-200 dark:border-zinc-800";',
    'subContainer.className = "ml-7 space-y-1 mt-1 pl-2 border-l-2 border-zinc-200 dark:border-zinc-800";\n                    subContainer.dataset.parent = item.id;',
    "subContainer",
)

patch(
    "subDiv.innerHTML = createCheckboxHTML(sub, true, item.id);",
    "subDiv.className = 'cl-sub';\n                        subDiv.dataset.id = sub.id;\n                        subDiv.innerHTML = createCheckboxHTML(sub, true, item.id);",
    "cl-sub",
)

# ---------------------------------------------------------------- JS: hoofdpunt afvinken -> subitems mee
patch(
    "if (item) item.checked = isChecked;",
    "if (item) { item.checked = isChecked; (item.subitems || []).forEach(s => { s.checked = isChecked; }); }",
    "cascade",
)

# ---------------------------------------------------------------- JS: slepen + afbeeldingen renderen
patch(
    "window.toggleItemStatus = async function (itemId, isChecked, parentId) {",
    r"""function renderActiveProjectImages() {
            if (!activeProject) return;
            const c = document.getElementById('modalProjectImagesContainer');
            const images = activeProject.images || (activeProject.imageBase64 ? [activeProject.imageBase64] : []);
            const key = activeProject.id + ':' + images.length;
            if (c.dataset.key === key) return;
            c.dataset.key = key;
            c.innerHTML = '';
            if (images.length === 0) {
                c.innerHTML = '<div class="m-auto text-sm text-zinc-500 dark:text-zinc-400 text-center p-4">Nog geen fiches. Gebruik "Fiche toevoegen" bij de checklist.</div>';
                return;
            }
            images.forEach(b64 => {
                const img = document.createElement('img');
                img.src = b64;
                img.className = "w-full max-h-[70vh] object-contain bg-white dark:bg-black border border-zinc-200 dark:border-zinc-800 shadow-sm rounded-md";
                c.appendChild(img);
            });
        }

        // Volgorde wijzigen via sleephandvat (werkt met muis en touch)
        (function setupChecklistSort() {
            const list = document.getElementById('liveChecklist');
            let drag = null;

            list.addEventListener('pointerdown', (e) => {
                const grip = e.target.closest('.cl-grip');
                if (!grip) return;
                const el = grip.closest('.cl-main, .cl-sub');
                if (!el) return;
                e.preventDefault();
                try { grip.setPointerCapture(e.pointerId); } catch (_) { }
                drag = { el, container: el.parentElement, parentId: el.classList.contains('cl-sub') ? el.parentElement.dataset.parent : null };
                el.classList.add('is-sorting');
            });

            list.addEventListener('pointermove', (e) => {
                if (!drag || !drag.el.isConnected) return;
                const siblings = Array.from(drag.container.children).filter(c => c !== drag.el);
                for (const sib of siblings) {
                    const r = sib.getBoundingClientRect();
                    if (e.clientY >= r.top && e.clientY <= r.bottom) {
                        const before = e.clientY < r.top + r.height / 2;
                        drag.container.insertBefore(drag.el, before ? sib : sib.nextSibling);
                        break;
                    }
                }
            });

            const end = async () => {
                if (!drag) return;
                const d = drag;
                drag = null;
                d.el.classList.remove('is-sorting');
                await saveChecklistOrder(d.parentId);
            };
            list.addEventListener('pointerup', end);
            list.addEventListener('pointercancel', end);

            async function saveChecklistOrder(parentId) {
                if (!currentUser || !activeProject) return;
                const cl = JSON.parse(JSON.stringify(activeProject.checklist || []));
                let next;
                if (parentId) {
                    const parent = cl.find(i => i.id === parentId);
                    const sc = Array.from(list.querySelectorAll('[data-parent]')).find(x => x.dataset.parent === parentId);
                    if (!parent || !sc) return;
                    const subs = new Map((parent.subitems || []).map(s => [s.id, s]));
                    const ordered = Array.from(sc.children).map(c => subs.get(c.dataset.id)).filter(Boolean);
                    if (ordered.length !== (parent.subitems || []).length) return;
                    parent.subitems = ordered;
                    next = cl;
                } else {
                    const byId = new Map(cl.map(i => [i.id, i]));
                    next = Array.from(list.children).map(c => byId.get(c.dataset.id)).filter(Boolean);
                    if (next.length !== cl.length) return;
                }
                if (JSON.stringify(next) === JSON.stringify(activeProject.checklist || [])) return;
                try { await updateDoc(projectDoc(activeProject.id), { checklist: next }); }
                catch (e) { showToast("Fout bij opslaan volgorde", "error"); renderActiveProjectLiveChecklist(); }
            }
        })();

        window.toggleItemStatus = async function (itemId, isChecked, parentId) {""",
    "sorteren + images",
)

# ---------------------------------------------------------------- schrijven
shutil.copyfile(path, path + ".bak")
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(src)
print(f"Klaar. Back-up: {path}.bak")
