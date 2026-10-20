#!/usr/bin/env python3
"""
Voegt project-labels toe aan Digichecker:
  zwart = A-Frames, blauw = Axor / A-Struc, rood = Extern

Gebruik:
    python apply_labels.py index.html

Maakt eerst een back-up (<bestand>.bak). Als een ankerpunt niet precies
één keer gevonden wordt, stopt het script zonder iets te wijzigen.
"""
import re
import shutil
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"

with open(path, encoding="utf-8", newline="") as f:
    html = f.read()

if "modalProjectLabel" in html:
    sys.exit("Labels zijn al toegevoegd aan dit bestand. Niets gewijzigd.")

errors = []


def sub_once(text, pattern, repl_fn, name, flags=0):
    matches = list(re.finditer(pattern, text, flags))
    if len(matches) != 1:
        errors.append(f"{name}: {len(matches)} keer gevonden (verwacht 1)")
        return text
    m = matches[0]
    return text[: m.start()] + repl_fn(m) + text[m.end():]


def after(text, anchor, addition, name):
    return sub_once(text, re.escape(anchor), lambda m: m.group(0) + addition, name)


def before(text, anchor, addition, name):
    return sub_once(text, re.escape(anchor), lambda m: addition + m.group(0), name)


# 1. CSS
CSS = """
        .label-aframes { border-left: 4px solid #18181b; }
        .label-axor    { border-left: 4px solid #2563eb; }
        .label-extern  { border-left: 4px solid #dc2626; }
        .dark .label-aframes { border-left-color: #e4e4e7; }
        .label-chip { display:inline-flex; align-items:center; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; padding:2px 6px; border-radius:2px; color:#fff; }
        .label-chip.aframes { background:#18181b; }
        .dark .label-chip.aframes { background:#e4e4e7; color:#18181b; }
        .label-chip.axor { background:#2563eb; }
        .label-chip.extern { background:#dc2626; }
    """
html = before(html, "</style>", CSS, "CSS")

# 2. Review-modal: label kiezen bij nieuw project
REVIEW_SELECT = """<div class="mb-4">
                    <label class="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">Label</label>
                    <select id="reviewLabel"
                        class="w-full p-2 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white rounded-md outline-none focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white">
                        <option value="aframes">⚫ A-Frames</option>
                        <option value="axor">🔵 Axor / A-Struc</option>
                        <option value="extern">🔴 Extern</option>
                    </select>
                </div>

                """
html = sub_once(
    html,
    r'<div class="mb-4">\s*<label[^>]*>\s*Checklist',
    lambda m: REVIEW_SELECT + m.group(0),
    "Review-modal",
)

# 3. Project-modal: label wijzigen
PROJECT_SELECT = """

                        <select id="modalProjectLabel"
                            class="text-sm font-medium rounded-md border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-sm focus:ring-1 focus:ring-zinc-500 outline-none px-2 py-1.5">
                            <option value="">Geen label</option>
                            <option value="aframes">⚫ A-Frames</option>
                            <option value="axor">🔵 Axor / A-Struc</option>
                            <option value="extern">🔴 Extern</option>
                        </select>"""
html = sub_once(
    html,
    r'<select id="modalProjectStatus".*?</select>',
    lambda m: m.group(0) + PROJECT_SELECT,
    "Project-modal",
    re.DOTALL,
)

# 4. Kaart-template: labelchip naast statusbadge
html = sub_once(
    html,
    r'<span\s+class="[^"]*card-status-badge">Nieuw</span>',
    lambda m: (
        '<div class="flex items-center gap-2">\n'
        '                    <span class="label-chip card-label-chip hidden"></span>\n'
        '                    <span class="text-[10px] uppercase tracking-wider font-bold '
        'text-zinc-500 dark:text-zinc-400 px-0.5 card-status-badge">Nieuw</span>\n'
        "                </div>"
    ),
    "Kaart-template",
)

# 5. JavaScript
html = before(
    html,
    "const esc = (s)",
    "const LABELS = { aframes: 'A-Frames', axor: 'Axor / A-Struc', extern: 'Extern' };\n        ",
    "LABELS-constante",
)

html = before(
    html,
    "document.getElementById('modalProjectWeek').addEventListener('change'",
    """document.getElementById('modalProjectLabel').addEventListener('change', (e) => {
                if (activeProject && (activeProject.label || '') !== e.target.value) {
                    updateProjectField(activeProject.id, { label: e.target.value });
                }
            });

            """,
    "Listener label",
)

html = after(
    html,
    "cardElement.dataset.status = status;",
    """
                    if (project.label && LABELS[project.label]) {
                        cardElement.classList.add('label-' + project.label);
                        const chip = clone.querySelector('.card-label-chip');
                        chip.textContent = LABELS[project.label];
                        chip.classList.add(project.label);
                        chip.classList.remove('hidden');
                    }""",
    "Gewone kaart",
)

html = after(
    html,
    "row.dataset.status = status;",
    "\n                    if (project.label && LABELS[project.label]) row.classList.add('label-' + project.label);",
    "Archiefrij",
)

html = after(
    html,
    "document.getElementById('modalProjectWeek').value = activeProject.weekNumber || '';",
    "\n                        document.getElementById('modalProjectLabel').value = activeProject.label || '';",
    "loadProjects",
)

html = after(
    html,
    "document.getElementById('modalProjectWeek').value = project.weekNumber || '';",
    "\n            document.getElementById('modalProjectLabel').value = project.label || '';",
    "openProjectModal",
)

html = after(
    html,
    "document.getElementById('reviewWeek').value = '';",
    "\n            document.getElementById('reviewLabel').value = 'aframes';",
    "Reset review-label",
)

html = after(
    html,
    "const weekNumber = document.getElementById('reviewWeek').value.trim();",
    "\n            const label = document.getElementById('reviewLabel').value;",
    "Label uitlezen",
)

html = after(
    html,
    "status: 'upcoming',",
    "\n                    label: label,",
    "addDoc",
)

if errors:
    print("Niets gewijzigd. Problemen:")
    for e in errors:
        print(" -", e)
    sys.exit(1)

shutil.copyfile(path, path + ".bak")
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(html)

print(f"Klaar. Labels toegevoegd aan {path} (back-up: {path}.bak)")