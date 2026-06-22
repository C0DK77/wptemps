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
    if not available():
        return False
    try:
        import ServiceManagement as SM
        return SM.SMAppService.mainAppService().status() == SM.SMAppServiceStatusEnabled
    except Exception:
        return False


def set_enabled(enabled: bool) -> bool:
    # gate sur available() : aucun appel SMAppService hors app empaquetee
    # (evite d'enregistrer par erreur un element de connexion depuis les sources).
    if not available():
        return False
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
