# wptemps Phase B — Empaquetage `.app` partageable (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Empaqueter wptemps en une app `.app` double-cliquable et partageable, embarquant Python + PyObjC + le binaire `macmon`, avec lecture des températures fonctionnelle et option « Lancer au démarrage ».

**Architecture :** py2app produit `dist/wptemps.app`. `macmon` est copié dans `Contents/Resources/` ; `metrics/macos.py` le résout via `_macmon_path()` (binaire embarqué si `sys.frozen`, sinon `macmon` du PATH). Le menu « Lancer au démarrage » s'active dans le bundle via `SMAppService`. Un `build.sh` régénère l'app.

**Tech Stack :** Python 3.9, PyObjC (Cocoa/Quartz/ServiceManagement), py2app, pytest. Binaire `macmon` (Homebrew). Spike de build déjà validé.

## Global Constraints

- Cible **macOS Apple Silicon** uniquement.
- L'app **ne modifie jamais le wallpaper** (garantie héritée des phases précédentes).
- `macmon` doit être **embarqué** dans le bundle ; l'app lancée depuis le Finder ne dépend pas du PATH ni de Homebrew.
- Attribution de la **licence MIT de macmon** incluse dans le bundle.
- App **non signée** : 1er lancement par clic-droit → Ouvrir (documenté, pas de signature dans ce périmètre).
- `_macmon_path()` : si `sys.frozen` et que `<bundle>/Contents/Resources/macmon` existe → ce chemin ; sinon `"macmon"`.
- Le package reste `wptemps/` ; tests dans `tests/` ; venv `.venv` ; lancer pytest avec `.venv/bin/pytest`.
- py2app est un outil de build (pas une dépendance runtime) ; `build/`, `dist/`, `*.egg-info/` sont gitignorés.

---

### Task 1: Résolution du `macmon` embarqué (`_macmon_path`)

**Files:**
- Modify: `wptemps/metrics/macos.py`
- Test: `tests/test_macmon_path.py`

**Interfaces:**
- Consumes: rien.
- Produces:
  - `wptemps.metrics.macos._macmon_path(frozen=None, executable=None, exists=os.path.exists) -> str`
    — chemin du binaire macmon : embarqué si `frozen` et présent, sinon `"macmon"`.
  - `_macmon_one_sample()` utilise désormais `_macmon_path()` comme exécutable.

- [ ] **Step 1: Écrire les tests qui échouent**

Create `tests/test_macmon_path.py`:

```python
from wptemps.metrics.macos import _macmon_path


def test_macmon_path_source_mode_returns_plain_name():
    assert _macmon_path(frozen=False) == "macmon"


def test_macmon_path_bundle_returns_embedded_when_present():
    p = _macmon_path(
        frozen=True,
        executable="/Apps/wptemps.app/Contents/MacOS/wptemps",
        exists=lambda path: True,
    )
    assert p == "/Apps/wptemps.app/Contents/Resources/macmon"


def test_macmon_path_bundle_falls_back_when_absent():
    p = _macmon_path(
        frozen=True,
        executable="/Apps/wptemps.app/Contents/MacOS/wptemps",
        exists=lambda path: False,
    )
    assert p == "macmon"
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_macmon_path.py -q`
Expected: FAIL (`ImportError: cannot import name '_macmon_path'`).

- [ ] **Step 3: Implémenter `_macmon_path` et l'utiliser**

In `wptemps/metrics/macos.py`, add `import os` and `import sys` to the imports at the top
(the file already imports `json`, `re`, `subprocess`). Then add this function just before
`_macmon_one_sample`:

```python
def _macmon_path(frozen=None, executable=None, exists=os.path.exists) -> str:
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    executable = sys.executable if executable is None else executable
    if frozen:
        res = os.path.normpath(
            os.path.join(os.path.dirname(executable), "..", "Resources", "macmon"))
        if exists(res):
            return res
    return "macmon"
```

Then change `_macmon_one_sample` to use it:

