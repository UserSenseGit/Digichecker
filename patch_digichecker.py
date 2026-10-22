#!/usr/bin/env python3
"""
Past Digichecker (index.html) aan:
  1. Compacte kaarten: titel, opleverweek, label + dunne voortgangsbalk
  2. Label 'Extern' voegt automatisch een afvinkbare regel 'Steekrubber' toe

Gebruik:   python patch_digichecker.py index.html
- Maakt eerst een back-up (index.html.bak)
- Is veilig om meerdere keren te draaien (reeds toegepaste stappen worden overgeslagen)
- Schrijft niets weg als een stap niet gevonden wordt
"""
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------- 1. template
TEMPLATE = """<!-- compact-card -->
    <template id="kanbanCardTemplate">
        <div class="kanban-card group bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md px-3 py-2 cursor-pointer"
            draggable="true">
            <div class="flex items-center gap-2">
                <h3 class="font-semibold text-zinc-900 dark:text-zinc-100 text-sm leading-snug break-words card-title flex-grow min-w-0"></h3>
                <span class="text-xs font-bold text-zinc-800 dark:text-zinc-100 bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 px-2 py-0.5 rounded-sm card-week-badge hidden shrink-0"></span>
                <span class="label-chip card-label-chip hidden shrink-0"></span>
            </div>
            <div class="flex items-center gap-2 mt-2">
                <div class="flex-grow bg-zinc-100 dark:bg-zinc-800 rounded-sm h-1.5 overflow-hidden">
                    <div class="bg-zinc-800 dark:bg-zinc-300 h-1.5 rounded-sm transition-all duration-500 card-progress-bar"
                        style="width: 0%"></div>
                </div>
                <span class="text-[10px] font-medium text-zinc-500 dark:text-zinc-400 card-progress-text shrink-0">0/0</span>
            </div>
        </div>
    </template>"""

# ------------------------------------------------------------ 2. renderBoard
RENDER_BLOCK = """// compact-card
                    clone.querySelector('.card-title').textContent = project.title || 'Nieuw Project';

                    const checklist = project.checklist || [];
                    let total = 0, checked = 0;
                    checklist.forEach(item => {
                        total++; if (item.checked) checked++;
                        if (item.subitems) {
                            item.subitems.forEach(sub => { total++; if (sub.checked) checked++; });
                        }
                    });

                    const percent = total === 0 ? 0 : Math.round((checked / total) * 100);
                    clone.querySelector('.card-progress-text').textContent = `${checked}/${total}`;

                    const progressBar = clone.querySelector('.card-progress-bar');
                    progressBar.style.width = `${percent}%`;
                    if (percent === 100 && total > 0) {
                        progressBar.classList.replace('bg-zinc-800', 'bg-emerald-500');
                        progressBar.classList.replace('dark:bg-zinc-300', 'dark:bg-emerald-500');
                    }

                    const weekBadge = clone.querySelector('.card-week-badge');
                    if (project.weekNumber) {
                        weekBadge.textContent = `W${project.weekNumber}`;
                        weekBadge.classList.remove('hidden');
                    }
"""

# ----------------------------------------------------------- 3. hulpfuncties
HELPERS = """
        const STEEKRUBBER = 'Steekrubber';
        const hasSteekrubber = (list) => list.some(i => (i.text || '').trim().toLowerCase() === STEEKRUBBER.toLowerCase());
        const newSteekrubberItem = () => ({ id: crypto.randomUUID(), text: STEEKRUBBER, checked: false, subitems: [] });"""

# ------------------------------------------------------ 4a/4b. label-listeners
LABEL_LISTENERS = """document.getElementById('modalProjectLabel').addEventListener('change', (e) => {
                if (activeProject && (activeProject.label || '') !== e.target.value) {
                    const fields = { label: e.target.value };
                    if (e.target.value === 'extern' && !hasSteekrubber(activeProject.checklist || [])) {
                        fields.checklist = [...(activeProject.checklist || []), newSteekrubberItem()];
                    }
                    updateProjectField(activeProject.id, fields);
                }
            });

            document.getElementById('reviewLabel').addEventListener('change', (e) => {
                if (e.target.value === 'extern' && pendingProjectData && !hasSteekrubber(pendingProjectData.checklist)) {
                    pendingProjectData.checklist.push(newSteekrubberItem());
                    renderReviewChecklist();
                }
            });"""

# ------------------------------------------------------------- 4c. vangnet
SAFETY_NET = """
            if (label === 'extern' && !hasSteekrubber(cleanedChecklist)) cleanedChecklist.push(newSteekrubberItem());"""

# (naam, marker die aangeeft dat de stap al gedaan is, regex, vervanging-functie)
PATCHES = [
    (
        "Compacte kaart-template",
        "<!-- compact-card -->",
        r'<template id="kanbanCardTemplate">.*?</template>',
        lambda m: TEMPLATE,
    ),
    (
        "renderBoard() opschonen + voortgangsbalk",
        "// compact-card",
        r"clone\.querySelector\('\.card-title'\)\.textContent = project\.title \|\| 'Nieuw Project';"
        r".*?(?=\s*cardElement\.addEventListener\('click')",
        lambda m: RENDER_BLOCK.rstrip("\n"),
    ),
    (
        "Hulpfuncties voor Steekrubber",
        "const STEEKRUBBER",
        r"^[ \t]*const esc = \(s\) =>[^\n]*$",
        lambda m: m.group(0) + HELPERS,
    ),
    (
        "Label-listeners (bestaand project + controlevenster)",
        "hasSteekrubber(activeProject.checklist",
        r"document\.getElementById\('modalProjectLabel'\)\.addEventListener\('change',.*?\n\s*\}\);",
        lambda m: LABEL_LISTENERS,
    ),
    (
        "Vangnet bij opslaan",
        "hasSteekrubber(cleanedChecklist)",
        r"const cleanedChecklist = .*?\n\s*\}\)\);",
        lambda m: m.group(0) + SAFETY_NET,
    ),
]


def main() -> int:
    if len(sys.argv) != 2:
        print("Gebruik: python patch_digichecker.py index.html")
        return 1

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Bestand niet gevonden: {path}")
        return 1

    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()

    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")

    changed = False
    for name, marker, pattern, repl in PATCHES:
        if marker in text:
            print(f"[overgeslagen] {name} (al toegepast)")
            continue
        new_text, count = re.subn(pattern, repl, text, count=1, flags=re.DOTALL | re.MULTILINE)
        if count == 0:
            print(f"[FOUT] '{name}' niet gevonden in het bestand. Er is niets gewijzigd.")
            return 1
        text = new_text
        changed = True
        print(f"[ok] {name}")

    if not changed:
        print("\nNiets te doen: alles was al toegepast.")
        return 0

    if crlf:
        text = text.replace("\n", "\r\n")

    backup = path.with_name(path.name + ".bak")
    shutil.copyfile(path, backup)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

    print(f"\nKlaar. Back-up: {backup.name}")
    print("Tip: formatteer daarna met Shift+Alt+F in VS Code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