```python
def _macmon_one_sample() -> str:
    out = subprocess.run(
        [_macmon_path(), "pipe", "-s", "1", "-i", "200"],
        capture_output=True, text=True, timeout=10, check=True,
    )
    return out.stdout.strip().splitlines()[-1]
```

- [ ] **Step 4: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_macmon_path.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Non-régression — lecture réelle depuis les sources**

Run: `.venv/bin/python -c "from wptemps.metrics import read_metrics; print(read_metrics())"`
Expected: valeurs réelles non nulles (en mode source, `_macmon_path()` renvoie `"macmon"`,
trouvé via le PATH du shell courant).

- [ ] **Step 6: Commit**

```bash
git add wptemps/metrics/macos.py tests/test_macmon_path.py
git commit -m "feat: _macmon_path resout le binaire macmon embarque dans le bundle"
```

---

### Task 2: « Lancer au démarrage » via SMAppService (`login.py`)

**Files:**
- Create: `wptemps/login.py`
- Modify: `wptemps/app.py`
- Test: `tests/test_login.py`

**Interfaces:**
- Consumes: rien (wrappe `ServiceManagement.SMAppService`).
- Produces:
  - `wptemps.login.available() -> bool` — vrai seulement si app empaquetée (`sys.frozen`) et
    `ServiceManagement` importable.
  - `wptemps.login.is_enabled() -> bool` — état courant ; `False` si indisponible/erreur.
  - `wptemps.login.set_enabled(enabled: bool) -> bool` — (dé)enregistre ; `False` si erreur.
- Modifie `app.py` : `login_supported()` délègue à `login.available()` ; le menu reflète/
  bascule l'état via `login.*`.

- [ ] **Step 1: Écrire les tests qui échouent**

Create `tests/test_login.py`:

```python
from wptemps import login


def test_available_false_from_source():
    # non empaquete (sys.frozen absent) -> indisponible
    assert login.available() is False


def test_is_enabled_safe_when_unavailable():
    # ne doit jamais lever, renvoie un bool
    assert login.is_enabled() in (True, False)


def test_set_enabled_safe_when_unavailable():
    # depuis les sources : echoue proprement, renvoie False, sans exception
    assert login.set_enabled(True) is False
    assert login.set_enabled(False) is False
```

- [ ] **Step 2: Lancer pour vérifier l'échec**

Run: `.venv/bin/pytest tests/test_login.py -q`
Expected: FAIL (`ModuleNotFoundError: wptemps.login`).

- [ ] **Step 3: Implémenter `login.py`**

Create `wptemps/login.py`:

```python
"""Lancement au demarrage via SMAppService (uniquement pour l'app empaquetee)."""
from __future__ import annotations

import sys


def available() -> bool:
    if not getattr(sys, "frozen", False):
        return False
    try:
        import ServiceManagement  # noqa: F401
        return True
    except Exception:
        return False


def is_enabled() -> bool:
    try:
        import ServiceManagement as SM
        return SM.SMAppService.mainAppService().status() == SM.SMAppServiceStatusEnabled
    except Exception:
        return False


def set_enabled(enabled: bool) -> bool:
    try:
        import ServiceManagement as SM
        svc = SM.SMAppService.mainAppService()
        if enabled:
            ok, _err = svc.registerAndReturnError_(None)
        else:
            ok, _err = svc.unregisterAndReturnError_(None)
        return bool(ok)
    except Exception:
        return False
```

- [ ] **Step 4: Lancer pour vérifier le succès**

Run: `.venv/bin/pytest tests/test_login.py -q`
Expected: PASS (3 tests). En mode source, `available()` est False et `set_enabled` renvoie
False sans lever (l'import de `ServiceManagement` peut réussir, mais `sys.frozen` est absent
pour `available`; `set_enabled` peut tenter l'appel — `SMAppService.mainAppService()` hors
bundle lève ou renvoie une erreur, capturée → False).

- [ ] **Step 5: Câbler le menu dans `app.py`**

In `wptemps/app.py`, add the import near the others:

```python
from . import login
```

Replace the existing `login_supported` function body so it delegates:

```python
def login_supported() -> bool:
    return login.available()
```

Replace `toggleLogin_` with a working implementation:

```python
    def toggleLogin_(self, sender):
        login.set_enabled(not login.is_enabled())
        self._refresh_checks()
```

In `_refresh_checks`, add the login checkmark sync (append after the existing lines):

```python
        if login_supported():
            self.item_login.setState_(
                AppKit.NSControlStateValueOn if login.is_enabled()
                else AppKit.NSControlStateValueOff)
```

(The existing `_build_status_item` already disables `item_login` when `not login_supported()`,
so in source mode it stays disabled; in the bundle it becomes active.)

- [ ] **Step 6: Lancer toute la suite**

Run: `.venv/bin/pytest -q`
Expected: PASS (l'ancien `test_app.py::test_login_supported_is_false_from_source` passe
toujours, `login.available()` étant False depuis les sources).

- [ ] **Step 7: Commit**

```bash
git add wptemps/login.py wptemps/app.py tests/test_login.py
git commit -m "feat: lancement au demarrage via SMAppService (actif dans l'app empaquetee)"
```

---

### Task 3: Configuration d'empaquetage py2app

**Files:**
- Create: `wptemps_app.py` (script d'entrée du bundle)
- Create: `setup.py`
- Create: `build.sh`
- Create: `THIRD_PARTY_NOTICES.md`
- Test: build validé en Task 4 (pas de test unitaire ; ce sont des fichiers de configuration)

**Interfaces:**
- Consumes: `wptemps.app.main`.
- Produces: une commande de build `bash build.sh` générant `dist/wptemps.app`.

- [ ] **Step 1: Créer le script d'entrée**

Create `wptemps_app.py`:

```python
from wptemps.app import main

main()
```

- [ ] **Step 2: Créer l'attribution de licence tierce**

Create `THIRD_PARTY_NOTICES.md`:

```markdown
# Notices tierces

Cette application embarque le binaire suivant :

## macmon
- Projet : https://github.com/vladkens/macmon
- Licence : MIT
- Usage : lecture sudoless des capteurs (températures, charge, conso) sur Apple Silicon.

Le texte de la licence MIT de macmon est disponible sur le dépôt du projet.
```

- [ ] **Step 3: Créer `setup.py`**

Create `setup.py`:

```python
import shutil

from setuptools import setup

MACMON = shutil.which("macmon") or "/opt/homebrew/bin/macmon"

setup(
    name="wptemps",
    app=["wptemps_app.py"],
    options={"py2app": {
        "argv_emulation": False,
        "plist": {
            "LSUIElement": True,
            "CFBundleName": "wptemps",
            "CFBundleDisplayName": "wptemps",
            "CFBundleIdentifier": "com.wptemps.app",
            "CFBundleShortVersionString": "1.0.0",
            "NSHumanReadableCopyright": "wptemps — voir THIRD_PARTY_NOTICES.md",
        },
        "packages": ["wptemps"],
        "resources": [MACMON, "THIRD_PARTY_NOTICES.md"],
    }},
    setup_requires=["py2app"],
)
```

- [ ] **Step 4: Créer `build.sh`**

Create `build.sh`:

```bash
#!/bin/bash
# Construit dist/wptemps.app (app partageable, Apple Silicon).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! command -v macmon >/dev/null 2>&1 && [ ! -x /opt/homebrew/bin/macmon ]; then
  echo "Erreur: macmon introuvable. Installe-le : brew install macmon" >&2
  exit 1
fi

rm -rf build dist
.venv/bin/python setup.py py2app

echo
echo "App construite : $ROOT/dist/wptemps.app"
echo "Partage : compresse dist/wptemps.app (zip). Au 1er lancement : clic-droit -> Ouvrir."
```

- [ ] **Step 5: Rendre `build.sh` exécutable et commit**

```bash
chmod +x build.sh
git add wptemps_app.py setup.py build.sh THIRD_PARTY_NOTICES.md
git commit -m "build: configuration py2app (.app + macmon embarque + attribution)"
```

---

### Task 4: Construire et valider le `.app` + README

**Files:**
- Modify: `README.md`
- Test: build et vérification réels (pas de test automatisé)

**Interfaces:**
- Consumes: tout le projet + `build.sh`.
- Produces: `dist/wptemps.app` validé + documentation de build/partage.

- [ ] **Step 1: Construire l'app**

Run: `bash build.sh`
Expected: build sans erreur ; `dist/wptemps.app` créé.

- [ ] **Step 2: Vérifier le binaire macmon embarqué et fonctionnel**

Run:

```bash
ls -la dist/wptemps.app/Contents/Resources/macmon
dist/wptemps.app/Contents/Resources/macmon pipe -s 1 -i 200 | python3 -c "import sys,json; d=json.load(sys.stdin); print('cpu_temp embarque:', d['temp']['cpu_temp_avg'])"
```

Expected : le binaire existe et imprime une température CPU réelle → l'app empaquetée
trouvera macmon sans Homebrew ni PATH.

- [ ] **Step 3: Lancer le `.app` et vérifier icône + overlay**

Run:

```bash
open dist/wptemps.app
sleep_pid=$(pgrep -f "wptemps.app/Contents/MacOS" | head -1)
.venv/bin/python - "$sleep_pid" <<'PY'
import sys, Quartz
pid = int(sys.argv[1])
infos = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
mine = [w for w in infos if w.get("kCGWindowOwnerPID") == pid]
print("fenetres du .app:", len(mine), "layers:", sorted(w.get("kCGWindowLayer") for w in mine))
PY
```

Expected : 2 fenêtres — overlay (layer négatif, niveau bureau) + icône barre de menus
(layer 25). Vérifier visuellement que les **températures réelles** s'affichent (plus de N/A,
grâce au macmon embarqué). Puis quitter l'app via son menu (ou `kill`).

- [ ] **Step 4: Mettre à jour le README (build & partage)**

Add this section to `README.md` just before the `## Tests` section:

```markdown
## Construire l'app partageable (.app)
```bash
bash build.sh
```
Produit `dist/wptemps.app` : Python, PyObjC et `macmon` sont **embarqués** — le
destinataire n'installe rien. Cible **Apple Silicon**.

Partage : compresser `dist/wptemps.app` en `.zip` et l'envoyer (ou le déposer sur
GitHub Releases). L'app n'étant pas signée par un compte développeur Apple, le 1er
lancement se fait par **clic-droit → Ouvrir** (ensuite, double-clic normal). Une fois
ouverte, le menu 🌡 propose « Lancer au démarrage ».

Licences tierces : voir `THIRD_PARTY_NOTICES.md` (macmon, MIT).
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README build & partage de l'app .app (Phase B)"
```

---

## Self-Review (rempli par l'auteur du plan)

**Couverture du spec (section Phase B) :**
- Empaquetage py2app → `dist/wptemps.app` → Tasks 3-4. ✓
- `macmon` embarqué dans `Contents/Resources/` → Task 3 (resources) ; validé Task 4. ✓
- `metrics/macos.py` résout le macmon embarqué (`_macmon_path`) → Task 1. ✓
- Attribution licence MIT macmon → Task 3 (`THIRD_PARTY_NOTICES.md`). ✓
- `build.sh` régénère l'app → Task 3 ; exécuté Task 4. ✓
- « Lancer au démarrage » via SMAppService, actif dans le bundle → Task 2. ✓
- Apple Silicon only / app non signée (clic-droit → Ouvrir) → README Task 4. ✓
- Ne modifie jamais le wallpaper → aucune dépendance wallpaper introduite. ✓

**Placeholders :** aucun TODO/TBD ; tout le code et les fichiers de config sont complets.

**Cohérence des types :** `_macmon_path(frozen, executable, exists) -> str` utilisé par
`_macmon_one_sample` ; `login.available/is_enabled/set_enabled` utilisés par `app.py`
(`login_supported` délègue à `login.available`, préservant le test Phase A) ;
`setup.py`/`build.sh`/`wptemps_app.py` cohérents (même nom de bundle `wptemps`, même script
d'entrée). Noms et signatures identiques entre tâches.
